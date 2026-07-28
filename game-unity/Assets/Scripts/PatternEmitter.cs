using UnityEngine;

namespace GameConfig.Runtime
{
    public sealed class PatternEmitter
    {
        private readonly ProjectilePool pool;
        private BulletHellPattern pattern;
        private float untilNextWave;
        private int waveIndex;

        public PatternEmitter(ProjectilePool pool, BulletHellPattern initialPattern)
        {
            this.pool = pool;
            SetPattern(initialPattern);
        }

        public void SetPattern(BulletHellPattern value)
        {
            pattern = value;
            untilNextWave = 0f;
            waveIndex = 0;
        }

        public int Tick(float deltaTime, Vector3 origin, Vector3 target)
        {
            untilNextWave -= deltaTime;
            if (untilNextWave > 0f) return 0;
            BulletSpawnSpec[] specs = BulletPatternCalculator.Calculate(pattern, origin, target, waveIndex++);
            foreach (BulletSpawnSpec spec in specs)
            {
                pool.Spawn(
                    origin,
                    spec.Direction,
                    pattern.bullet_speed * spec.SpeedMultiplier,
                    pattern.bullet_lifetime_seconds
                );
            }
            untilNextWave = pattern.wave_interval_ms / 1000f;
            return specs.Length;
        }
    }
}
