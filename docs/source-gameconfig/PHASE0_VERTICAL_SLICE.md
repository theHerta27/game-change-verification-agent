# Phase 0 垂直切片

## 输入

```text
设计一个新手武器 Training Sword，基础攻击力 50，可升级 3 次，每级攻击力 +5。升级消耗金币和强化石。该武器作为新手任务奖励发放，只能领取一次。
```

## 故意有缺陷的草案

Mock Generator Agent 会故意生成结构完整但有问题的配置：

- `base_attack = 80`，与需求中的 `50` 不一致。
- `upgrade_config` 只有 level 1 和 level 3，缺少 level 2。
- 金币消耗为 `0`。
- `item_refine_stone` 被引用，但没有在 `item_config` 中定义。
- `reward_config.once_only = false`。

## Validation Errors 设计

Schema Validator 预期通过，因为草案结构是完整的。

Reference Checker 预期发现：

- `upgrade_config[*].cost_items[*].item_id = item_refine_stone` 缺少 `item_config` 定义。

Rule Engine 预期发现：

- 升级等级不连续。
- 金币消耗不能为 0。
- 新手任务奖励必须 `once_only=true`。

## Review Findings 设计

Reviewer 输出两个部分：

- Balance & Consistency Review：攻击力、升级等级、金币曲线。
- Risk Review：重复领取风险、缺失引用风险。

Reviewer 不直接修改配置。

## Repair Actions 设计

Repair Agent 在 bounded scope 内执行：

- 将 `base_attack` 修复为 `50`。
- 添加 `item_refine_stone` 基础 item 定义。
- 补齐 level 1、2、3，并设置每级 `attack_bonus = 5`。
- 设置金币曲线 `100, 150, 200`。
- 设置强化石曲线 `1, 2, 3`。
- 将 `reward_config.once_only` 修复为 `true`。

## 最终输出

最终 `final_configs.json` 应满足：

- `base_attack = 50`
- upgrade levels 为 `1, 2, 3`
- 每级 `attack_bonus = 5`
- gold cost 为 `100, 150, 200`
- `item_refine_stone` 引用存在
- `reward_config.once_only = true`
- schema/reference/rule validation 全部通过

## Trace 示例

```json
{
  "step": 1,
  "actor": "Config Generator Agent",
  "actor_type": "agent",
  "action": "generate_draft_configs",
  "input_refs": ["requirement_text", "design_reference"],
  "output_refs": ["structured_requirement", "draft_configs", "assumptions"],
  "status": "succeeded"
}
```
