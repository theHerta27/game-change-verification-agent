using System;

namespace GameConfig.Runtime
{
    [Serializable]
    public sealed class BulletHellContract
    {
        public string bullet_hell_contract_version;
        public string source;
        public BulletHellScenario scenario;
        public BulletHellPlayer player;
        public BulletHellBoss boss;
        public BulletHellPhase[] phases;
        public BulletHellConstraints constraints;
        public BulletHellRuntimeTargets runtime_targets;
    }

    [Serializable] public sealed class BulletHellScenario { public string scenario_id; public string display_name; public float duration_seconds; public float arena_width; public float arena_height; }
    [Serializable] public sealed class BulletHellPlayer { public int max_health; public float move_speed; public float focus_speed_multiplier; public float hit_radius; public float start_x; public float start_z; public int auto_fire_damage; public float auto_fire_interval_seconds; }
    [Serializable] public sealed class BulletHellBoss { public string boss_id; public string display_name; public int max_health; public float position_x; public float position_z; }
    [Serializable] public sealed class BulletHellPhase { public string phase_id; public string display_name; public BulletHellTrigger trigger; public BulletHellPattern pattern; }
    [Serializable] public sealed class BulletHellTrigger { public string type; public float value; }
    [Serializable] public sealed class BulletHellPattern { public string type; public int bullets_per_wave; public int wave_interval_ms; public float bullet_speed; public float bullet_lifetime_seconds; public float rotation_per_wave_deg; public float spread_angle_deg; public int layer_count; public bool bidirectional; }
    [Serializable] public sealed class BulletHellConstraints { public int max_alive_bullets; public float min_fps; public int max_player_hits; }
    [Serializable] public sealed class BulletHellRuntimeTargets { public int max_alive_bullets; public int max_player_hits; public float min_survival_seconds; public float min_fps; public bool require_all_phases; }

    [Serializable]
    public sealed class BulletHellTelemetry
    {
        public string scenario_id;
        public string bullet_hell_contract_version;
        public string status;
        public string run_mode;
        public int random_seed;
        public float duration_seconds;
        public int total_bullets_spawned;
        public int peak_alive_bullets;
        public float bullets_per_second;
        public int player_hits;
        public float player_survival_seconds;
        public float average_fps;
        public float low_percentile_fps;
        public float minimum_fps;
        public int exception_log_count;
        public int frame_count;
        public string exported_at_utc;
        public BulletHellPhaseTelemetry[] phase_results;
    }

    [Serializable]
    public sealed class BulletHellPhaseTelemetry
    {
        public string phase_id;
        public string pattern_type;
        public float started_at_seconds;
        public float duration_seconds;
        public int bullets_spawned;
        public int player_hits;
        public int peak_alive_bullets;
    }
}
