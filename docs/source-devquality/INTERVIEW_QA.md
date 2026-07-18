# DevQuality 面试问答

使用方式：先背每题的“推荐短答”，再理解“结合代码展开”。不要逐字背长段落，面试时围绕事实和取舍回答。

## 1. AI Code Review 怎么解决误报和漏报？

### 推荐短答

> 我没有假设 LLM 能彻底消除误报和漏报，而是把它拆成可度量的问题。静态规则提供确定性线索，Prompt 要求 evidence，Validator 拒绝 diff 外的文件和行号，negative samples 测误报，positive samples 测漏报，人工 feedback 用来沉淀 badcase。当前这些机制能降低幻觉和提高可诊断性，但真实模型只做了小规模 smoke，不能宣称已经解决泛化误报率。

### 结合代码展开

- `static_checker.py`：对 timeout、resource leak、SQL injection 等风险给 deterministic hints。
- `openai_compatible.py`：要求 evidence、allowed locations、受限枚举。
- `validator.py`：检查 file path、line number、confidence、evidence 和 finding index。
- Phase 4A dataset 同时有 positive 和 safe negative。
- `review_feedback` 收集 useful / not useful 和 comment。

### 还可以怎么改

- 用独立人工标注的真实开源 diff 做盲测。
- 按语言/类别统计 precision、recall 和 badcase。
- 把“代码有风险”和“团队接受该风险”分开建模。
- 对低置信度 finding 做提示而不是阻断。

## 2. 如果程序员故意这样写，但 AI 不通过怎么办？

### 推荐短答

> 当前 DevQuality 不是强制合并门禁，而是审查辅助工具。finding 有 evidence、severity 和 confidence，开发者可以标记 not useful 并写原因。真正产品化时，我会增加 accepted risk、规则抑制和到期时间，而不是让模型拥有最终决策权。AI 负责发现和解释，人负责接受业务权衡。

### 结合当前实现

- 前端能提交“有帮助 / 不准确 + comment”。
- Go API 把反馈写入 `review_feedback`。
- 当前没有 waiver/accepted-risk 表，也没有 PR blocking policy。

不要说“现在已经支持规则豁免”。正确说法是：反馈采集已实现，策略豁免是下一步。

## 3. Prompt 怎么设计？

### 推荐短答

> Prompt 不是只描述角色，而是把程序约束写进去。我给模型 allowed file/line locations、static hints、固定枚举和输出 schema；展示字段要求中文，结构字段保持英文；要求只输出 JSON、evidence 必须来自新增代码、静态提示只作为线索。温度设为 0，结构失败最多 repair 一次。

### Prompt 的四层约束

1. **任务约束**：只审查 Git Diff，不讨论无关代码。
2. **事实约束**：path 和 line 必须来自 allowed locations。
3. **协议约束**：severity/category/source/finding index 的类型和枚举固定。
4. **展示约束**：title、suggestion、test description 使用中文。

代码入口：`agent_service/llm/openai_compatible.py` 的 `_system_prompt`、`_review_prompt` 和 repair prompt。

## 4. Agent Loop 怎么设计？

### 推荐短答

> 我采用的是有边界的 pipeline，不是无限 ReAct。Diff Parser 建立行号，Static Checker 给 hints，Review Agent 生成 finding，Validator 先做事实校验，通过后 Test Agent 生成测试建议，最后再校验引用并生成报告。JSON schema 失败和 finding location 失败各最多修一次，失败就记录 agent run 并结束。

### 为什么有边界

- 代码审查是可分解任务，不需要 Agent 自由探索无限轮次。
- 成本、延迟和失败状态可预测。
- 每个阶段能单测和独立归因。

## 5. Review Agent / Test Agent 为什么拆开？单 Agent 不行吗？

### 推荐短答

> 我先做了 single-agent baseline，没有一开始就追求多 Agent。拆分依据是：finding 是事实判断，测试建议是基于 finding 的下游任务。拆开后可以先验证 finding，再让 Test Agent 只消费 validated findings；agent run 也能区分 Review/Test，未来可以独立重试。当前 mock dataset 中结果一致，dual token estimate 更高，所以我不会声称准确率显著提升，它的主要收益是职责边界和失败归因。

### 数据事实

- Phase 4A：single/dual 在当前 mock dataset 中 finding/test 结果一致。
- dual 平均 token estimate 更高。
- Test Agent 的 `finding_index` 由 Validator 检查。

这段回答能避免“为了赶 multi-agent 热潮而拆 Agent”的印象。

## 6. 内容太长放不进上下文怎么办？

### 推荐短答

> 当前版本直接处理完整 diff，还没有 chunking，这是明确限制。扩展时我会按 file 和 hunk 切分，先做局部 Review，保留每块的 path/line 映射，再聚合 findings、去重和统一生成测试建议。跨文件依赖可以按 import、调用关系或检索结果补有限上下文，并设置 token budget，而不是截断整个 diff。

### 可落地方案

1. 估算 token，超过预算才切分。
2. 优先按文件，再按 hunk 切分，不能破坏行号映射。
3. 每块输出同一个 Finding schema。
4. 聚合阶段按 category + file + line 去重。
5. Test Agent 使用聚合后 findings。
6. 对需要跨文件判断的 finding 标记 `needs_context`，再做一次受控检索。

不要说当前已经实现 MapReduce/向量检索。

## 7. 缓存机制怎么设计？

### 推荐短答

> 当前 Redis 实际用于限流、任务锁和运行计数，结果缓存还没有实现，`cache_hit` 固定为 false。我已经保存 diff hash、workflow、mode、prompt/schema/static-rule 版本，这些字段可以构成未来缓存 key。真正加缓存时还要包含 provider/model 和影响结果的参数，避免 Prompt 或规则升级后命中旧结果；真实模型请求级密钥绝不能进入 key 或缓存值。

### 推荐 cache key

```text
sha256(
  diff_hash + language + workflow + provider + model +
  prompt_version + schema_version + static_rule_version
)
```

### 缓存策略

- 只缓存 `succeeded + validator passed`。
- Mock 可以长 TTL；Real 应短 TTL 或按成本策略配置。
- feedback 不修改历史输出，但可以触发重新评测。
- 缓存命中仍返回新 task id，保留审计和权限边界。

## 8. Agent UX 怎么优化？

### 推荐短答

> Agent UX 的关键是让用户知道系统在做什么、为什么这么判断、失败在哪。当前前端区分 pending/running/succeeded，显示 evidence、severity、confidence、测试关联、raw JSON、Markdown 和字段级 validation error；示例库还能显示 expected/actual。下一步会增加 accepted risk、按文件导航和逐步流式状态，但不会用“模型正在思考”这种不可验证文案。

### 当前已实现的 UX

- 未完成时显示“等待审查/正在审查”，不提前显示零风险。
- Real 配置分服务端默认和本次临时覆盖。
- API key masked，不进 localStorage。
- validation error 显示 stage、field、expected、reason。
- safe negative 的结果明确显示是否符合预期。

## 9. 为什么用 Go + Python？

### 推荐短答

> 我按职责而不是按偏好拆语言。Go 负责 API、DB-backed queue、worker pool、context timeout、Redis 限流和事务持久化；Python 负责 Pydantic、Diff 工具、Agent workflow、LLM provider 和 evaluation。Go 是唯一数据库写入者，Python 保持无状态，这样边界清楚。代价是双服务联调更复杂，所以我先做 Python CLI baseline，再接 Go 平台层。

### 追问：为什么不用全 Python？

全 Python 当然可行，但这个项目还想展示任务治理和后端工程；Go 在并发 worker 和服务边界上更直接。重点不是“Go 一定更快”，而是职责分离和我对工程平台的取舍。

## 10. 项目最大难点是什么？

### 推荐短答

> 最大难点不是调用模型，而是跨层保证“模型输出能成为可信系统数据”。我遇到过模型 JSON 合法但路径/行号不合法、Python 返回详细 validation error 但 Go 只保存通用错误、旧端口实例干扰诊断、Windows UTF-8 BOM 导致请求解析失败。最后通过 Pydantic + 业务 Validator、脱敏 debug info、单一数据库写入 owner、阶段日志和端到端 smoke 把问题定位清楚。

### 可选择讲的真实故障

- `return resp, err` 被静态规则误报，补上下文判断和回归测试。
- 8080 端口竞争导致请求打到旧实例，改 18080 并在 `net.Listen` 成功后打印日志。
- PowerShell UTF-8 BOM 导致 Go JSON decoder 失败。
- Python real case 失败时详细 validation errors 被 Go 丢弃，后来补持久化和前端展示。

面试中选一个展开，不要一次罗列全部。

## 11. 真实 LLM 接入遇到了什么问题？

### 推荐短答

> 主要是结构稳定性、事实映射、中文展示和密钥安全。模型可能输出 Markdown fence、非法枚举、错误行号或英文展示字段。我用 response_format、温度 0、Pydantic、一次 schema repair、allowed locations 和一次 finding repair处理；API key 支持服务端环境配置或请求级内存透传，不落库、不写日志和报告。

### 真实验证边界

- DeepSeek `deepseek-v4-flash`：Go positive 命中 resource leak/timeout，Go safe negative 0 finding，Python positive 命中 timeout/SQL injection。
- 这是三个代表性 smoke，不是盲测或大规模评测。

## 12. Mock Evaluation 和 Real LLM Smoke Test 有什么区别？

### 推荐短答

> Mock evaluation 测的是系统工程稳定性：规则、schema、Validator、single/dual workflow 和 backend pipeline 是否可重复；Real smoke 测的是特定模型在少量样例上能否完整走通。Phase 4A 的 100% 指标来自 31 个与确定性规则一致的 mock 样本，不能当作 DeepSeek 的准确率。真实模型目前只有少量 positive/safe negative 手工验证。

| 对比 | Mock Evaluation | Real LLM Smoke |
|---|---|---|
| 样本 | 31 个人工数据 | 少量代表样本 |
| 模型 | MockLLM | DeepSeek/OpenAI-compatible |
| 目的 | 可复现工程回归 | 协议和基本质量验收 |
| 成本 | 低 | 有 API 成本 |
| 能否证明泛化 | 不能 | 也不能 |

## 13. 如果面试官质疑“这是不是 API 套壳”，怎么回答？

### 推荐短答

> 如果只是前端把 Prompt 发给模型再展示文本，那是套壳。DevQuality 的主要代码并不在 API 调用本身：它解析 Git Diff 和行号、生成静态 hints、定义结构化 schema、做确定性 Validator、拆 Review/Test 阶段、处理 schema repair、记录 agent runs；平台侧还有 DB queue、worker timeout、Redis 限流、事务写入、反馈、evaluation 和负载测试。模型只是可替换的一个 provider。不过我也不会说它已经是完整生产系统，因为仓库级上下文、真实盲测和反馈学习还没完成。

### 投屏证据

优先打开：

1. `agent_service/tools/diff_parser.py`
2. `agent_service/validator.py`
3. `agent_service/agents/dual_agent.py`
4. `backend/internal/worker/worker.go`
5. `backend/internal/repository/postgres.go`
6. `agent_service/evaluation/runner.py`

不要先打开 CSS 或一个大 Prompt 文件来回答“套壳”质疑。

## 14. 为什么选择 DB-backed queue？

### 推荐短答

> MVP 的任务规模不需要 Kafka/Celery。任务本来就要落 PostgreSQL，所以我用 status + `FOR UPDATE SKIP LOCKED` 领取 pending 任务，减少基础设施并保持状态一致。Redis 只做限流和锁。代价是数据库承担扫描压力，规模扩大后才考虑独立消息队列和 outbox。

## 15. 为什么 Go 是唯一数据库写入者？

### 推荐短答

> 如果 Python 和 Go 都写任务结果，状态、findings、agent runs 和报告很难维持同一事务边界。现在 Python 只返回计算结果，Go 在一个事务中写入并更新终态。这样失败恢复和审计更清楚。

## 16. Feedback 已经形成学习闭环了吗？

### 推荐短答

> 现在闭合的是反馈采集，不是自动学习。用户反馈已经持久化，可以用于离线 badcase 分类；但它还没有自动进入 Prompt、规则权重或训练。直接在线学习风险很大，我会先做人工审核和离线评测，确认修改不会扩大其他类别误报。

## 面试回答红线

- 不说“真实模型准确率 100%”。
- 不说“dual_agent 显著优于 single_agent”。
- 不说“Redis 已经缓存审查结果”。
- 不说“已经支持任意大仓库上下文”。
- 不说“反馈会自动训练模型”。
- 不说“这是高并发生产系统”。
- 可以说“当前已经把不确定模型放进可验证、可观测的平台流程，并明确记录了下一步缺口”。
