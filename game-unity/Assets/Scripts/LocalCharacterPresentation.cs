using UnityEngine;

namespace GameConfig.Runtime
{
    public sealed class LocalCharacterPresentation : MonoBehaviour
    {
        [SerializeField] private Transform visualRoot;
        private Vector3 baseLocalPosition;
        private Quaternion baseLocalRotation;
        private Vector3 previousWorldPosition;
        private float phase;

        public void Configure(Transform target)
        {
            visualRoot = target;
            CaptureBasePose();
        }

        private void Awake()
        {
            if (visualRoot == null && transform.childCount > 0) visualRoot = transform.GetChild(0);
            CaptureBasePose();
            previousWorldPosition = transform.position;
        }

        private void LateUpdate()
        {
            if (visualRoot == null) return;
            float speed = (transform.position - previousWorldPosition).magnitude / Mathf.Max(Time.deltaTime, 0.0001f);
            previousWorldPosition = transform.position;
            float movement = Mathf.Clamp01(speed / 3f);
            phase += Time.deltaTime * Mathf.Lerp(2f, 8f, movement);
            float bob = Mathf.Sin(phase) * Mathf.Lerp(0.015f, 0.045f, movement);
            float lean = Mathf.Sin(phase * 0.5f) * Mathf.Lerp(0.5f, 2.5f, movement);
            visualRoot.localPosition = baseLocalPosition + Vector3.up * bob;
            visualRoot.localRotation = baseLocalRotation * Quaternion.Euler(0, 0, lean);
        }

        private void CaptureBasePose()
        {
            if (visualRoot == null) return;
            baseLocalPosition = visualRoot.localPosition;
            baseLocalRotation = visualRoot.localRotation;
        }
    }
}
