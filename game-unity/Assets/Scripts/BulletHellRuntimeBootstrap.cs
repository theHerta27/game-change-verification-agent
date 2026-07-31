using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace GameConfig.Runtime
{
    public sealed class BulletHellRuntimeBootstrap : MonoBehaviour
    {
        private BulletHellContract contract;
        private RuntimeRunSettings settings;
        private BulletHellTelemetryRecorder telemetry;
        private BossPhaseController bossState;
        private PatternEmitter emitter;
        private ProjectilePool projectilePool;
        private GameObject player;
        private GameObject boss;
        private Camera gameplayCamera;
        private float startedAt;
        private float simulationElapsed;
        private float nextPlayerShot;
        private float invulnerableUntil;
        private int playerHealth;
        private bool completed;
        private string message = "正在加载弹幕配置";

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            bool requested = Environment.GetCommandLineArgs().Contains("--bullet-hell") ||
                             SceneManager.GetActiveScene().name == "BulletHellDemo";
            if (requested && FindFirstObjectByType<BulletHellRuntimeBootstrap>() == null)
                new GameObject("Bullet Hell Runtime").AddComponent<BulletHellRuntimeBootstrap>();
        }

        private void Start()
        {
            try
            {
                settings = RuntimeRunSettings.FromArgs(Environment.GetCommandLineArgs());
                UnityEngine.Random.InitState(settings.RandomSeed);
                Application.runInBackground = true;
                QualitySettings.vSyncCount = 0;
                Application.targetFrameRate = 60;
                Time.timeScale = settings.AutoRun ? 4f : 1f;
                Time.fixedDeltaTime = 1f / 60f;
                contract = BulletHellConfigLoader.Load();
                CreateArena();
                playerHealth = contract.player.max_health;
                bossState = new BossPhaseController(contract.phases, contract.boss.max_health);
                telemetry = new BulletHellTelemetryRecorder(contract, settings);
                telemetry.BeginPhase(bossState.CurrentPhase, 0f);
                emitter = new PatternEmitter(projectilePool, bossState.CurrentPhase.pattern);
                Application.logMessageReceived += HandleLog;
                startedAt = Time.time;
                message = settings.AutoRun ? "固定轨迹自动验证中" : "WASD 移动，Shift 低速聚焦，玩家自动射击";
                if (Environment.GetCommandLineArgs().Contains("--screenshot-output-dir"))
                    StartCoroutine(CaptureEvidenceSequence());
                else if (Environment.GetCommandLineArgs().Contains("--screenshot-output"))
                    StartCoroutine(CaptureEvidence());
            }
            catch (Exception exception)
            {
                message = "弹幕配置加载失败：" + exception.Message;
                Debug.LogException(exception);
            }
        }

        private void Update()
        {
            if (contract == null || completed) return;
            if (settings.AutoRun)
            {
                telemetry.RecordFrame(simulationElapsed, Time.unscaledDeltaTime, projectilePool.ActiveCount);
                return;
            }
            float elapsed = Time.time - startedAt;
            TickGameplay(elapsed, Time.deltaTime);
            telemetry.RecordFrame(elapsed, Time.unscaledDeltaTime, projectilePool.ActiveCount);
        }

        private void FixedUpdate()
        {
            if (contract == null || completed || !settings.AutoRun) return;
            simulationElapsed += Time.fixedDeltaTime;
            TickGameplay(simulationElapsed, Time.fixedDeltaTime);
        }

        private void TickGameplay(float elapsed, float deltaTime)
        {
            UpdatePlayer(elapsed, deltaTime);
            UpdatePlayerFire(elapsed);
            int spawned = emitter.Tick(deltaTime, boss.transform.position, player.transform.position);
            telemetry.RecordBullets(spawned);
            int hits = projectilePool.StepAll(
                deltaTime,
                player.transform.position,
                contract.player.hit_radius,
                contract.scenario.arena_width,
                contract.scenario.arena_height
            );
            if (hits > 0 && elapsed >= invulnerableUntil)
            {
                invulnerableUntil = elapsed + 0.35f;
                playerHealth--;
                telemetry.RecordHit();
                if (playerHealth <= 0)
                {
                    Finish("failed", elapsed);
                    return;
                }
            }
            if (elapsed >= contract.scenario.duration_seconds || bossState.Health <= 0)
                Finish("completed", Mathf.Min(elapsed, contract.scenario.duration_seconds));
        }

        private void CreateArena()
        {
            Shader shader = Resources.Load<Shader>("SolidColor");
            if (shader == null) throw new InvalidDataException("GameConfig/SolidColor shader is required.");
            gameplayCamera = Camera.main;
            if (gameplayCamera == null) gameplayCamera = new GameObject("Main Camera").AddComponent<Camera>();
            gameplayCamera.tag = "MainCamera";
            gameplayCamera.orthographic = true;
            gameplayCamera.orthographicSize = contract.scenario.arena_height * 0.58f;
            gameplayCamera.clearFlags = CameraClearFlags.SolidColor;
            gameplayCamera.backgroundColor = new Color(0.025f, 0.035f, 0.065f);
            gameplayCamera.transform.position = new Vector3(0f, 22f, 0f);
            gameplayCamera.transform.rotation = Quaternion.Euler(90f, 0f, 0f);

            GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "Boundary Arena";
            floor.transform.position = new Vector3(0f, -0.2f, 0f);
            floor.transform.localScale = new Vector3(contract.scenario.arena_width, 0.2f, contract.scenario.arena_height);
            floor.GetComponent<Renderer>().sharedMaterial = Material(shader, new Color(0.055f, 0.085f, 0.13f));

            bool forcePlaceholder = Environment.GetCommandLineArgs().Contains("--force-placeholder");
            CharacterViewResolution view = CharacterViewResolver.Resolve(
                new Vector3(contract.player.start_x, 0.65f, contract.player.start_z),
                Material(shader, new Color(0.18f, 0.82f, 0.95f)),
                forcePlaceholder
            );
            player = view.View;
            player.name = view.UsesLocalAsset ? "Local Player View" : "Placeholder Player";
            player.transform.localScale *= 0.62f;

            boss = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            boss.name = contract.boss.display_name;
            boss.transform.position = new Vector3(contract.boss.position_x, 0.8f, contract.boss.position_z);
            boss.transform.localScale = new Vector3(1.4f, 0.8f, 1.4f);
            boss.GetComponent<Renderer>().sharedMaterial = Material(shader, new Color(0.92f, 0.2f, 0.34f));

            GameObject bulletRoot = new("Projectile Pool");
            projectilePool = new ProjectilePool(
                bulletRoot.transform,
                Material(shader, new Color(1f, 0.72f, 0.18f)),
                384
            );
        }

        private void UpdatePlayer(float elapsed, float deltaTime)
        {
            if (settings.AutoRun)
            {
                player.transform.position = FixedTrajectoryPlayer.PositionAt(elapsed, contract);
                return;
            }
            float horizontal = (Input.GetKey(KeyCode.D) ? 1f : 0f) - (Input.GetKey(KeyCode.A) ? 1f : 0f);
            float vertical = (Input.GetKey(KeyCode.W) ? 1f : 0f) - (Input.GetKey(KeyCode.S) ? 1f : 0f);
            Vector3 direction = new(horizontal, 0f, vertical);
            float focus = Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift)
                ? contract.player.focus_speed_multiplier
                : 1f;
            if (direction.sqrMagnitude > 0.01f)
                player.transform.position += direction.normalized * contract.player.move_speed * focus * deltaTime;
            float halfWidth = contract.scenario.arena_width * 0.5f - 0.4f;
            float halfHeight = contract.scenario.arena_height * 0.5f - 0.4f;
            Vector3 position = player.transform.position;
            position.x = Mathf.Clamp(position.x, -halfWidth, halfWidth);
            position.z = Mathf.Clamp(position.z, -halfHeight, halfHeight);
            position.y = 0.65f;
            player.transform.position = position;
        }

        private void UpdatePlayerFire(float elapsed)
        {
            if (elapsed < nextPlayerShot) return;
            nextPlayerShot = elapsed + contract.player.auto_fire_interval_seconds;
            bool changed = bossState.ApplyDamage(contract.player.auto_fire_damage);
            if (changed)
            {
                emitter.SetPattern(bossState.CurrentPhase.pattern);
                telemetry.BeginPhase(bossState.CurrentPhase, elapsed);
                message = $"进入 {bossState.CurrentPhase.display_name}";
            }
        }

        private void HandleLog(string condition, string stackTrace, LogType type)
        {
            if (type == LogType.Exception || type == LogType.Error || type == LogType.Assert)
                telemetry?.RecordException();
        }

        private void Finish(string status, float elapsed)
        {
            if (completed) return;
            completed = true;
            projectilePool.Clear();
            BulletHellTelemetry result = telemetry.Finish(status, elapsed);
            string path = OutputPath(Environment.GetCommandLineArgs());
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, JsonUtility.ToJson(result, true));
            message = status == "completed" ? "验证完成" : "玩家未能存活到测试结束";
            if (settings.AutoRun) StartCoroutine(QuitAfterCleanup(status == "completed" ? 0 : 1));
        }

        private IEnumerator CaptureEvidence()
        {
            yield return new WaitForSeconds(contract.scenario.duration_seconds * 0.55f);
            string[] args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, "--screenshot-output");
            if (index >= 0 && index + 1 < args.Length)
            {
                string path = Path.GetFullPath(args[index + 1]);
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                ScreenCapture.CaptureScreenshot(path);
            }
        }

        private IEnumerator CaptureEvidenceSequence()
        {
            string[] args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, "--screenshot-output-dir");
            if (index < 0 || index + 1 >= args.Length) yield break;
            string outputDirectory = Path.GetFullPath(args[index + 1]);
            Directory.CreateDirectory(outputDirectory);
            float[] targets = { 10f, 20f, 30f };
            List<VisualCaptureRecord> records = new();

            foreach (float target in targets)
            {
                while (!completed && simulationElapsed < target)
                    yield return null;
                if (completed) break;
                yield return new WaitForEndOfFrame();
                string fileName = $"capture_{target:00}s.png";
                ScreenCapture.CaptureScreenshot(Path.Combine(outputDirectory, fileName));
                records.Add(new VisualCaptureRecord
                {
                    time_seconds = target,
                    phase_id = bossState.CurrentPhase.phase_id,
                    phase_name = bossState.CurrentPhase.display_name,
                    pattern_type = bossState.CurrentPhase.pattern.type,
                    file_name = fileName,
                });
            }

            VisualCaptureManifest manifest = new()
            {
                random_seed = settings.RandomSeed,
                run_mode = settings.RunMode,
                fixed_trajectory = settings.AutoRun,
                duration_seconds = contract.scenario.duration_seconds,
                captures = records.ToArray(),
            };
            File.WriteAllText(
                Path.Combine(outputDirectory, "capture_manifest.json"),
                JsonUtility.ToJson(manifest, true)
            );
        }

        private static IEnumerator QuitAfterCleanup(int exitCode)
        {
            yield return new WaitForSecondsRealtime(0.2f);
            Application.Quit(exitCode);
        }

        private static string OutputPath(string[] args)
        {
            int index = Array.IndexOf(args, "--telemetry-output");
            return index >= 0 && index + 1 < args.Length
                ? Path.GetFullPath(args[index + 1])
                : Path.Combine(Application.persistentDataPath, "bullet_hell_telemetry.json");
        }

        private static Material Material(Shader shader, Color color)
        {
            Material material = new(shader);
            material.SetColor("_Color", color);
            return material;
        }

        private void OnGUI()
        {
            GUI.Box(new Rect(18, 18, 430, 154), "Game Change Verification Agent | 弹幕运行验证");
            GUI.Label(new Rect(36, 48, 390, 22), message);
            if (contract == null || bossState == null) return;
            GUI.Label(new Rect(36, 74, 390, 22), $"阶段：{bossState.CurrentPhase.display_name} | Pattern: {bossState.CurrentPhase.pattern.type}");
            GUI.Label(new Rect(36, 100, 390, 22), $"玩家生命：{playerHealth}/{contract.player.max_health} | Boss：{bossState.HealthRatio * 100f:0}%");
            GUI.Label(new Rect(36, 126, 390, 22), $"存活子弹：{projectilePool.ActiveCount}/{contract.constraints.max_alive_bullets}");
        }

        [Serializable]
        private sealed class VisualCaptureRecord
        {
            public float time_seconds;
            public string phase_id;
            public string phase_name;
            public string pattern_type;
            public string file_name;
        }

        [Serializable]
        private sealed class VisualCaptureManifest
        {
            public int random_seed;
            public string run_mode;
            public bool fixed_trajectory;
            public float duration_seconds;
            public VisualCaptureRecord[] captures;
        }
    }
}
