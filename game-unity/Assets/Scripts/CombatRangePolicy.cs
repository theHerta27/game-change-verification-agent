using UnityEngine;

namespace GameConfig.Runtime
{
    public static class CombatRangePolicy
    {
        public static float PlanarDistance(Vector3 origin, Vector3 target)
        {
            float deltaX = target.x - origin.x;
            float deltaZ = target.z - origin.z;
            return Mathf.Sqrt(deltaX * deltaX + deltaZ * deltaZ);
        }

        public static bool IsInRange(Vector3 origin, Vector3 target, float range)
        {
            return PlanarDistance(origin, target) <= range;
        }
    }
}
