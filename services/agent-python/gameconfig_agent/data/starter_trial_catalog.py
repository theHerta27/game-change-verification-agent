"""Deterministic capability catalog for the starter trial tuning loop."""

from __future__ import annotations


STARTER_TRIAL_CAPABILITY = {
    "capability": "starter_trial_config",
    "contract_versions": ["1.0", "2.0"],
    "required_groups": ["item_config", "weapon_config", "upgrade_config", "reward_config"],
    "optional_groups": ["enemy_config", "wave_config", "skill_config", "runtime_target_config"],
    "change_field_allowlist": {
        "weapon_config": ["base_attack"],
        "upgrade_config": ["attack_bonus", "cost_items"],
        "reward_config": ["once_only", "reward_items"],
        "enemy_config": ["max_health", "attack", "move_speed"],
        "wave_config": ["enemy_id", "count"],
        "skill_config": ["damage", "cooldown", "range"],
        "runtime_target_config": [
            "completion_time_seconds_min",
            "completion_time_seconds_max",
            "enemies_defeated",
            "skill_uses_min",
            "first_upgrade_affordable",
            "second_upgrade_affordable",
        ],
    },
    "unsupported_scope_examples": [
        "multiplayer dungeon",
        "gacha economy",
        "quest chain",
        "shop event schedule",
        "character art generation",
    ],
}


STARTER_TRIAL_DEFAULT_V2_CONFIGS = {
    "enemy_config": [
        {
            "enemy_id": "enemy_training_dummy",
            "display_name": "Training Dummy",
            "role": "normal",
            "max_health": 180,
            "attack": 8,
            "move_speed": 2.2,
        },
        {
            "enemy_id": "enemy_training_guard",
            "display_name": "Training Guard",
            "role": "normal",
            "max_health": 260,
            "attack": 12,
            "move_speed": 2.5,
        },
        {
            "enemy_id": "enemy_training_elite",
            "display_name": "Training Elite",
            "role": "elite",
            "max_health": 700,
            "attack": 18,
            "move_speed": 2.0,
        },
    ],
    "wave_config": [
        {"wave": 1, "enemy_id": "enemy_training_dummy", "count": 2},
        {"wave": 2, "enemy_id": "enemy_training_guard", "count": 2},
        {"wave": 3, "enemy_id": "enemy_training_elite", "count": 1},
    ],
    "skill_config": [
        {
            "skill_id": "skill_training_slash",
            "display_name": "Training Slash",
            "damage": 100,
            "cooldown": 5.0,
            "range": 4.5,
        }
    ],
    "runtime_target_config": [
        {
            "target_id": "target_beginner_trial_baseline",
            "completion_time_seconds_min": 60.0,
            "completion_time_seconds_max": 90.0,
            "enemies_defeated": 5,
            "skill_uses_min": 1,
            "first_upgrade_affordable": True,
            "second_upgrade_affordable": False,
        }
    ],
}
