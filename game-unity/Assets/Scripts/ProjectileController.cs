using UnityEngine;

namespace GameConfig.Runtime
{
    public enum ProjectileStepResult
    {
        Active,
        Expired,
        HitPlayer
    }

    public sealed class ProjectileController : MonoBehaviour
    {
        private Vector3 velocity;
        private float remainingLifetime;

        public bool IsActive => gameObject.activeSelf;

        public void Activate(Vector3 position, Vector3 direction, float speed, float lifetime, Material material)
        {
            transform.position = position;
            velocity = direction.normalized * speed;
            remainingLifetime = lifetime;
            GetComponent<Renderer>().sharedMaterial = material;
            gameObject.SetActive(true);
        }

        public ProjectileStepResult Step(
            float deltaTime,
            Vector3 playerPosition,
            float playerHitRadius,
            float arenaWidth,
            float arenaHeight)
        {
            transform.position += velocity * deltaTime;
            remainingLifetime -= deltaTime;
            Vector2 planarOffset = new(transform.position.x - playerPosition.x, transform.position.z - playerPosition.z);
            if (planarOffset.sqrMagnitude <= playerHitRadius * playerHitRadius)
                return ProjectileStepResult.HitPlayer;
            if (remainingLifetime <= 0f ||
                Mathf.Abs(transform.position.x) > arenaWidth * 0.65f ||
                Mathf.Abs(transform.position.z) > arenaHeight * 0.65f)
                return ProjectileStepResult.Expired;
            return ProjectileStepResult.Active;
        }
    }
}
