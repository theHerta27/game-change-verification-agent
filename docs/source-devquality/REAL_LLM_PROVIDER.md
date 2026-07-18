# OpenAI-compatible Provider 设计

## 调用路径

```text
Demo Console
  -> Go Backend POST /api/review-tasks
  -> DB-backed queue
  -> Go worker（可选：读取一次性 llm_config）
  -> Python Agent Service /agent/review
  -> 请求级 llm_config 或服务端环境配置
  -> OpenAI-compatible /chat/completions
  -> schema + validator
  -> Go Backend 事务写入结果
```

## 配置优先级

配置严格按来源选择，不逐字段混用：

1. 请求中存在 `llm_config`：整套使用请求级配置。
2. 请求中不存在 `llm_config`：整套使用 Python Agent Service 的环境变量或本地 `.env`。
3. real mode 两种来源都不可用：返回 `real LLM config missing`。

服务端默认配置：

```text
LLM_PROVIDER=openai_compatible
LLM_API_BASE=https://api.example.com/v1
LLM_API_KEY=<YOUR_API_KEY>
LLM_MODEL=<MODEL_NAME>
```

将 `agent_service/.env.example` 复制为本机 `.env` 后填写真实值，再重启 Python Agent Service。进程环境变量优先于 `.env`；`.env` 已被 `.gitignore` 排除，`.env.example` 只能保留占位符。

使用服务端默认配置时，前端请求不包含 `llm_config`：

```json
{
  "mode": "real"
}
```

使用本次请求临时覆盖配置时：

```json
{
  "mode": "real",
  "llm_config": {
    "provider": "openai_compatible",
    "base_url": "https://api.example.com/v1",
    "api_key": "<CURRENT_REQUEST_API_KEY>",
    "model": "<MODEL_NAME>",
    "timeout_seconds": 30
  }
}
```

## API Key 安全策略

- 不写入 PostgreSQL、Redis、报告、agent_runs、README 或日志。
- 前端使用密码输入框，值只保存在 React 内存状态，不写 localStorage/sessionStorage。
- Go Backend 只在进程内按 `task_id` 暂存，请求被 worker 领取后删除。
- `ReviewTask` 的 JSON 序列化显式排除 `llm_config`。
- Python 对 Pydantic 请求错误只返回字段位置、消息和类型，不回显输入值。
- Provider 错误不会回显 Authorization Header 或 API Key。
- 服务端 `.env` 只由 Python 进程读取，不通过 Go API 或前端返回。

请求级密钥不持久化意味着：Go Backend 重启后，尚未执行的 real 任务无法恢复该密钥。需要跨重启恢复时，应使用 Python 服务环境变量，而不是把密钥写入任务表。

## Schema Repair

1. 第一次 Chat Completions 使用 `response_format={"type":"json_object"}`。
2. 返回内容先去除可选 Markdown fence，再进行 JSON 解析和 Pydantic 校验。
3. 首次失败时，把目标 JSON Schema、脱敏后的校验错误和原始模型输出发送给同一 provider。
4. repair 最多一次；第二次仍失败则生成 failed agent run 和 validation error。

如果 Pydantic schema 已通过、但 file_path/line_number 等确定性 Validator 失败，dual-agent workflow 会执行一次 `review_repair`：只允许模型依据 `allowed_locations` 和 validator errors 修正 findings，不允许增加与 diff 无关的新风险。

## 失败任务调试信息

failed real task 只保存脱敏摘要，不保存 raw model output：

- provider、model、workflow、language
- validation error 的 stage、field、expected、reason
- repair_attempted
- final_status

这些字段保存于 `review_tasks.validation_errors_json` 和 `review_tasks.debug_info_json`。API key 不进入上述字段。

## Timeout 与运行记录

- 请求级 `timeout_seconds` 当前允许 1 到 120 秒；服务端默认配置使用 30 秒。
- Go worker 仍受 `TASK_TIMEOUT` 控制，因此生产配置应保证 worker deadline 大于模型 timeout。
- agent_runs 记录 agent_name、provider、model、input/output tokens、latency、status 和脱敏错误。

## 当前限制

- 只实现 OpenAI-compatible Chat Completions，不包含 Responses API、流式输出或工具调用。
- 未做真实模型大规模 evaluation；真实模型效果不能引用 Phase 4A mock 指标。
- 不实现密钥托管、账号权限、项目管理、Docker 或 DevQuality multi-agent board。
