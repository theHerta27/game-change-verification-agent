using UnityEngine;

namespace GameConfig.Runtime
{
    public sealed class CharacterViewResolution
    {
        public GameObject View { get; }
        public bool UsesLocalAsset { get; }

        public CharacterViewResolution(GameObject view, bool usesLocalAsset)
        {
            View = view;
            UsesLocalAsset = usesLocalAsset;
        }
    }

    public static class CharacterViewResolver
    {
        public const string LocalCharacterPath = "LocalThirdParty/Reimu/Reimu";
        public const string PlaceholderPath = "Characters/Placeholder";

        public static CharacterViewResolution Resolve(Vector3 position, Material placeholderMaterial)
        {
            GameObject localPrefab = Resources.Load<GameObject>(LocalCharacterPath);
            GameObject placeholderPrefab = Resources.Load<GameObject>(PlaceholderPath);
            return ResolveFromCandidates(localPrefab, placeholderPrefab, position, placeholderMaterial);
        }

        public static CharacterViewResolution ResolveFromCandidates(
            GameObject localPrefab,
            GameObject placeholderPrefab,
            Vector3 position,
            Material placeholderMaterial)
        {
            bool usesLocalAsset = localPrefab != null;
            GameObject source = usesLocalAsset ? localPrefab : placeholderPrefab;
            GameObject view = source != null
                ? Object.Instantiate(source, position, Quaternion.identity)
                : GameObject.CreatePrimitive(PrimitiveType.Capsule);

            view.name = usesLocalAsset ? "Player - Local Reimu" : "Player - Placeholder";
            view.transform.position = position;
            if (!usesLocalAsset && placeholderMaterial != null)
            {
                foreach (Renderer renderer in view.GetComponentsInChildren<Renderer>(true))
                    renderer.sharedMaterial = placeholderMaterial;
            }

            return new CharacterViewResolution(view, usesLocalAsset);
        }
    }
}

