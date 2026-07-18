# DevQuality Agent Loop 设计

## 先说明：这里的 Loop 是有边界的工作流

DevQuality 不是让多个 Agent 自由聊天，也不是 ReAct 无限循环。当前实现是一个可观测、可中止、最多有限 repair 的 pipeline：每一步都有确定输入、输出和失败条件。

```text
Git Diff
  -> Diff Parser
  -> Static Checker
  -> Review Agent
  -> Finding Validator
  -> Test Agent
  -> Full Validator
  -> Report Builder
```

## 1. Git Diff -> Diff Parser

入口：`agent_service/tools/diff_parser.py`

Parser 把 unified diff 转成：

- files：old/new path。
- hunks：old/new start 和 count。
- lines：added/removed/context。
- added line 的新文件行号。

这一步很重要，因为模型输出的 `file_path` 和 `line_number` 后续必须能映射回 diff。没有这层，模型说“第 42 行有问题”时系统无法判断它是否在编造。

## 2. Diff Parser -> Static Checker

入口：`agent_service/tools/static_checker.py`

第一版规则：

- Go：HTTP helper 无 timeout、response body 未关闭、err 未处理、SQL 字符串构造。
- Python：requests 无 timeout、宽泛 except、SQL 插值、eval/exec。

输出是 `StaticHint`，包含 rule id、文件、行号、类别、证据和置信度。

Static Hint 的定位：

- 在 Mock 模式中，它决定可复现输出。
- 在 Real 模式中，它只是模型线索；Prompt 明确要求模型不要机械照抄。

## 3. Review Agent

入口：`agent_service/agents/review_agent.py`

Review Agent 只负责 finding：

- 哪个文件、哪一行。
- 什么风险类别和严重度。
- 证据是什么。
- 修复建议是什么。

它不生成测试建议，目的是缩小职责和输出 schema。

## 4. Finding Validator

入口：`agent_service/validator.py`

确定性检查包括：

- file path 必须在 diff 中。
- line number 必须能映射到该文件的新行或上下文行。
- severity 必须是 `low/medium/high/critical`。
- category 必须在允许枚举中。
- confidence 必须在 0 到 1。
- evidence 非空。

这层不调用 LLM。它解决的是结构和事实锚定，不等于理解所有业务语义。

## 5. Test Agent

入口：`agent_service/agents/test_agent.py`

只有 findings 校验通过，Test Agent 才会运行。输入是 validated findings，不是原始自由文本。

输出中的每条测试建议必须：

- 使用已有 `finding_index`。
- 指向对应目标文件。
- 给出测试名和测试步骤。

这样可以避免“Review 说 A，测试却在测 B”。

## 6. Full Validator

Review/Test 都完成后再次执行 Validator，额外检查：

- `finding_index` 是否越界。
- 建议是否引用真实 finding。

当前 Prompt 要求 `target_file` 与 finding 对应，但确定性 Validator 还没有单独校验两者相等；这是可补强点。

失败不会把无效结果当成 succeeded；错误会进入 validation errors 和调试摘要。

## 7. Report Builder

入口：`agent_service/report_builder.py`

Report Builder 不调用模型，只把已经结构化的数据转为 Markdown：

- 语言、校验状态。
- findings 和中文分类。
- test suggestions。
- agent runs 和错误。

报告只是展示层，事实来源仍然是结构化响应。

## single_agent 路径

入口：`agent_service/agents/single_agent.py`

```text
parse + static hints
  -> LLM 一次生成 findings + test_suggestions
  -> Pydantic
  -> Validator
  -> Report
```

它是 baseline，用于回答“为什么要拆 Agent”。优点是调用少、成本低；缺点是一个阶段同时承担审查和测试生成，失败归因不够细。

## dual_agent 路径

入口：`agent_service/agents/dual_agent.py`

```text
parse + hints
  -> Review Agent
  -> finding validator
  -> optional finding repair
  -> Test Agent
  -> full validator
  -> Report
```

Review/Test 复用同一个 LLM client，但分别记录 `review_agent`、`review_repair`、`test_agent` agent run。

## MockLLM 模式

入口：`agent_service/llm/mock_llm.py`

MockLLM 根据 static hints 稳定生成 findings，再按 finding 生成测试建议。它还支持：

- success。
- invalid_json。
- timeout。
- mock latency。

它的价值是把模型不确定性移除，单独测试 parser、workflow、Validator、Go worker、数据库和负载。它不是用来证明 AI 能力。

## Real LLM 模式

入口：`agent_service/llm/factory.py`、`openai_compatible.py`

配置优先级：

1. 请求级 `llm_config` 整套优先。
2. 否则使用 Python Agent Service 的 `.env` / 环境变量。
3. 都没有时返回 `real LLM config missing`。

请求级 key 只在浏览器内存、Go 进程内存和单次 Python 请求中存在，不落库、不进报告。

## OpenAI-compatible Provider

Provider 调用 Chat Completions：

- `temperature=0`。
- `response_format={"type":"json_object"}`。
- Prompt 限制文件/行号、枚举、中文展示字段和 JSON-only。
- 记录 provider、model、usage 和 latency。
- HTTP/网络错误不回显 API key。

当前只支持 OpenAI-compatible Chat Completions，不支持流式、tool calling 或 Responses API。

## Schema Repair Retry

首次模型输出经过：

1. 去掉可选 Markdown fence。
2. JSON parse。
3. Pydantic schema validation。

失败后最多进行一次 schema repair。Repair Prompt 明确要求：

- 只输出 JSON。
- 不要 Markdown fence 或解释。
- 遵守 schema。
- finding index、severity、category 使用允许值。
- 不编造路径和行号。

repair 仍失败时结束该阶段，不无限重试。

## Deterministic Finding Repair

有一种情况是 JSON/Pydantic 已通过，但 file path 或 line number 没有通过业务 Validator。dual workflow 会尝试一次 `review_repair`：

- 把 allowed locations 和 validation details 发给 provider。
- 只允许修字段，不允许增加无关风险。
- 修复后再次运行确定性 Validator。

这是有限校正，不是开放式 Agent 自我反思循环。

## Validation Failure 怎么处理

Python 返回：

- `validation_errors`。
- failed agent run。
- sanitized debug info：stage、field、expected、reason、repair attempted。

Go worker 看到 validation errors 后把任务标记为 failed，并持久化调试摘要。前端在结果区展示具体字段错误。系统不保存 raw model output，避免敏感内容和无界存储。

## Feedback Loop 怎么用

当前已经实现的闭环：

```text
用户查看 finding
  -> useful / not useful + comment
  -> Go feedback API
  -> review_feedback 表
```

当前还没有实现：

- 自动把反馈加入下一次 Prompt。
- 在线学习或微调。
- 根据 feedback 自动调整规则权重。

合理的下一步是离线聚合 feedback，把误报分成规则误报、Prompt 问题、证据不足、行号错误，再人工决定改规则、改 Prompt 或补数据集。

## 为什么当前不是复杂 multi-agent board

Review 和 Test 已经存在清晰的数据依赖：先 finding，后 test。增加 Planner、Critic、Judge 等 Agent 会带来：

- 更多 token 和延迟。
- 更复杂的失败组合。
- 更难证明每个 Agent 的增益。
- 更难做确定性测试和面试解释。

所以当前选择两个 Agent 加确定性工具和 Validator。只有真实评测证明某个新增角色能解决明确 badcase 时，才有理由扩展。

## 面试时如何概括这个 Loop

> 我没有把 Agent 设计成无限自主循环，而是设计成有边界的 Review/Test pipeline。静态工具先提供线索，Review Agent 生成结构化风险，Validator 做路径和行号事实校验，只有通过后 Test Agent 才生成关联测试。真实模型结构失败最多 repair 一次，业务位置失败也最多修一次。这样每一步都能独立观测、失败和重试，成本与风险是可控的。
