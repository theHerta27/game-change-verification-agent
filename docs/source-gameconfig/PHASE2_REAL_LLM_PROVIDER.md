# Phase 2 真实 LLM Provider 接入

## 目标

Phase 2 在不重构 Phase 0 / Phase 1 主流程的基础上，新增真实 LLM provider 接入层、prompt contract、badcase 记录和 small real-run evaluation。

## Provider

支持两个 provider：

- `MockLLMProvider`：默认 provider，确定性、离线、适合测试和稳定演示。
- `OpenAICompatibleProvider`：OpenAI-compatible Chat Completions 风格 provider。

## 环境变量与 `.env`

`OpenAICompatibleProvider` 只从环境变量读取配置：

- `GAMECONFIG_LLM_BASE_URL`
- `GAMECONFIG_LLM_API_KEY`
- `GAMECONFIG_LLM_MODEL`

也可以在项目根目录创建 `.env`：

```text
GAMECONFIG_LLM_BASE_URL=https://api.example.com/v1
GAMECONFIG_LLM_API_KEY=replace-with-your-api-key
GAMECONFIG_LLM_MODEL=replace-with-model-name
```

`run_real_demo` 启动前会加载 `.env`。如果同名变量已经存在于 `os.environ`，`.env` 不会覆盖它。`.env` 不应提交，`.env.example` 可提交。

## Prompt Contract

Prompt templates 位于 `gameconfig_agent/prompts/`：

- `generator.md`
- `reviewer.md`
- `repairer.md`
- `test_scenario.md`

所有 prompt 都要求 provider 返回 JSON，不返回 Markdown。Generator 和 Repairer prompt 会明确给出：

- 四个 config group 必须为数组
- 每种配置行的必填字段和数据类型
- 可用枚举值
- 引用完整性约束
- 可复制的完整 JSON 结构示例

“JSON 可解析”只说明语法有效，不代表配置符合项目 Schema；Validator 仍是最终质量门禁。

## 单次运行与评测边界

- Web Console 的“生成并校验当前需求”只运行当前 requirement，`sample_count=1`。
- CLI `run_real_demo` 用于 small real-run evaluation，会运行当前输入加 3 个固定样本，`sample_count=4`。
- Web 单次运行失败时，策划视图显示本次 provider、model、校验阶段和问题数量；开发者视图保留字段级 badcase。

## Validation And Badcases

真实 LLM 输出必须经过：

- JSON parse
- Schema Validator
- Reference Checker
- Rule Engine
- Final Validation
- Test scenario coverage evaluation

如果 JSON parse failed 或 schema validation failed，写入 badcase：

```text
outputs/phase2/badcases.md
```

真实 LLM 输出可能发生 schema drift，例如：

- `upgrade_config` 不是 list
- `upgrade_config[i]` 是 string 而不是 object
- `cost_items` 不是 list
- `cost_items[j]` 是 string 而不是 object

Schema Validator 必须返回结构化错误，real-run pipeline 必须生成 badcase artifacts，不允许因为脏结构 traceback 崩溃。

## CLI

默认 mock provider：

```powershell
python -m gameconfig_agent.cli run_real_demo `
  --input examples\training_sword_requirement.txt `
  --output outputs\phase2 `
  --provider mock
```

OpenAI-compatible provider：

```powershell
python -m gameconfig_agent.cli run_real_demo `
  --input examples\training_sword_requirement.txt `
  --output outputs\phase2 `
  --provider openai_compatible
```

## 指标

Phase 2 记录：

- `json_parse_success_rate`
- `schema_pass_rate`
- `final_validation_pass_rate`
- `repair_success_rate`
- `test_scenario_coverage_rate`
- `latency_ms`
- `token_estimate`
- provider 返回的 `usage`
