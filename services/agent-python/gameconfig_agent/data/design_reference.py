"""Deterministic design reference data, not an agent."""

RESOURCE_ITEM_CATALOG = {
    "item_gold": {"item_id": "item_gold", "display_name": "Gold", "item_type": "currency", "rarity": "common"},
    "item_refine_stone": {"item_id": "item_refine_stone", "display_name": "Refine Stone", "item_type": "material", "rarity": "common"},
    "item_exp_book": {"item_id": "item_exp_book", "display_name": "EXP Book", "item_type": "material", "rarity": "common"},
    "item_skill_manual": {"item_id": "item_skill_manual", "display_name": "Skill Manual", "item_type": "material", "rarity": "common"},
    "item_trial_medal": {"item_id": "item_trial_medal", "display_name": "Trial Medal", "item_type": "material", "rarity": "common"},
}

BALANCE_POLICY_LOOKUP = {
    "beginner_weapon": {
        "base_attack_range": [35, 55],
        "upgrade_bonus_range": [3, 8],
        "recommended_gold_cost": [100, 150, 200],
        "recommended_refine_stone_cost": [1, 2, 3],
        "reward_once_only": True,
        "max_reward_strength": "common",
    },
    "rare_weapon": {
        "base_attack_range": [90, 130],
        "upgrade_bonus_range": [8, 15],
        "recommended_gold_cost": [300, 450, 650],
        "recommended_refine_stone_cost": [3, 5, 8],
        "reward_once_only": True,
        "max_reward_strength": "rare",
    }
}
