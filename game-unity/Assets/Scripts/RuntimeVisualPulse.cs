using UnityEngine;

namespace GameConfig.Runtime
{
    public sealed class RuntimeVisualPulse : MonoBehaviour
    {
        private float lifetime = 0.24f;
        private float elapsed;
        private Vector3 startScale;

        public void Configure(float duration)
        {
            lifetime = Mathf.Max(0.05f, duration);
            startScale = transform.localScale;
        }

        private void Awake()
        {
            startScale = transform.localScale;
        }

        private void Update()
        {
            elapsed += Time.deltaTime;
            float progress = Mathf.Clamp01(elapsed / lifetime);
            transform.localScale = startScale * Mathf.Lerp(0.65f, 1.8f, progress);
            if (elapsed >= lifetime) Destroy(gameObject);
        }
    }
}
