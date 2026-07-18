# DevQuality 代码投屏讲解路线

目标：面试官打开 GitHub 后，你能在 10 分钟内从入口讲到结果，不在目录里来回找文件。

## 投屏前准备

- IDE 打开项目根目录。
- 关闭包含 API key 的 `.env`，不要投屏环境变量。
- 提前固定以下文件标签页：
  - `frontend/src/api.ts`
  - `backend/internal/service/review_service.go`
  - `backend/internal/repository/postgres.go`
  - `backend/internal/worker/worker.go`
  - `agent_service/agent_service/agents/dual_agent.py`
  - `agent_service/agent_service/validator.py`
  - `agent_service/agent_service/llm/openai_compatible.py`
- 另开 Demo Console，但先讲代码再运行样例。

## 第一站：先看根目录

```text
DevQuality-Agent/
  frontend/       中文演示和 Agent UX
  backend/        Go 平台层
  agent_service/  Python Agent/LLM/评测
  docs/           设计、运行和面试材料
```

讲法：

> 我按职责拆成三层。前端只调用 Go；Go 管任务和数据库；Python 做无状态 Agent 计算。Go 是唯一数据库写入者。

不要一上来逐个介绍几十个文件。

## 第二站：前端如何发起 Review

### 打开 `frontend/src/api.ts`

重点看 `createReviewTask`：

- 构造 repo、commit、language、workflow、mode 和 diff。
- real + request override 时才发送 `llm_config`。
- server default 模式不发送 key。
- 调用 `POST /api/review-tasks`。

### 再看 `frontend/src/App.tsx`

只指出几个功能，不展开 UI 样式：

- `handleReview`：创建任务并轮询。
- `pollTask`：等待 pending/running 进入终态。
- `ReviewConsole`：输入和模式选择。
- `ResultPanel`：finding、test、report、JSON、validation debug。
- `SmokeExpectation`：示例 expected/actual 辅助对照。

讲法：

> 浏览器不直接调用模型厂商，所有请求先进入 Go Backend。这样密钥、任务状态和审计路径集中。

## 第三站：Go API 和任务创建

### 打开 `backend/internal/api/handler.go`

先让面试官看到 API 边界：

- `POST /api/review-tasks`
- `GET /api/review-tasks/{id}`
- `GET /api/review-tasks/{id}/report`
- `POST /api/findings/{id}/feedback`
- `GET /api/metrics/summary`

不需要逐行讲 JSON decode。

### 打开 `backend/internal/service/review_service.go`

重点讲 `CreateTask`：

1. 校验 language/workflow/mode。
2. Redis 用户限流。
3. 计算 diff hash。
4. Redis repo/commit 锁。
5. 构造 task 输入快照和版本字段。
6. PostgreSQL 创建 pending task。
7. 请求级 `llm_config` 放入内存 secret store。
8. 返回 `202 + task_id`。

这里可以强调：API 不同步等待 LLM，因此真实模型慢时不会一直占住创建请求。

## 第四站：DB-backed Queue

### 打开 `backend/internal/repository/postgres.go`

先跳到 `ClaimPendingTasks`，指出：

```sql
FOR UPDATE SKIP LOCKED
```

讲法：

> MVP 没有引入 Kafka/Celery。任务本来就要落库，所以我用 PostgreSQL status 做队列，多个 worker 通过 SKIP LOCKED 避免重复领取。

再跳到 `CompleteTask`：

- 开事务。
- 写 findings。
- 写 test suggestions，并关联 finding id/index。
- 写 agent runs。
- 更新 report、parsed/static JSON、duration 和 succeeded。
- commit。

最后指出 `FailTask` 会保存 validation errors 和 sanitized debug info。

## 第五站：Worker 如何调用 Python

### 打开 `backend/internal/worker/worker.go`

看 `Run` 和 `handleTask`：

- ticker 扫描 pending tasks。
- semaphore 控制 worker concurrency。
- 读取并删除一次性 LLM config。
- Redis 控制运行任务计数。
- `context.WithTimeout` 包住 Python 调用。
- validation errors 会转成 failed task。
- 成功进入 `CompleteTask`。

### 打开 `backend/internal/client/agent/client.go`

指出它把 task 转成 Python `/agent/review` 请求；只有 task 中存在请求级配置时才带 `llm_config`。

讲法：

> Go 不理解 Prompt，也不拼模型输出；它只管理计算任务和结果事务。

## 第六站：Python 服务入口

### 打开 `agent_service/agent_service/server.py`

说明：

- 提供 `/healthz` 和 `/agent/review`。
- Pydantic 解析 ReviewRequest。
- 根据 workflow 调 single 或 dual。
- 服务启动时加载本地 `.env`，但不写数据库。

不用纠结它没有使用 FastAPI。当前标准库 HTTP server 是 MVP 的轻量服务边界。

## 第七站：Agent Workflow 核心

### 首选打开 `agent_service/agent_service/agents/dual_agent.py`

按代码顺序讲：

1. `parse_unified_diff`
2. `run_static_checks`
3. `create_llm_client`
4. `run_review_agent`
5. `validate_response(..., validate_test_suggestions=False)`
6. 可选 `_repair_findings`
7. `run_test_agent`
8. 完整 Validator
9. `build_markdown_report`

这是整个项目最值得投屏的文件。

### 对照打开 `single_agent.py`

一句话说明：single 是 baseline，一次生成 finding + test；dual 是按职责拆分后的版本。

不要声称 dual 的准确率已经显著更高。可以说 mock 中结果一致，dual 换来的是阶段边界和可归因性。

## 第八站：Schema 和 Validator

### 打开 `agent_service/agent_service/schemas.py`

重点看：

- `Finding`
- `TestSuggestion`
- `AgentRun`
- `ReviewRequest`
- `ReviewResponse`
- `ValidationErrorDetail`

说明 API 合同是代码的一部分，不靠 Prompt 文本约定。

### 打开 `agent_service/agent_service/validator.py`

重点讲：

- path 必须在 diff。
- line 必须映射。
- severity/category/confidence/evidence。
- finding index 引用。

讲法：

> Pydantic 解决“长得像不像协议”，Validator 解决“是否符合当前 diff 的业务事实”。两者不是一回事。

## 第九站：Mock 与 Real Provider

### 打开 `agent_service/agent_service/llm/factory.py`

说明 provider 选择：

- mock -> MockLLM。
- request config 优先。
- 否则使用服务端环境配置。
- 缺失时清晰失败。

### 打开 `mock_llm.py`

指出它根据 static hints 生成稳定结果，并能模拟 invalid JSON、timeout 和 latency。

### 打开 `openai_compatible.py`

只定位四块：

1. `_system_prompt` / `_review_prompt`
2. `_chat`：temperature 0、JSON response format、timeout
3. `_generate`：Pydantic + schema repair once
4. `repair_findings`：allowed locations + deterministic validation errors

不要从文件第一行读到最后一行。

## 第十站：报告、反馈和评测

### 报告

打开 `agent_service/agent_service/report_builder.py`：报告由已校验结构生成，不再调用模型。

### 反馈

回到 `backend/internal/repository/postgres.go` 的 `RecordFeedback`：写入 `review_feedback`。

说明当前只是采集反馈，还没有自动学习。

### 评测

打开：

- `agent_service/agent_service/evaluation/dataset.py`
- `agent_service/agent_service/evaluation/runner.py`
- `agent_service/outputs/phase4/phase4_summary.md`

讲清：31 个样本的 Phase 4A 是 MockLLM/规则一致性测试；真实模型只有小规模 smoke。

## 10 分钟时间分配

| 时间 | 内容 | 文件 |
|---|---|---|
| 0:00-0:45 | 三层架构 | 根目录 |
| 0:45-1:30 | 前端提交 | `frontend/src/api.ts` |
| 1:30-2:45 | 创建 pending task | `review_service.go` |
| 2:45-4:00 | DB queue + transaction | `postgres.go` |
| 4:00-5:00 | worker timeout | `worker.go` |
| 5:00-7:00 | dual workflow | `dual_agent.py` |
| 7:00-8:00 | schema + Validator | `schemas.py`、`validator.py` |
| 8:00-9:00 | real provider + repair | `openai_compatible.py` |
| 9:00-10:00 | Demo、反馈、评测边界 | 前端 + Phase 4 summary |

## 面试官问什么，就打开什么

| 问题 | 优先文件 |
|---|---|
| 为什么不是 API 套壳 | `dual_agent.py`、`validator.py`、`worker.go` |
| 怎么防幻觉 | `diff_parser.py`、`validator.py` |
| Prompt 怎么写 | `openai_compatible.py` |
| 为什么双 Agent | `single_agent.py`、`dual_agent.py` |
| 队列怎么做 | `postgres.go::ClaimPendingTasks` |
| 并发怎么控 | `worker.go`、`ratelimit/limiter.go` |
| 失败怎么定位 | `debug_info.py`、`worker.go::validationSummary` |
| API key 怎么保护 | `secretstore/llm_config.go`、`factory.py` |
| 评测怎么做 | `evaluation/runner.py`、`phase4_summary.md` |
| feedback 怎么用 | `handler.go`、`postgres.go::RecordFeedback` |

## 现场 Demo 推荐顺序

1. 在示例库载入 Go timeout positive。
2. 先用 Mock 跑，说明链路可复现。
3. 如果真实模型配置稳定，再用 Real 跑一个样例。
4. 展示 finding 的 path/line/evidence。
5. 展示测试建议的 finding index。
6. 展示 Markdown 和 JSON。
7. 对 finding 提交反馈。
8. 最后展示 expected/actual，但强调只是 smoke 辅助判断。

不要现场批量运行真实模型。

## 常见投屏失误

- 在目录中搜索半天，不知道入口。
- 先讲 CSS，没讲 Agent workflow。
- 把 `.env` 或 API key 投屏。
- 把 Mock 100% 指标说成真实准确率。
- 只展示成功结果，不知道失败在哪里记录。
- 面试官问缓存时把 Redis 锁说成结果缓存。
- 用“多 Agent 更智能”代替具体数据流和校验边界。
