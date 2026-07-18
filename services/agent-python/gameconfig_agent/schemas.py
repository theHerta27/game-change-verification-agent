"""Shared schema constants for deterministic GameConfig validation."""

STRUCTURED_REQUIREMENT_FIELDS = {
    "request_id": str,
    "item_name": str,
    "category": str,
    "base_attack": int,
    "upgrade_times": int,
    "upgrade_attack_bonus": int,
    "cost_item_tags": list,
    "reward_channel": str,
    "once_only": bool,
}

ITEM_FIELDS = {
    "item_id": str,
    "display_name": str,
    "item_type": str,
    "rarity": str,
}

WEAPON_FIELDS = {
    "weapon_id": str,
    "item_id": str,
    "weapon_type": str,
    "base_attack": int,
    "strength_tier": str,
}

UPGRADE_FIELDS = {
    "weapon_id": str,
    "level": int,
    "attack_bonus": int,
    "cost_items": list,
}

REWARD_FIELDS = {
    "reward_id": str,
    "quest_id": str,
    "reward_item_id": str,
    "weapon_id": str,
    "once_only": bool,
    "source": str,
}

REWARD_ITEM_FIELDS = {
    "item_id": str,
    "amount": int,
}

ENEMY_FIELDS = {
    "enemy_id": str,
    "display_name": str,
    "role": str,
    "max_health": int,
    "attack": int,
    "move_speed": (int, float),
}

WAVE_FIELDS = {
    "wave": int,
    "enemy_id": str,
    "count": int,
}

SKILL_FIELDS = {
    "skill_id": str,
    "display_name": str,
    "damage": int,
    "cooldown": (int, float),
    "range": (int, float),
}

RUNTIME_TARGET_FIELDS = {
    "target_id": str,
    "completion_time_seconds_min": (int, float),
    "completion_time_seconds_max": (int, float),
    "enemies_defeated": int,
    "skill_uses_min": int,
    "first_upgrade_affordable": bool,
    "second_upgrade_affordable": bool,
}

CONFIG_GROUPS = ("item_config", "weapon_config", "upgrade_config", "reward_config")
OPTIONAL_CONFIG_GROUPS = ("enemy_config", "wave_config", "skill_config", "runtime_target_config")
ALL_CONFIG_GROUPS = CONFIG_GROUPS + OPTIONAL_CONFIG_GROUPS

ENUMS = {
    "item_type": {"weapon", "currency", "material"},
    "rarity": {"common", "uncommon", "rare"},
    "weapon_type": {"sword", "bow", "staff"},
    "strength_tier": {"common", "uncommon", "rare"},
    "source": {"beginner_quest", "event", "shop"},
}
