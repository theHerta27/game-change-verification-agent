# Test Scenario Report

- Scenario count: 7
- Source agent: Test Scenario Agent

## scenario_weapon_base_attack
- Title: Training Sword base attack matches beginner requirement
- Priority: high
- Coverage tags: `base_attack_exact`
- Expected result: base_attack is 50 and equals 50.

## scenario_weapon_item_reference
- Title: Weapon item reference resolves to item_config
- Priority: high
- Coverage tags: `weapon_item_reference`
- Expected result: item_training_sword exists in item_config.

## scenario_upgrade_levels_and_bonus
- Title: Upgrade levels are continuous and grant +5 attack
- Priority: high
- Coverage tags: `upgrade_levels_continuous, upgrade_bonus_per_level`
- Expected result: Upgrade levels are [1, 2, 3] and each attack_bonus is 5.

## scenario_upgrade_gold_cost_curve
- Title: Upgrade gold costs follow beginner curve
- Priority: medium
- Coverage tags: `gold_cost_curve`
- Expected result: Gold costs are [100, 150, 200].

## scenario_upgrade_material_cost_curve
- Title: Upgrade material costs follow beginner curve
- Priority: medium
- Coverage tags: `material_cost_curve`
- Expected result: Refine stone costs are [1, 2, 3].

## scenario_reward_once_only
- Title: Beginner quest reward can only be claimed once
- Priority: critical
- Coverage tags: `reward_once_only`
- Expected result: once_only is True and duplicate claim is rejected.

## scenario_reward_item_reference
- Title: Reward item and weapon references resolve
- Priority: high
- Coverage tags: `reward_item_reference`
- Expected result: Reward references resolve to final item and weapon configs.
