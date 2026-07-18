"""Phase 3 benchmark dataset and hard cases."""

from __future__ import annotations

from copy import deepcopy


def _requirement(
    sample_id: str,
    text: str,
    *,
    item_name: str,
    category: str,
    base_attack: int,
    upgrade_times: int,
    upgrade_attack_bonus: int,
    once_only: bool,
) -> dict:
    return {
        "sample_id": sample_id,
        "requirement_text": text,
        "structured_requirement": {
            "request_id": f"req_{sample_id}",
            "item_name": item_name,
            "category": category,
            "base_attack": base_attack,
            "upgrade_times": upgrade_times,
            "upgrade_attack_bonus": upgrade_attack_bonus,
            "cost_item_tags": ["gold", "refine_stone"],
            "reward_channel": "beginner_quest" if category == "beginner_weapon" else "event",
            "once_only": once_only,
        },
    }


def _weapon_configs(
    *,
    item_id: str,
    weapon_id: str,
    display_name: str,
    base_attack: int,
    levels: list[int],
    bonus: int,
    gold_costs: list[int],
    once_only: bool,
    include_refine_stone: bool = True,
    duplicate_reward: bool = False,
    missing_reward_item: bool = False,
    rarity: str = "common",
    source: str = "beginner_quest",
) -> dict:
    item_config = [
        {"item_id": item_id, "display_name": display_name, "item_type": "weapon", "rarity": rarity},
        {"item_id": "item_gold", "display_name": "Gold", "item_type": "currency", "rarity": "common"},
    ]
    if include_refine_stone:
        item_config.append(
            {
                "item_id": "item_refine_stone",
                "display_name": "Refine Stone",
                "item_type": "material",
                "rarity": "common",
            }
        )
    upgrade_config = []
    for index, level in enumerate(levels):
        upgrade_config.append(
            {
                "weapon_id": weapon_id,
                "level": level,
                "attack_bonus": bonus,
                "cost_items": [
                    {"item_id": "item_gold", "amount": gold_costs[index]},
                    {"item_id": "item_refine_stone", "amount": index + 1},
                ],
            }
        )
    reward_item_id = "item_missing_reward" if missing_reward_item else item_id
    reward = {
        "reward_id": f"reward_{weapon_id}",
        "quest_id": f"quest_{weapon_id}",
        "reward_item_id": reward_item_id,
        "weapon_id": weapon_id,
        "once_only": once_only,
        "source": source,
    }
    reward_config = [reward]
    if duplicate_reward:
        dup = deepcopy(reward)
        dup["quest_id"] = f"quest_{weapon_id}_duplicate"
        reward_config.append(dup)
    return {
        "item_config": item_config,
        "weapon_config": [
            {
                "weapon_id": weapon_id,
                "item_id": item_id,
                "weapon_type": "sword",
                "base_attack": base_attack,
                "strength_tier": rarity,
            }
        ],
        "upgrade_config": upgrade_config,
        "reward_config": reward_config,
    }


BENCHMARK_SAMPLES = [
    {
        **_requirement(
            "beginner_weapon_flawed",
            "新手剑 Training Sword，攻击力 50，升级 3 次，每级 +5，金币和强化石消耗，一次性新手奖励。",
            item_name="Training Sword",
            category="beginner_weapon",
            base_attack=50,
            upgrade_times=3,
            upgrade_attack_bonus=5,
            once_only=True,
        ),
        "tags": ["beginner weapon", "missing reference", "reward once_only"],
        "draft_configs": _weapon_configs(
            item_id="item_training_sword",
            weapon_id="weapon_training_sword",
            display_name="Training Sword",
            base_attack=80,
            levels=[1, 3],
            bonus=5,
            gold_costs=[0, 0],
            once_only=False,
            include_refine_stone=False,
        ),
    },
    {
        **_requirement(
            "rare_weapon_flawed",
            "稀有武器 Moon Saber，攻击力 110，升级 3 次，每级 +10，活动奖励只能领取一次。",
            item_name="Moon Saber",
            category="rare_weapon",
            base_attack=110,
            upgrade_times=3,
            upgrade_attack_bonus=10,
            once_only=True,
        ),
        "tags": ["rare weapon", "upgrade cost"],
        "draft_configs": _weapon_configs(
            item_id="item_moon_saber",
            weapon_id="weapon_moon_saber",
            display_name="Moon Saber",
            base_attack=140,
            levels=[1, 2, 3],
            bonus=10,
            gold_costs=[0, 0, 0],
            once_only=True,
            rarity="rare",
            source="event",
        ),
    },
    {
        **_requirement(
            "upgrade_cost_negative",
            "新手斧配置：攻击力 45，升级三次，每级 +5，升级消耗不能为负。",
            item_name="Training Axe",
            category="beginner_weapon",
            base_attack=45,
            upgrade_times=3,
            upgrade_attack_bonus=5,
            once_only=True,
        ),
        "tags": ["upgrade cost"],
        "draft_configs": _weapon_configs(
            item_id="item_training_axe",
            weapon_id="weapon_training_axe",
            display_name="Training Axe",
            base_attack=45,
            levels=[1, 2, 3],
            bonus=5,
            gold_costs=[-10, 0, 0],
            once_only=True,
        ),
    },
    {
        **_requirement(
            "reward_once_only_false",
            "新手弓作为新手任务奖励，只能领取一次，攻击力 48，升级三次。",
            item_name="Training Bow",
            category="beginner_weapon",
            base_attack=48,
            upgrade_times=3,
            upgrade_attack_bonus=5,
            once_only=True,
        ),
        "tags": ["reward once_only"],
        "draft_configs": _weapon_configs(
            item_id="item_training_bow",
            weapon_id="weapon_training_bow",
            display_name="Training Bow",
            base_attack=48,
            levels=[1, 2, 3],
            bonus=5,
            gold_costs=[100, 150, 200],
            once_only=False,
        ),
    },
    {
        **_requirement(
            "duplicate_reward_hardcase",
            "活动奖励 Moon Saber 只能配置一份奖励，不能重复发放。",
            item_name="Moon Saber",
            category="rare_weapon",
            base_attack=110,
            upgrade_times=3,
            upgrade_attack_bonus=10,
            once_only=True,
        ),
        "tags": ["duplicate reward", "hardcase"],
        "draft_configs": _weapon_configs(
            item_id="item_moon_saber_dup",
            weapon_id="weapon_moon_saber_dup",
            display_name="Moon Saber",
            base_attack=110,
            levels=[1, 2, 3],
            bonus=10,
            gold_costs=[300, 450, 650],
            once_only=True,
            duplicate_reward=True,
            rarity="rare",
            source="event",
        ),
    },
    {
        **_requirement(
            "skill_damage_optional_config",
            "配置技能 Spark Slash，技能伤害倍率 1.2，绑定 Training Sword。",
            item_name="Training Sword",
            category="beginner_weapon",
            base_attack=50,
            upgrade_times=3,
            upgrade_attack_bonus=5,
            once_only=True,
        ),
        "tags": ["skill damage config", "optional skill_config"],
        "draft_configs": {
            **_weapon_configs(
                item_id="item_training_sword_skill",
                weapon_id="weapon_training_sword_skill",
                display_name="Training Sword",
                base_attack=50,
                levels=[1, 2, 3],
                bonus=5,
                gold_costs=[100, 150, 200],
                once_only=True,
            ),
            "skill_config": [
                {
                    "skill_id": "skill_spark_slash",
                    "weapon_id": "weapon_training_sword_skill",
                    "damage_multiplier": 1.2,
                }
            ],
        },
    },
    {
        **_requirement(
            "level_reward_curve",
            "等级奖励曲线每 5 级给一次新手材料，奖励引用必须存在。",
            item_name="Training Sword",
            category="beginner_weapon",
            base_attack=50,
            upgrade_times=3,
            upgrade_attack_bonus=5,
            once_only=True,
        ),
        "tags": ["level reward curve"],
        "draft_configs": {
            **_weapon_configs(
                item_id="item_training_sword_level",
                weapon_id="weapon_training_sword_level",
                display_name="Training Sword",
                base_attack=50,
                levels=[1, 2, 3],
                bonus=5,
                gold_costs=[100, 150, 200],
                once_only=True,
            ),
            "event_config": [
                {"event_id": "level_reward_5", "level": 5, "reward_item_id": "item_refine_stone"}
            ],
        },
    },
    {
        **_requirement(
            "missing_reward_reference",
            "奖励配置引用缺失时必须被识别，Training Sword 仍应保持合法。",
            item_name="Training Sword",
            category="beginner_weapon",
            base_attack=50,
            upgrade_times=3,
            upgrade_attack_bonus=5,
            once_only=True,
        ),
        "tags": ["missing reference"],
        "draft_configs": _weapon_configs(
            item_id="item_training_sword_missing_reward",
            weapon_id="weapon_training_sword_missing_reward",
            display_name="Training Sword",
            base_attack=50,
            levels=[1, 2, 3],
            bonus=5,
            gold_costs=[100, 150, 200],
            once_only=True,
            missing_reward_item=True,
        ),
    },
    {
        **_requirement(
            "safe_balanced_config",
            "安全平衡的新手剑配置，攻击力 50，升级三次，奖励一次性。",
            item_name="Training Sword",
            category="beginner_weapon",
            base_attack=50,
            upgrade_times=3,
            upgrade_attack_bonus=5,
            once_only=True,
        ),
        "tags": ["safe balanced config"],
        "draft_configs": _weapon_configs(
            item_id="item_training_sword_safe",
            weapon_id="weapon_training_sword_safe",
            display_name="Training Sword",
            base_attack=50,
            levels=[1, 2, 3],
            bonus=5,
            gold_costs=[100, 150, 200],
            once_only=True,
        ),
    },
    {
        **_requirement(
            "dirty_schema_hardcase",
            "脏结构 hardcase：升级配置可能被模型输出成字符串，系统不能崩溃。",
            item_name="Training Sword",
            category="beginner_weapon",
            base_attack=50,
            upgrade_times=3,
            upgrade_attack_bonus=5,
            once_only=True,
        ),
        "tags": ["hardcase", "schema drift"],
        "draft_configs": _weapon_configs(
            item_id="item_training_sword_dirty",
            weapon_id="weapon_training_sword_dirty",
            display_name="Training Sword",
            base_attack=50,
            levels=[1, 2, 3],
            bonus=5,
            gold_costs=[100, 150, 200],
            once_only=True,
        )
        | {"upgrade_config": ["bad string"]},
    },
]
