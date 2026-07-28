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
    public static class BulletHellDemoBuilder
    {
        [MenuItem("GameConfig/Configure Bullet Hell Demo")]
        public static void ConfigureProject()
        {
            ValidateContract();
            ValidatePatterns();
            Directory.CreateDirectory("Assets/Scenes");
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/BulletHellDemo.unity");
            EditorBuildSettings.scenes = new[]
            {
                new EditorBuildSettingsScene("Assets/Scenes/RuntimeDemo.unity", true),
                new EditorBuildSettingsScene("Assets/Scenes/BulletHellDemo.unity", true),
            };
            PlayerSettings.productName = "Agentic Game R&D Lab Runtime Demos";
            PlayerSettings.companyName = "Agentic Game R&D Lab";
            AssetDatabase.SaveAssets();
            Debug.Log("Bullet Hell demo configured.");
        }

        public static void BuildWindows()
        {
            ConfigureProject();
            Directory.CreateDirectory("Builds/BulletHellWindows");
            BuildReport report = BuildPipeline.BuildPlayer(
                new[] { "Assets/Scenes/BulletHellDemo.unity" },
                "Builds/BulletHellWindows/BulletHellDemo.exe",
                BuildTarget.StandaloneWindows64,
                BuildOptions.Development
            );
            if (report.summary.result != BuildResult.Succeeded)
                throw new BuildFailedException($"Bullet Hell Windows build failed: {report.summary.result}");
            File.WriteAllText("Builds/BulletHellWindows/runtime_version.txt", "bullet-hell-runtime-v1");
        }

        private static void ValidateContract()
        {
            BulletHellContract contract = BulletHellConfigLoader.Load();
            if (contract.phases.Length < 2) throw new BuildFailedException("Bullet Hell baseline phases are missing.");
            Debug.Log("Bullet Hell contract smoke passed.");
        }

        private static void ValidatePatterns()
        {
            foreach (string type in new[] { "ring", "aimed_fan", "spiral", "petal" })
            {
                BulletHellPattern pattern = new()
                {
                    type = type,
                    bullets_per_wave = 8,
                    wave_interval_ms = 800,
                    bullet_speed = 3f,
                    bullet_lifetime_seconds = 4f,
                    rotation_per_wave_deg = 10f,
                    spread_angle_deg = type == "aimed_fan" ? 90f : 360f,
                    layer_count = type == "petal" ? 2 : 1,
                    bidirectional = false,
                };
                BulletSpawnSpec[] specs = BulletPatternCalculator.Calculate(pattern, Vector3.zero, Vector3.forward, 1);
                int expected = pattern.bullets_per_wave * pattern.layer_count;
                if (specs.Length != expected)
                    throw new BuildFailedException($"{type} pattern expected {expected} bullets, got {specs.Length}.");
                foreach (BulletSpawnSpec spec in specs)
                    if (Mathf.Abs(spec.Direction.magnitude - 1f) > 0.001f)
                        throw new BuildFailedException($"{type} pattern produced a non-normalized direction.");
            }
            Debug.Log("Bullet pattern math smoke passed for ring, aimed_fan, spiral, and petal.");
        }
    }
}
