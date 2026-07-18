# Validation Report

## Initial Validation
- Error count: 4
- `Reference Checker Tool` `missing_reference` at `upgrade_config[0].cost_items[1].item_id`: 'item_refine_stone' does not exist in item_config.item_id.
- `Rule Engine Tool` `non_continuous_upgrade_levels` at `upgrade_config.level`: Expected levels [1, 2, 3], got [1, 3].
- `Rule Engine Tool` `zero_gold_cost` at `upgrade_config.cost_items[item_gold].amount`: Gold cost must be positive for upgrade progression.
- `Rule Engine Tool` `beginner_reward_not_once_only` at `reward_config[0].once_only`: Beginner quest reward must be once_only=true.

## Final Validation
- Passed: True
- Error count: 0
