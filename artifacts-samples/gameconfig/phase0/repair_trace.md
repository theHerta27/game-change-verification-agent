# Repair Trace

## Action 1: set_base_attack
- Scope: `weapon_config.base_attack`
- Before: `80`
- After: `50`
- Reason: Align with original requirement and beginner policy.

## Action 2: add_missing_item_reference
- Scope: `item_config`
- Before: `null`
- After: `{"item_id": "item_refine_stone", "display_name": "Refine Stone", "item_type": "material", "rarity": "common"}`
- Reason: Referenced item is known by the deterministic resource catalog.

## Action 3: normalize_upgrade_level
- Scope: `upgrade_config[level=1]`
- Before: `{"weapon_id": "weapon_training_sword", "level": 1, "attack_bonus": 5, "cost_items": [{"item_id": "item_gold", "amount": 0}, {"item_id": "item_refine_stone", "amount": 1}]}`
- After: `{"weapon_id": "weapon_training_sword", "level": 1, "attack_bonus": 5, "cost_items": [{"item_id": "item_gold", "amount": 100}, {"item_id": "item_refine_stone", "amount": 1}]}`
- Reason: Repair coupled level, attack bonus, and cost fields locally.

## Action 4: normalize_upgrade_level
- Scope: `upgrade_config[level=2]`
- Before: `null`
- After: `{"weapon_id": "weapon_training_sword", "level": 2, "attack_bonus": 5, "cost_items": [{"item_id": "item_gold", "amount": 150}, {"item_id": "item_refine_stone", "amount": 2}]}`
- Reason: Repair coupled level, attack bonus, and cost fields locally.

## Action 5: normalize_upgrade_level
- Scope: `upgrade_config[level=3]`
- Before: `{"weapon_id": "weapon_training_sword", "level": 3, "attack_bonus": 5, "cost_items": [{"item_id": "item_gold", "amount": 0}, {"item_id": "item_refine_stone", "amount": 3}]}`
- After: `{"weapon_id": "weapon_training_sword", "level": 3, "attack_bonus": 5, "cost_items": [{"item_id": "item_gold", "amount": 200}, {"item_id": "item_refine_stone", "amount": 3}]}`
- Reason: Repair coupled level, attack bonus, and cost fields locally.

## Action 6: set_reward_once_only
- Scope: `reward_config.once_only`
- Before: `false`
- After: `true`
- Reason: Beginner quest reward must be one-time.
