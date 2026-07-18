# Milestone 8：新手试炼配置调优闭环计划

## 1. 目标

将当前 Training Sword 单次演示升级为一个受控、可解释、可重复的新手试炼配置调优闭环：

```text
策划输入新需求
-> 需求准入与约束提取
-> 生成并静态校验配置
-> Unity Run A
-> 根据 telemetry 发现偏差
-> 策划输入修改要求
-> 生成配置 Diff
-> 策划确认
-> 重新静态校验
-> Unity Run B
-> Run A / Run B 前后对比
```

本 Milestone 不把 GameConfig Agent 改造成通用聊天机器人，不引入 LangGraph，不增加多 Agent 辩论，也不接数据库和云端 Remote Config。

## 2. 已确认的产品决策

| 决策 | 结论 |
|---|---|
| 产品形态 | 保持结构化策划工作台 |
| 自由文本入口 | 分为“新配置需求”和“修改当前配置”两种明确模式 |
| 确定性操作 | 静态校验、准备 Unity、启动试玩、自动回归和对比继续使用按钮与 API |
| 配置范围 | 扩展为受控的单人新手试炼配置包 |
| 修改方式 | 先生成 Diff，必须由策划确认后才能应用 |
| 运行验证 | 每次 Unity 运行绑定独立 run_id 和配置快照 |
| 对比方式 | Run A / Run B 工程前后对比，不宣称统计学 A/B 实验 |
| Agent 边界 | 不为了数量新增 Agent；准入、Diff 和应用属于 Tool / Service |

## 3. 外部项目核验结论

### 3.1 Langflow

截至本计划核验时，Langflow 官方仓库 `main` 分支的 Assistant 路径包含：

- 输入清洗和 Prompt Injection 模式检测。
- 一次独立 LLM 调用完成翻译和轻量意图分类。
- `generate_component`、`question`、`off_topic` 三类意图。
- `off_topic` 的确定性拒绝分支。
- 生成代码的静态检查、安全扫描、运行检查和重试。

官方当前源码并不支持二手对话中声称的七类 `build_flow/run_flow/manage_files` Intent，也没有在 `classify_intent` 中接收会话状态；该分类调用明确保持无状态和会话隔离。

对本项目的启发是：

```text
自然语言入口需要轻量治理；
治理状态应少而明确；
生成后仍必须执行确定性校验；
不能从 Langflow 推导出“所有工作台操作都应走 Intent Router”。
```

来源：

- [Langflow assistant_service.py](https://github.com/langflow-ai/langflow/blob/main/src/backend/base/langflow/agentic/services/assistant_service.py)
- [Langflow intent_classification.py](https://github.com/langflow-ai/langflow/blob/main/src/backend/base/langflow/agentic/services/helpers/intent_classification.py)
- [Langflow input_sanitization.py](https://github.com/langflow-ai/langflow/blob/main/src/backend/base/langflow/agentic/helpers/input_sanitization.py)
- [Langflow translation_flow.py](https://github.com/langflow-ai/langflow/blob/main/src/backend/base/langflow/agentic/flows/translation_flow.py)

### 3.2 TradingAgents

TradingAgents 的程序入口接收 ticker、日期和资产类型等结构化参数。CLI 对 ticker 字符集、长度和日期格式做确定性校验，不需要处理通用自然语言意图。

它使用 LangGraph `StateGraph` 编排市场、新闻、情绪和基本面分析节点，以及 Bull/Bear 研究辩论、Trader、风险辩论和 Portfolio Manager。多 Agent 图结构来自金融分析中确实存在的多视角论证需求，不是通用模板。

对本项目的启发是：

```text
结构化输入不应交给 LLM 猜；
只有存在真实职责冲突时才需要多 Agent；
GameConfig 的校验与配置应用不需要辩论图。
```

来源：

- [TradingAgents README](https://github.com/TauricResearch/TradingAgents)
- [TradingAgents graph setup](https://github.com/TauricResearch/TradingAgents/blob/main/tradingagents/graph/setup.py)
- [TradingAgents CLI validation](https://github.com/TauricResearch/TradingAgents/blob/main/cli/utils.py)

### 3.3 通用 Agent 与垂直工作台

Codex 面向用户委托的广泛软件工程任务，重点是模型推理、工具调用、隔离环境、权限和人工监督，而不是先把用户请求分类成少数业务 Intent。OpenAI Agents SDK 同时提供输入、输出和 Tool guardrails，以及需要人工批准时暂停和恢复 Run 的机制。

这说明：

```text
通用 Agent 可以依赖模型规划多种任务；
垂直业务系统仍需限制可修改的数据和可执行工具；
Human-in-the-loop 应放在有副作用的变更应用边界，而不是只做提示文案。
```

来源：

- [Codex app](https://openai.com/index/introducing-the-codex-app/)
- [OpenAI Agents SDK Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [OpenAI Agents SDK Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/)

### 3.4 Unity 配置与遥测

Unity Remote Config 将配置键映射到游戏代码变量，使数值可以独立于代码调整；Unity Analytics 建议围绕明确问题设计事件，例如关卡难度和教学完成情况；Unity Game Overrides 的 A/B 文档要求控制组、变体、目标指标和足够样本，并建议一次只测试一个主要变化。

本地原型不接这些云服务，但采用相同工程原则：

- 配置字段必须真实映射到 Unity 运行变量。
- 先定义策划目标，再定义 telemetry。
- 每次修改保留基础版本、变更内容和运行证据。
- 单次手动试玩只称为 Run 前后对比，不称为统计学 A/B 测试。

来源：

- [Unity Remote Config](https://docs.unity.com/en-us/remote-config)
- [Unity Analytics Events](https://docs.unity.com/en-us/analytics/events/events)
- [Unity Game Overrides A/B testing](https://docs.unity.com/en-us/game-overrides/ab-testing)

## 4. 新手试炼配置包边界

只支持以下垂直切片：

```text
单角色
单武器
一个主动技能
三波敌人
首通奖励
三段武器升级
运行目标
```

现有配置组保持名称不变，并增加新组或新字段：

| 配置组 | 本阶段字段范围 |
|---|---|
| `item_config` | 物品、货币和材料定义 |
| `weapon_config` | 武器类型、基础攻击、强度档位 |
| `upgrade_config` | 等级、攻击加成、多资源消耗 |
| `reward_config` | 保留现有字段，增加带数量的 `reward_items` |
| `enemy_config` | 敌人 ID、角色类型、生命、攻击、移动速度 |
| `wave_config` | 波次、敌人 ID、数量 |
| `skill_config` | 伤害、冷却、范围 |
| `runtime_target_config` | 通关时间、击败数、技能使用和经济目标 |

明确不做：

```text
多人副本
角色养成全系统
抽卡和付费经济
装备随机词条
任务链和剧情系统
商店和活动系统
真实玩家分群实验
```

## 5. 配置契约演进

### 5.1 兼容原则

- 不重命名现有四个配置组和已有字段。
- 新字段和新配置组使用英文稳定字段名。
- Runtime Contract 升级为版本化契约，Unity Loader 在迁移期兼容 `1.0` 和 `2.0`。
- Phase 0 到 Phase 3 的历史 fixture 继续走 v1 兼容路径。
- 新的 Starter Trial 流程使用 v2，不偷偷从 Classic Case Profile 补充模型声称已生成的字段。

### 5.2 奖励数量

推荐在 v2 `reward_config` 中增加：

```json
{
  "reward_items": [
    {"item_id": "item_training_sword", "amount": 1},
    {"item_id": "item_gold", "amount": 100},
    {"item_id": "item_refine_stone", "amount": 1}
  ]
}
```

Reference Checker 必须校验每个 `item_id`，Rule Engine 必须校验数量为正数和首通奖励约束。

### 5.3 目标来源统一

当前 Classic Case Profile 与 Runtime Contract 都可能提供通关时间目标。v2 必须建立单一来源：

```text
requirement constraint
-> runtime_target_config
-> Unity contract targets
-> runtime evaluator
-> Web Console evidence
```

任何展示层不得维护另一套独立目标值。

## 6. 需求准入与语义对齐

### 6.1 新配置需求入口

自由文本只进入 Requirement Intake，不承担启动 Unity、打开报告或运行 Benchmark 等命令。

输出契约：

```json
{
  "decision": "accepted | needs_clarification | rejected",
  "capability": "starter_trial_config | unsupported",
  "reason": "string",
  "missing_information": [],
  "conflicts": [],
  "constraints": [],
  "normalized_requirement": "string"
}
```

`constraints` 需要记录原文片段、目标字段、操作符和值，使生成后的 Semantic Alignment 可以逐项核对。

### 6.2 修改当前配置入口

Change Request Intake 必须绑定：

```text
base_run_id
base_config_hash
当前 final_configs 快照
当前失败检查项
策划修改要求
```

不允许修改未列入 Capability Registry 的字段，也不允许从自由文本直接调用工具。

## 7. Config Diff 与人工确认

第一版使用受限 Change Set，不接受任意 JSONPath 或任意代码：

```json
{
  "change_set_id": "change_xxx",
  "base_run_id": "run_xxx",
  "base_config_hash": "sha256",
  "status": "proposed",
  "operations": [
    {
      "config_group": "enemy_config",
      "row_id": "enemy_training_elite",
      "field": "max_health",
      "before": 700,
      "after": 900,
      "reason": "延长精英战斗时长",
      "source_requirement": "提高精英敌人的生命值"
    }
  ]
}
```

状态机：

```text
proposed
-> approved -> applied -> validated -> child_run_prepared
-> rejected
-> invalidated（基础配置已变化）
```

应用前必须检查 `base_config_hash`，防止把旧 Diff 应用到新配置。确认动作需要记录确认时间和最终应用结果。

## 8. Run A / Run B 关系

子运行 Manifest 增加：

```text
parent_run_id
change_set_id
comparison_group_id
```

比较报告至少展示：

| 指标 | Run A | Run B | 策划目标 | 判断 |
|---|---:|---:|---:|---|
| 通关时间 | 实测 | 实测 | 60–90s | 改善 / 退化 / 未变化 |
| 击败敌人 | 实测 | 实测 | 5 | 通过 / 失败 |
| 技能使用 | 实测 | 实测 | >=1 | 通过 / 失败 |
| 连续升级两次 | 是 / 否 | 是 / 否 | 否 | 修复 / 未修复 |

报告必须同时显示配置 Diff 和 telemetry 证据，不能只根据文字建议宣称改善。

## 9. 实施阶段

### Phase 8A：契约与能力目录

- 定义 Starter Trial Capability Registry。
- 定义 v2 structured requirement 和 config schema。
- 增加 reward quantities、enemy、wave、skill 和 runtime targets。
- 统一 Classic Case、Unity Contract、Evaluator 和 Web Console 的目标来源。
- 增加 v1 到 v2 兼容适配和契约测试。
- 更新 Unity Loader，使新增字段真实驱动运行变量。

验收门槛：策划口头可修改的每个字段，都能在 JSON、Unity 变量和 telemetry/evaluation 中找到明确映射。

### Phase 8B：Requirement Intake 与 Semantic Alignment

- 新增 Requirement Intake Service / Tool，不命名为 Agent。
- 支持 `accepted`、`needs_clarification` 和 `rejected`。
- 提取带 source span 的结构化约束。
- 新增生成后语义对齐检查。
- 建立支持需求、信息缺失、冲突、越界和无关输入数据集。
- Web Console 展示支持范围、缺失信息和约束映射。

验收门槛：无关输入不进入 Generator；明确约束可以从原文追踪到最终配置字段。

### Phase 8C：Change Request、Diff 与 Approval

- 新增受限 Change Request Intake。
- 只支持 Capability Registry 中的可修改字段。
- 生成 typed Change Set 和影响说明。
- Web Console 展示修改前、修改后、原因和影响范围。
- 策划明确批准后才应用。
- 应用后重新运行 Schema、Reference、Rule 和 Semantic Alignment。

验收门槛：任何配置变化都有提议、人工决定、应用结果和配置哈希证据。

### Phase 8D：子运行与前后对比

- 用已批准 Change Set 创建 child run。
- 导出独立 v2 Unity Contract。
- 支持手动试玩和自动回归生成 Run B telemetry。
- 新增 Run A / Run B 比较服务、API、JSON 和 Markdown 报告。
- Web Console 展示配置变化、指标变化和目标达成状态。

验收门槛：面试演示可以从 Run A 的失败证据进入修改确认，再生成 Run B 的独立证据并完成对比。

### Phase 8E：评测与演示收口

- 增加 8–12 条 Requirement Intake hardcases。
- 增加 6–10 条 Change Request hardcases。
- 覆盖越界字段、冲突修改、过期 config hash 和非法引用。
- 记录 requirement decision accuracy、constraint match rate、change apply pass rate 和 comparison completeness。
- 运行完整 pytest、frontend build、Unity C# 编译、自动回归和人工试玩验收。
- 更新中文指南、演示脚本和项目边界说明。

验收门槛：所有指标有数据集定义和证据文件，不把单次 Run 前后对比描述为统计学 A/B 实验。

## 10. 计划输出

建议新增以下 artifact，不修改已有 artifact 字段：

```text
outputs/runtime_runs/{run_id}/requirement_intake.json
outputs/runtime_runs/{run_id}/semantic_alignment.json
outputs/change_sets/{change_set_id}/change_set.json
outputs/change_sets/{change_set_id}/approval.json
outputs/comparisons/{comparison_group_id}/run_comparison.json
outputs/comparisons/{comparison_group_id}/run_comparison_report.md
```

建议新增只读或受限写入 API：

```text
POST /api/requirements/intake
POST /api/runtime-runs/{run_id}/change-sets
POST /api/change-sets/{change_set_id}/approve
POST /api/change-sets/{change_set_id}/reject
POST /api/change-sets/{change_set_id}/apply
GET  /api/runtime-runs/{run_id}/comparison/{other_run_id}
```

API 命名和最终字段需在 Phase 8A 完成 Schema Decision Record 后冻结。

## 11. 风险与控制

| 风险 | 控制方式 |
|---|---|
| Schema 扩展过大 | 只覆盖单角色、单武器、单技能和三波敌人 |
| LLM 生成合法但答非所问 | Requirement Intake + Semantic Alignment 双门禁 |
| 修改请求误改多个字段 | typed allowlist + Diff + 人工批准 |
| Diff 应用到错误版本 | `base_config_hash` 乐观并发检查 |
| Unity 仍使用固定值 | 契约映射测试和 C# runtime smoke |
| 单次试玩波动被夸大 | 明确记录 manual/auto，称为工程前后对比 |
| 多次改动无法解释结果 | 第一版推荐一次只确认一个主要调优目标 |
| 为 Agent 数量牺牲清晰度 | 新模块默认实现为 Tool / Service |

## 12. 完成定义

Milestone 8 只有在以下条件全部满足时才能标记 complete：

- 新手试炼需求可以被真实 v2 Schema 表达。
- 每个可调字段真实驱动 Unity，而不是只存在于 Web Console。
- Requirement Intake 能正确接受、澄清和拒绝测试样本。
- 明确需求约束可以追踪到最终配置。
- 修改要求生成受限 Diff，未经批准不会应用。
- Run B 保存 parent run、Change Set 和独立 telemetry。
- 对比报告同时引用配置变化和运行证据。
- Mock 默认路径、Phase 0–3 CLI 和现有 artifacts 保持可用。
- Python、前端和 Unity 测试通过。
- 用户完成一次可视手动 Run A / Run B 验收。

