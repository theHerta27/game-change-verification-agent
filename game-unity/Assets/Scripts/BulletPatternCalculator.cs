using System.Collections.Generic;
using UnityEngine;

namespace GameConfig.Runtime
{
    public readonly struct BulletSpawnSpec
    {
        public readonly Vector3 Direction;
        public readonly float SpeedMultiplier;

        public BulletSpawnSpec(Vector3 direction, float speedMultiplier)
        {
            Direction = direction.normalized;
            SpeedMultiplier = speedMultiplier;
        }
    }

    public static class BulletPatternCalculator
    {
        public static BulletSpawnSpec[] Calculate(
            BulletHellPattern pattern,
            Vector3 origin,
            Vector3 target,
            int waveIndex)
        {
            List<BulletSpawnSpec> result = new();
            float targetAngle = Mathf.Atan2(target.z - origin.z, target.x - origin.x) * Mathf.Rad2Deg;
            int directions = pattern.bidirectional ? 2 : 1;
            for (int directionIndex = 0; directionIndex < directions; directionIndex++)
            {
                float directionSign = directionIndex == 0 ? 1f : -1f;
                for (int layer = 0; layer < pattern.layer_count; layer++)
                {
                    float layerOffset = layer * (180f / Mathf.Max(1, pattern.bullets_per_wave * pattern.layer_count));
                    float rotation = waveIndex * pattern.rotation_per_wave_deg * directionSign;
                    for (int index = 0; index < pattern.bullets_per_wave; index++)
                    {
                        float angle = PatternAngle(pattern, index, targetAngle, rotation, layerOffset);
                        float radians = angle * Mathf.Deg2Rad;
                        float speedMultiplier = pattern.type == "petal" ? 1f + layer * 0.16f : 1f;
                        result.Add(new BulletSpawnSpec(new Vector3(Mathf.Cos(radians), 0f, Mathf.Sin(radians)), speedMultiplier));
                    }
                }
            }
            return result.ToArray();
        }

        private static float PatternAngle(BulletHellPattern pattern, int index, float targetAngle, float rotation, float layerOffset)
        {
            if (pattern.type == "aimed_fan")
            {
                float step = pattern.bullets_per_wave == 1 ? 0f : pattern.spread_angle_deg / (pattern.bullets_per_wave - 1);
                return targetAngle - pattern.spread_angle_deg * 0.5f + index * step + layerOffset;
            }
            float radialStep = pattern.spread_angle_deg / pattern.bullets_per_wave;
            if (pattern.type == "petal")
            {
                float wave = Mathf.Sin(index * Mathf.PI * 2f / pattern.bullets_per_wave) * 12f;
                return rotation + layerOffset + index * radialStep + wave;
            }
            return rotation + layerOffset + index * radialStep;
        }
    }
}
