# Real LLM Smoke Test

本清单用于手工验收 OpenAI-compatible 真实模型。它只验证少量代表性样本的端到端行为，不替代独立评测集。

## 前置条件

1. PostgreSQL 已执行 `001_init.sql`、`002_real_llm.sql`、`003_real_llm_debug.sql`。
2. Redis、Python Agent Service、Go Backend 和 Demo Console 均已启动。
3. 在前端“真实模型”区域选择服务端默认配置，或填写当前请求的 `base_url`、`api_key`、`model` 和超时。
4. API key 不写入仓库、日志、数据库、报告或截图。

## 使用前端示例库

1. 在 Review Console 点击“示例库”。
2. 展开 `Real LLM Smoke Cases`，选择一个 patch。
3. 前端会自动填充 Git Diff、语言、`dual_agent` 和推荐的真实模型模式。
4. 检查服务端默认配置或本次请求临时覆盖配置后，手动点击“运行代码审查”。
5. 任务成功后，结果区会显示 Expected、Actual 和“符合预期 / 未完全命中预期”。

第一版只载入和运行单个样例，不提供批量真实模型执行，避免意外消耗 API 配额。

## Go Positive Diff

推荐使用 `agent_service/examples/go_resp_body_not_closed.patch`，或包含以下风险的 diff：

- `http.Get` 没有显式 timeout。
- 使用 response body 但没有 `resp.Body.Close()`。

成功标准：

- 任务最终为 `succeeded`。
- findings 与 test suggestions 能一一对应。
- title、suggestion、test_name、description 使用简体中文。
- category、severity、source 保持英文结构枚举。
- Validator 显示通过。

## Go Safe Negative Diff

推荐使用 `agent_service/examples/negative_safe_logging.patch`。

成功标准：

- 任务最终为 `succeeded`。
- findings 为 0，test suggestions 为 0。
- Validator 显示通过。

## Python Positive Diff

可以使用 `agent_service/examples/python_sql_injection.patch`、`python_requests_no_timeout.patch`，或同时包含动态 SQL 与无 timeout requests 调用的 diff。

成功标准：

- 优先结果：任务 `succeeded`，风险分类为 `sql_injection` / `timeout_missing`，并生成关联测试建议。
- 可诊断结果：若任务 `failed`，页面必须显示字段、期望类型/枚举、实际原因、失败阶段，以及是否执行 schema repair。

## 查看 Validation Error

任务失败后，在结果顶部查看“校验失败详情”：

- `首次模型输出`：第一次 JSON/schema 校验失败。
- `Schema Repair 输出`：repair 后仍不符合 schema。
- `确定性 Validator`：file_path、line_number、finding_index 等业务约束失败。
- `Repair 后 Validator`：业务约束修复后仍失败。

“JSON”标签页同时包含：

- `task.validation_errors`
- `task.debug_info.provider`
- `task.debug_info.model`
- `task.debug_info.workflow`
- `task.debug_info.language`
- `task.debug_info.repair_attempted`
- `task.debug_info.final_status`

系统不保存 raw model output，只保存脱敏错误摘要。

## 指标边界

真实模型 smoke 只说明指定模型和少量 diff 能否完成当前链路。Phase 4A 的 JSON valid rate、finding recall、false positive 等指标来自 MockLLM 和确定性规则，不能复用为真实模型准确率。

## 已完成的 DeepSeek Smoke

使用模型：`deepseek-v4-flash`

| 样本 | 最终状态 | Findings | Validator |
|---|---|---|---|
| Go positive | succeeded | `resource_leak`、`timeout_missing` | passed |
| Go safe negative | succeeded | 0 | passed |
| Python positive | succeeded | `timeout_missing`、`sql_injection` | passed |

Python finding 与测试建议的中文展示正常。以上是三个代表性样本的小规模 smoke test，只证明当前模型配置和链路在这些输入上可用，不等价于真实模型大规模准确率评测。

后续手工复测使用 `agent_service/real_llm_smoke_cases/` 中的 7 个 patch。positive 样本检查预期分类、路径、行号和测试建议关联；safe negative 样本检查是否出现误报。

前端示例由 `frontend/scripts/sync-examples.mjs` 在 `npm run dev` / `npm run build` 前从上述规范目录同步，避免前端静态副本与原始 patch 漂移。

对照条只是 smoke 辅助判断：

- positive：实际 findings 至少覆盖 metadata 中的 expected categories。
- safe negative：实际 findings 为 0 时显示“符合预期”。
- 真实模型具有非确定性，即使分类命中，人工验收仍需检查 file path、line number、evidence、suggestion 和测试建议的 finding_index 关联。
