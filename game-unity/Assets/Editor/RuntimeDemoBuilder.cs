using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using GameConfig.Runtime;

namespace GameConfig.Editor
{
    public static class RuntimeDemoBuilder
    {
        private const string PlaceholderDirectory = "Assets/Resources/Characters";
        private const string PlaceholderAssetPath = PlaceholderDirectory + "/Placeholder.prefab";

        [MenuItem("GameConfig/Configure Runtime Demo")]
        public static void ConfigureProject()
        {
            ValidateCombatRangePolicy();
            ValidateRuntimeRunSettings();
            EnsurePlaceholderPrefab();
            ValidateCharacterViewResolver();
            Directory.CreateDirectory("Assets/Scenes");
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/RuntimeDemo.unity");
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene("Assets/Scenes/RuntimeDemo.unity", true) };
            PlayerSettings.productName = "GameConfig Runtime Demo";
            PlayerSettings.companyName = "GameConfig Agent";
            AssetDatabase.SaveAssets();
            Debug.Log("GameConfig runtime demo configured.");
        }

        private static void ValidateCombatRangePolicy()
        {
            Vector3 origin = new(0, 1, 0);
            if (!CombatRangePolicy.IsInRange(origin, new Vector3(0, 20, 0), 3.2f))
                throw new BuildFailedException("Close-range combat smoke failed at distance 0.");
            if (!CombatRangePolicy.IsInRange(origin, new Vector3(1, -4, 0), 3.2f))
                throw new BuildFailedException("Close-range combat smoke failed at distance 1.0.");
            if (!CombatRangePolicy.IsInRange(origin, new Vector3(3.2f, 100, 0), 3.2f))
                throw new BuildFailedException("Combat range boundary smoke failed at distance 3.2.");
            if (CombatRangePolicy.IsInRange(origin, new Vector3(3.21f, 1, 0), 3.2f))
                throw new BuildFailedException("Combat range boundary smoke failed at distance 3.21.");
            Debug.Log("Combat range smoke passed: 0, 1.0, and 3.2 hit; 3.21 misses.");
        }

        private static void ValidateRuntimeRunSettings()
        {
            RuntimeRunSettings defaults = RuntimeRunSettings.FromArgs(new string[0]);
            if (defaults.AutoRun || defaults.RandomSeed != RuntimeRunSettings.DefaultSeed || defaults.RunMode != "manual")
                throw new BuildFailedException("Runtime run settings default smoke failed.");

            RuntimeRunSettings automatic = RuntimeRunSettings.FromArgs(new[] { "--auto-run", "--seed", "42" });
            if (!automatic.AutoRun || automatic.RandomSeed != 42 || automatic.RunMode != "auto")
                throw new BuildFailedException("Runtime run settings argument smoke failed.");
            Debug.Log("Runtime run settings smoke passed for manual defaults and seeded auto mode.");
        }

        private static void EnsurePlaceholderPrefab()
        {
            if (AssetDatabase.LoadAssetAtPath<GameObject>(PlaceholderAssetPath) != null) return;

            Directory.CreateDirectory(PlaceholderDirectory);
            AssetDatabase.Refresh();
            GameObject placeholder = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            placeholder.name = "Placeholder";
            placeholder.transform.localScale = new Vector3(0.85f, 1f, 0.85f);
            PrefabUtility.SaveAsPrefabAsset(placeholder, PlaceholderAssetPath);
            Object.DestroyImmediate(placeholder);
            AssetDatabase.SaveAssets();
            Debug.Log("Created tracked placeholder character prefab.");
        }

        private static void ValidateCharacterViewResolver()
        {
            GameObject placeholder = AssetDatabase.LoadAssetAtPath<GameObject>(PlaceholderAssetPath);
            CharacterViewResolution fallback = CharacterViewResolver.ResolveFromCandidates(
                null,
                placeholder,
                Vector3.zero,
                null
            );
            if (fallback.UsesLocalAsset || fallback.View == null)
                throw new BuildFailedException("Character fallback smoke failed without local asset.");
            Object.DestroyImmediate(fallback.View);

            GameObject localCandidate = GameObject.CreatePrimitive(PrimitiveType.Cube);
            CharacterViewResolution local = CharacterViewResolver.ResolveFromCandidates(
                localCandidate,
                placeholder,
                Vector3.zero,
                null
            );
            if (!local.UsesLocalAsset || local.View == null)
                throw new BuildFailedException("Character local-asset replacement smoke failed.");
            Object.DestroyImmediate(local.View);
            Object.DestroyImmediate(localCandidate);

            GameObject actualLocalPrefab = Resources.Load<GameObject>(CharacterViewResolver.LocalCharacterPath);
            if (actualLocalPrefab != null)
            {
                CharacterViewResolution actualLocal = CharacterViewResolver.ResolveFromCandidates(
                    actualLocalPrefab,
                    placeholder,
                    Vector3.zero,
                    null
                );
                bool hasRenderer = actualLocal.View.GetComponentsInChildren<Renderer>(true).Length > 0;
                bool hasPresentation = actualLocal.View.GetComponent<LocalCharacterPresentation>() != null;
                Object.DestroyImmediate(actualLocal.View);
                if (!actualLocal.UsesLocalAsset || !hasRenderer || !hasPresentation)
                    throw new BuildFailedException("Actual local Reimu prefab smoke failed.");
                Debug.Log("Actual local Reimu prefab smoke passed with renderer and presentation component.");
            }
            Debug.Log("Character view resolver smoke passed for fallback and local-asset branches.");
        }

        public static void BuildWindows()
        {
            ConfigureProject();
            Directory.CreateDirectory("Builds/Windows");
            BuildReport report = BuildPipeline.BuildPlayer(
                EditorBuildSettings.scenes,
                "Builds/Windows/GameConfigRuntimeDemo.exe",
                BuildTarget.StandaloneWindows64,
                BuildOptions.Development
            );
            if (report.summary.result != BuildResult.Succeeded)
                throw new BuildFailedException($"Windows build failed: {report.summary.result}");
            File.WriteAllText("Builds/Windows/guided_runtime_version.txt", "guided-runtime-v1");
            Debug.Log("Guided runtime marker written: guided-runtime-v1");
        }
    }
}
