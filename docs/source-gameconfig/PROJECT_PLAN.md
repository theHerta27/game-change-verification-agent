# 项目计划

## 项目目标

GameConfig Agent 的目标是搭建一个面向游戏策划配置生成、校验、风险审查、自动修复、测试场景生成、基准评测和本地可视化演示的多 Agent 协作平台。项目使用 deterministic MockLLM 作为默认路径，保证离线、稳定、可复现；真实 LLM provider 作为可选能力，并通过 schema、reference、rule validation 和 badcase 记录控制输出漂移风险。

## 目标岗位适配

| 岗位 | 价值 |
|------|------|
| 游戏策划 | 将自然语言需求转换为可检查配置，并看到假设、风险和修复记录 |
| 数值策划 | 通过设计参考和 Reviewer 发现平衡性问题 |
| 配置工程师 | 通过 Validator、Reference Checker、Rule Engine 捕获上线前硬错误 |
| 制作人 / Lead | 通过 Markdown 报告和 Web Console 审阅风险、修复动作、最终状态和评测指标 |

## Agent / Tool 边界

Agent 负责语义判断、审查和修复策略：

- Config Generator Agent：理解自然语言需求并生成配置草案。
- Config Reviewer Agent：输出问题、证据、严重级别、推荐范围和修复建议。
- Config Repair Agent：根据校验错误与审查发现执行有边界的局部修复。
- Test Scenario Agent：根据最终配置生成配置测试场景。

Tool 负责确定性执行：

- Schema Validator Tool：字段、类型、枚举、必填项和脏结构防御式检查。
- Reference Checker Tool：配置引用完整性检查。
- Rule Engine Tool：硬规则、升级连续性、once_only、关联字段检查。
- Report Builder / Exporter Tool：输出 JSON 与 Markdown。
- Evaluation Tool：计算测试场景覆盖率和 benchmark 指标。

Design Reference 只提供参考数据，不做语义判断，也不称为 Agent。

## Blackboard 设计

Blackboard 是所有 Agent 和 Tool 的共享状态，至少包含：

```json
{
  "requirement_text": "...",
  "structured_requirement": {},
  "assumptions": [],
  "draft_configs": {},
  "design_reference": {},
  "validation_errors": [],
  "review_findings": [],
  "repair_actions": [],
  "repaired_configs": {},
  "final_validation": {},
  "trace": []
}
```

每一步 trace 记录 actor、actor_type、action、input_refs、output_refs、status 和 error_count。Web Console 只读取和展示这些产物，不改变核心 pipeline。

## Repair Scope Rules

允许修改：

- 当前实体内部字段，例如 `base_attack`、`attack_bonus`、`gold_cost`。
- 显式引用关系字段，例如 `weapon_config.item_id`。
- Rule Engine 标记的关联字段。
- 缺失但必要的引用项，例如 `item_refine_stone` 的基础 item 定义。

禁止修改：

- 不相关配置表。
- 新增系统级机制。
- 修改原始需求语义。
- 大范围重构配置结构。
- 引入新的玩法规则。
- 删除核心配置实体。

## 路线图

### Milestone 1：Core Multi-Agent Pipeline

已完成：

- deterministic MockLLM。
- Training Sword demo。
- 3 个核心 Agent、确定性工具和设计参考。
- blackboard trace、bounded repair loop。
- Phase 0 JSON artifacts、Markdown reports、pytest。

### Milestone 2：Test Scenario & Evaluation

已完成：

- 新增 Test Scenario Agent，从 `final_configs` 生成配置测试场景。
- 新增 small evaluation dataset，用 expected coverage tags 计算场景覆盖率。
- 输出 `test_scenarios.json`、`test_scenario_report.md`、`evaluation_report.md`。
- 保持 Phase 0 CLI 可用。

### Milestone 3：LLM Provider & Robustness

已完成：

- 新增 LLM provider 抽象：`MockLLMProvider` 和 `OpenAICompatibleProvider`。
- 保留 mock provider 为默认路径。
- 新增 generator、reviewer、repairer、test scenario prompt templates。
- 所有真实 provider 输出进入 JSON 解析、schema/reference/rule/final validation。
- JSON 解析失败、schema validation failed、provider 异常和 schema drift 都记录 badcase。
- 支持项目根目录 `.env`，且不覆盖已有环境变量。

### Milestone 4：Benchmark Dataset & Hardcase Evaluation

已完成：

- 扩展 10 个 benchmark requirement samples。
- 覆盖 beginner weapon、rare weapon、upgrade cost、reward once_only、duplicate reward、skill damage config、level reward curve、missing reference、safe balanced config 和 schema drift hardcase。
- 使用现有 Generator、Reviewer、Repairer、Test Scenario Agent 相关流程能力，不新增 Agent。
- 输出统一评测报告、badcases 和 sample summary。

### Milestone 5：Web Console

已完成：

- 新增 FastAPI local API wrapper。
- 新增 React + Vite + TypeScript + Tailwind 前端。
- 展示 workflow summary、timeline、blackboard trace、configs、validation、review、repair、test scenarios、metrics、badcases、Markdown reports 和 artifacts。
- 默认使用 mock provider，真实 provider 作为可选能力并带 timeout。

### Milestone 6：Final Packaging & Interview Demo

已完成：

- 新增本地启动脚本和全量测试脚本。
- 新增演示脚本和面试讲解笔记。
- 生成 `outputs/final/project_summary.md`。
- README 收口为快速入口。
- smoke test 覆盖 pytest、npm build、FastAPI health、Web Console access、mock demo 和 Phase 3 benchmark metrics。
