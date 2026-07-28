using System;
using System.Collections.Generic;
using System.Linq;

namespace GameConfig.Runtime
{
    public sealed class BulletHellTelemetryRecorder
    {
        private readonly BulletHellContract contract;
        private readonly List<float> frameTimes = new();
        private readonly List<BulletHellPhaseTelemetry> phases = new();
        private BulletHellPhaseTelemetry currentPhase;

        public BulletHellTelemetry Data { get; }

        public BulletHellTelemetryRecorder(BulletHellContract contract, RuntimeRunSettings settings)
        {
            this.contract = contract;
            Data = new BulletHellTelemetry
            {
                scenario_id = contract.scenario.scenario_id,
                bullet_hell_contract_version = contract.bullet_hell_contract_version,
                status = "running",
                run_mode = settings.RunMode,
                random_seed = settings.RandomSeed,
                phase_results = Array.Empty<BulletHellPhaseTelemetry>(),
            };
        }

        public void BeginPhase(BulletHellPhase phase, float elapsed)
        {
            EndPhase(elapsed);
            currentPhase = new BulletHellPhaseTelemetry
            {
                phase_id = phase.phase_id,
                pattern_type = phase.pattern.type,
                started_at_seconds = elapsed,
            };
        }

        public void RecordFrame(float elapsed, float unscaledDeltaTime, int activeBullets)
        {
            Data.frame_count++;
            Data.peak_alive_bullets = Math.Max(Data.peak_alive_bullets, activeBullets);
            if (currentPhase != null)
                currentPhase.peak_alive_bullets = Math.Max(currentPhase.peak_alive_bullets, activeBullets);
            if (elapsed >= 2f && unscaledDeltaTime > 0f) frameTimes.Add(unscaledDeltaTime);
        }

        public void RecordBullets(int count)
        {
            Data.total_bullets_spawned += count;
            if (currentPhase != null) currentPhase.bullets_spawned += count;
        }

        public void RecordHit()
        {
            Data.player_hits++;
            if (currentPhase != null) currentPhase.player_hits++;
        }

        public void RecordException() => Data.exception_log_count++;

        public BulletHellTelemetry Finish(string status, float elapsed)
        {
            EndPhase(elapsed);
            Data.status = status;
            Data.duration_seconds = elapsed;
            Data.player_survival_seconds = elapsed;
            Data.bullets_per_second = elapsed > 0f ? Data.total_bullets_spawned / elapsed : 0f;
            if (frameTimes.Count > 0)
            {
                float averageFrame = frameTimes.Average();
                List<float> ordered = frameTimes.OrderBy(value => value).ToList();
                int percentileIndex = Math.Min(ordered.Count - 1, (int)Math.Floor(ordered.Count * 0.95f));
                Data.average_fps = 1f / averageFrame;
                Data.low_percentile_fps = 1f / ordered[percentileIndex];
                Data.minimum_fps = 1f / ordered[ordered.Count - 1];
            }
            Data.exported_at_utc = DateTime.UtcNow.ToString("O");
            Data.phase_results = phases.ToArray();
            return Data;
        }

        private void EndPhase(float elapsed)
        {
            if (currentPhase == null) return;
            currentPhase.duration_seconds = Math.Max(0f, elapsed - currentPhase.started_at_seconds);
            phases.Add(currentPhase);
            currentPhase = null;
        }
    }
}
