# DevQuality 面试讲述主线

## 讲述原则

- 先说问题和设计依据，再说技术栈。
- 区分“已实现”“已 smoke”“下一步”。
- 不把 MockLLM 指标解释成真实模型准确率。
- 不用“多 Agent 更高级”作为理由。
- 遇到不会的追问，先说明当前实现，再给扩展方案。

## 30 秒项目介绍

> 我做了一个面向 Git Diff 的研发质量 Agent 平台。用户提交 Go 或 Python diff 后，系统会结合静态规则和 LLM 生成结构化 findings、关联测试建议和 Markdown 报告。Go 后端负责任务队列、worker、超时、Redis 限流和 PostgreSQL 事务，Python 负责 Diff Parser、Review/Test Agent、Pydantic schema、Validator 和 OpenAI-compatible provider。这个项目的重点不是调用模型，而是让模型输出可校验、可追踪、可反馈，并且支持 Mock 回归和真实模型 smoke。

## 3 分钟项目介绍

### 0:00-0:35 背景

> 我想解决的是 AI code review 的工程化问题。直接把 diff 发给模型会遇到 JSON 不稳定、路径行号幻觉、finding 和测试建议不对应，以及失败难定位。所以我没有只做一个 Prompt 页面，而是设计了一条受约束的审查链路。

### 0:35-1:20 核心流程

> Git Diff 先经过 parser 建立文件和行号映射，再由 static checker 给出 deterministic hints。dual workflow 中 Review Agent 只生成 findings，Validator 先检查 path、line、severity、evidence；通过后 Test Agent 才根据 validated findings 生成测试建议，最后再检查 finding index，报告由结构化数据生成。

### 1:20-2:10 平台层

> 前端只调用 Go Backend。Go 创建 pending 任务，PostgreSQL 同时作为事实库和 MVP 队列，worker 用 FOR UPDATE SKIP LOCKED 领取任务，带 context timeout 调 Python。Redis 当前用于用户限流、任务锁和运行计数。Python 是无状态服务，Go 是唯一数据库写入者，结果在一个事务内落库。

### 2:10-2:40 模型和安全

> 系统支持 MockLLM 和 OpenAI-compatible Real LLM。Mock 用于确定性测试、故障注入和负载测试；Real 支持服务端默认配置或单次请求覆盖，API key 不落库。模型结构失败最多 schema repair 一次，业务行号失败可以做一次受限 repair。

### 2:40-3:00 验证边界

> Phase 4A 用 31 个 mock 样本验证 workflow、schema、Validator 和 backend pipeline；这不是模型准确率。真实模型目前只完成 DeepSeek 的 Go positive、Go safe negative 和 Python positive smoke。下一步真正有价值的是独立人工标注的真实开源 diff 和长上下文处理，而不是继续堆 Agent。

## 5 分钟技术架构介绍

### 第 1 分钟：系统边界

```text
React Demo Console
  -> Go Backend
  -> PostgreSQL DB queue
  -> Go Worker
  -> Python Agent Service
  -> MockLLM / OpenAI-compatible LLM
```

> 前端负责交互，Go 负责平台治理，Python 负责 Agent 计算，PostgreSQL 是事实源，Redis 不作为队列。

### 第 2 分钟：任务生命周期

> 创建任务时 Go 做请求校验、Redis 限流和 repo/commit 锁，计算 diff hash，然后写 pending 并返回 task id。worker pool 周期领取任务，状态进入 running，Python 调用受 Go context timeout 保护。成功后 Go 在事务中写 findings、tests、agent runs 和 report；失败写错误和脱敏 validation details。

### 第 3 分钟：Agent 数据流

> Parser 先建立 allowed locations，Static Checker 提供 hints。Review Agent 生成结构化 finding，Pydantic 先做 schema 校验，Validator 再做 diff 事实校验。只有 finding 合法，Test Agent 才运行。最终测试建议必须引用已有 finding index。

### 第 4 分钟：Real LLM 稳定性

> Provider 使用 Chat Completions、temperature 0 和 JSON response format。Prompt 限制枚举、路径、行号和中文展示字段。首次输出非法会 repair 一次；路径行号不合法时 dual workflow 还能做一次受 allowed locations 限制的 finding repair。每个阶段记录 provider、model、token、latency、status。

### 第 5 分钟：验证和取舍

> 我保留 single-agent baseline 来和 dual 比较。当前 mock dataset 中结果一致，dual token 更高，但阶段边界和归因更清楚。负载测试也只使用 Mock，验证队列和 worker，不烧真实 API。真实模型只做小规模 smoke，所以我不会给出真实准确率结论。

## 10 分钟代码投屏讲解路线

### 0:00-1:00：目录和前端入口

- 根目录三层。
- `frontend/src/api.ts`：浏览器只调用 Go。
- `App.tsx`：轮询、状态、结果和反馈。

说：

> 我先从请求入口讲完整数据流，后面再看模型实现。

### 1:00-2:30：Go 创建任务

- `backend/internal/api/handler.go`
- `backend/internal/service/review_service.go::CreateTask`

说：

> API 请求不会同步等待模型，而是创建 pending task 后返回 202。这里能看到限流、diff hash 和任务锁。

### 2:30-4:00：数据库队列和事务

- `repository/postgres.go::ClaimPendingTasks`
- 指出 `FOR UPDATE SKIP LOCKED`。
- `CompleteTask` 的事务写入。

说：

> 我选择 DB-backed queue 是为了 MVP 简化基础设施，同时保证任务状态和结果一致。

### 4:00-5:00：Worker

- `worker/worker.go`
- semaphore、running counter、context timeout、success/failure。

### 5:00-7:00：Dual Agent

- `agents/dual_agent.py`
- parser -> hints -> review -> validator -> test -> validator -> report。

说：

> 这是项目核心。每一阶段都可以失败、记录和独立评测，不是自由聊天式多 Agent。

### 7:00-8:00：Schema 和 Validator

- `schemas.py`
- `validator.py`

说：

> Pydantic 检查协议，Validator 检查 path/line/finding reference 等业务事实。

### 8:00-9:00：Real Provider

- `llm/factory.py`
- `llm/openai_compatible.py`

说：

> 模型是可替换 provider；这里主要看结构化 Prompt、一次 repair、timeout 和密钥脱敏。

### 9:00-10:00：Demo 与评测边界

- 示例库载入一个 Go positive。
- 展示 finding evidence、测试关联和 expected/actual。
- 打开 `phase4_summary.md`。

说：

> Mock 数据证明工程链路可复现，Real smoke 证明特定模型能跑通，二者不混为一个准确率结论。

更完整的文件顺序见 `docs/CODE_WALKTHROUGH.md`。

## 项目亮点

### 1. 不是纯 Prompt Demo

- Diff Parser 和静态工具。
- 结构化 schema 和确定性 Validator。
- DB queue、worker、timeout、事务和反馈。

### 2. 有 baseline 和设计演进

- 先做 single-agent。
- 再拆 Review/Test。
- 能说明拆分收益和代价。

### 3. 模型失败可解释

- schema repair once。
- finding repair once。
- stage/field/expected/reason 调试信息。

### 4. Mock 和 Real 分层验证

- Mock evaluation 和 load test 可复现。
- Real LLM 只做有限 smoke，不夸大。

### 5. 安全边界清楚

- API key 不落库、不进日志/报告。
- Go 唯一写库。
- 请求级配置只在内存存在。

### 6. 演示闭环完整

- 示例库输入。
- pending/running 状态。
- finding/test/report/JSON。
- feedback。
- expected/actual smoke 对照。

## 项目不足

面试时主动讲 2-3 个，不要等面试官指出：

1. **真实模型评测不足**：只有少量 DeepSeek smoke，没有独立盲测 precision/recall。
2. **上下文范围有限**：只看 diff，没有仓库检索、调用图和长 diff chunking。
3. **静态规则有限**：规则覆盖面小，且只看 diff context。
4. **反馈未自动学习**：已采集但未回灌 Prompt/规则。
5. **没有结果缓存**：Redis 当前不是结果缓存，`cache_hit=false`。
6. **DB queue 有扩展上限**：高规模下需要独立队列/outbox。
7. **请求级 key 不可跨 Go 重启恢复**：安全和可恢复性之间的取舍。
8. **不是 PR 门禁产品**：没有账号、权限、GitHub App 和 accepted-risk policy。

## 下一步计划

按价值排序，而不是继续堆功能：

### P0：真实评测可信度

- 从真实开源 bugfix commit 抽取独立样本。
- 人工双人标注。
- 统计真实模型 precision、recall、误报和置信区间。

### P1：长上下文

- file/hunk chunking。
- token budget。
- finding 聚合、去重。
- 对需要跨文件上下文的 finding 做受控检索。

### P2：反馈驱动 badcase

- 离线聚合 not useful。
- 区分规则、Prompt、行号和证据问题。
- 修改后跑回归，不直接在线学习。

### P3：平台稳定性

- 有限任务重试和 retry count。
- accepted risk/waiver。
- 版本化结果缓存。
- 更完整的取消和恢复。

这些是 DevQuality 自身的合理延伸，不等于现在要进入 GameConfig 或 multi-agent board。

## 结束语模板

> 这个项目让我最大的收获是，Agent 工程不是把模型接进 API 就结束，而是要明确模型在哪些地方不可信，再用 schema、Validator、工具、任务治理、反馈和评测约束它。当前 DevQuality 已经完成了从 diff 输入到真实模型报告和反馈的闭环，但我也明确知道它还缺真实盲测和仓库级上下文。这两个方向比继续增加 Agent 数量更值得做。
