using System;

namespace GameConfig.Runtime
{
    [Serializable]
    public sealed class RuntimeContract
    {
        public string contract_version;
        public string source;
        public ConfigGroups configs;
        public RuntimeScenario runtime_scenario;
    }

    [Serializable] public sealed class ConfigGroups { public ItemConfig[] item_config; public WeaponConfig[] weapon_config; public UpgradeConfig[] upgrade_config; public RewardConfig[] reward_config; public EnemyConfig[] enemy_config; public WaveConfig[] wave_config; public SkillConfig[] skill_config; public RuntimeTargetConfig[] runtime_target_config; }
    [Serializable] public sealed class ItemConfig { public string item_id; public string display_name; public string item_type; public string rarity; }
    [Serializable] public sealed class WeaponConfig { public string weapon_id; public string item_id; public string weapon_type; public int base_attack; public string strength_tier; }
    [Serializable] public sealed class UpgradeConfig { public string weapon_id; public int level; public int attack_bonus; public CostItem[] cost_items; }
    [Serializable] public sealed class CostItem { public string item_id; public int amount; }
    [Serializable] public sealed class RewardConfig { public string reward_id; public string quest_id; public string reward_item_id; public string weapon_id; public bool once_only; public string source; public RewardItem[] reward_items; }
    [Serializable] public sealed class RewardItem { public string item_id; public int amount; }

    [Serializable]
    public sealed class RuntimeScenario
    {
        public string scenario_id;
        public string display_name;
        public PlayerConfig player;
        public SkillConfig skill;
        public EnemyConfig[] enemies;
        public WaveConfig[] waves;
        public RuntimeTargets targets;
    }

    [Serializable] public sealed class PlayerConfig { public int max_health; public float move_speed; public float attack_range; public float attack_cooldown; }
    [Serializable] public sealed class SkillConfig { public string skill_id; public string display_name; public int damage; public float cooldown; public float range; }
    [Serializable] public sealed class EnemyConfig { public string enemy_id; public string display_name; public string role; public int max_health; public int attack; public float move_speed; }
    [Serializable] public sealed class WaveConfig { public int wave; public string enemy_id; public int count; }
    [Serializable] public sealed class RuntimeTargets { public int normal_enemy_hits_to_kill_min; public int normal_enemy_hits_to_kill_max; public float completion_time_seconds_min; public float completion_time_seconds_max; public int enemies_defeated; public int skill_uses_min; public bool first_upgrade_affordable; public bool second_upgrade_affordable; }
    [Serializable] public sealed class RuntimeTargetConfig { public string target_id; public float completion_time_seconds_min; public float completion_time_seconds_max; public int enemies_defeated; public int skill_uses_min; public bool first_upgrade_affordable; public bool second_upgrade_affordable; }

    [Serializable]
    public sealed class RuntimeTelemetry
    {
        public string scenario_id;
        public string contract_version;
        public string status;
        public int waves_completed;
        public int enemies_defeated;
        public int basic_attacks;
        public int skill_uses;
        public int damage_dealt;
        public int damage_taken;
        public int gold_earned;
        public int gold_spent;
        public int final_attack;
        public float completion_time_seconds;
        public string exported_at_utc;
    }
}
