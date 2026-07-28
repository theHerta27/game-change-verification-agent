using UnityEngine;

namespace GameConfig.Runtime
{
    public static class FixedTrajectoryPlayer
    {
        public static Vector3 PositionAt(float elapsed, BulletHellContract contract)
        {
            float x = Mathf.Sin(elapsed * 0.72f) * contract.scenario.arena_width * 0.34f;
            float zOffset = Mathf.Sin(elapsed * 0.39f) * contract.scenario.arena_height * 0.1f;
            return new Vector3(x, 0.65f, contract.player.start_z + zOffset);
        }
    }
}
