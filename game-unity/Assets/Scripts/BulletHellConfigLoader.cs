using System;
using System.IO;
using UnityEngine;

namespace GameConfig.Runtime
{
    public static class BulletHellConfigLoader
    {
        public static BulletHellContract Load()
        {
            string path = ConfigPath(Environment.GetCommandLineArgs());
            if (!File.Exists(path)) throw new FileNotFoundException("Bullet Hell config was not found.", path);
            string text = File.ReadAllText(path);
            if (string.IsNullOrWhiteSpace(text)) throw new InvalidDataException("Bullet Hell config is empty.");
            BulletHellContract contract = JsonUtility.FromJson<BulletHellContract>(text);
            Validate(contract);
            return contract;
        }

        public static string ConfigPath(string[] args)
        {
            int index = Array.IndexOf(args, "--config-input");
            return index >= 0 && index + 1 < args.Length
                ? Path.GetFullPath(args[index + 1])
                : Path.Combine(Application.streamingAssetsPath, "bullet_hell_config.json");
        }

        public static void Validate(BulletHellContract contract)
        {
            if (contract == null || contract.bullet_hell_contract_version != "1.0")
                throw new InvalidDataException("bullet_hell_contract_version must be 1.0.");
            if (contract.scenario == null || contract.player == null || contract.boss == null)
                throw new InvalidDataException("scenario, player, and boss are required.");
            if (contract.phases == null || contract.phases.Length < 2 || contract.phases.Length > 3)
                throw new InvalidDataException("Bullet Hell requires two or three phases.");
            if (contract.constraints == null || contract.runtime_targets == null)
                throw new InvalidDataException("constraints and runtime_targets are required.");
            if (contract.scenario.duration_seconds < 30f || contract.scenario.duration_seconds > 60f)
                throw new InvalidDataException("duration_seconds must be between 30 and 60.");
            float previousTrigger = 2f;
            for (int index = 0; index < contract.phases.Length; index++)
            {
                BulletHellPhase phase = contract.phases[index];
                if (phase == null || phase.trigger == null || phase.pattern == null)
                    throw new InvalidDataException($"phases[{index}] is incomplete.");
                if (phase.trigger.type != "boss_hp_below" || phase.trigger.value <= 0f || phase.trigger.value > 1f)
                    throw new InvalidDataException($"phases[{index}].trigger is invalid.");
                if (phase.trigger.value > previousTrigger)
                    throw new InvalidDataException("Phase triggers must be ordered from high to low.");
                previousTrigger = phase.trigger.value;
                ValidatePattern(phase.pattern, index);
            }
        }

        private static void ValidatePattern(BulletHellPattern pattern, int index)
        {
            if (Array.IndexOf(new[] { "ring", "aimed_fan", "spiral", "petal" }, pattern.type) < 0)
                throw new InvalidDataException($"phases[{index}].pattern.type is unsupported.");
            if (pattern.bullets_per_wave < 1 || pattern.bullets_per_wave > 64)
                throw new InvalidDataException($"phases[{index}].pattern.bullets_per_wave is outside 1..64.");
            if (pattern.wave_interval_ms < 100 || pattern.wave_interval_ms > 5000)
                throw new InvalidDataException($"phases[{index}].pattern.wave_interval_ms is outside 100..5000.");
            if (pattern.bullet_speed < 0.5f || pattern.bullet_speed > 12f)
                throw new InvalidDataException($"phases[{index}].pattern.bullet_speed is outside 0.5..12.");
            if (pattern.bullet_lifetime_seconds < 0.5f || pattern.bullet_lifetime_seconds > 12f)
                throw new InvalidDataException($"phases[{index}].pattern.bullet_lifetime_seconds is outside 0.5..12.");
            if (pattern.layer_count < 1 || pattern.layer_count > 4)
                throw new InvalidDataException($"phases[{index}].pattern.layer_count is outside 1..4.");
            if (pattern.type == "petal" && pattern.layer_count < 2)
                throw new InvalidDataException($"phases[{index}].petal requires at least two layers.");
        }
    }
}
