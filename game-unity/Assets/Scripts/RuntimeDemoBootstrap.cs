using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEngine;

namespace GameConfig.Runtime
{
    public sealed class RuntimeDemoBootstrap : MonoBehaviour
    {
        private sealed class EnemyState
        {
            public EnemyConfig Config;
            public GameObject View;
            public float Health;
            public float NextAttackTime;
        }

        private RuntimeContract contract;
        private RuntimeTelemetry telemetry;
        private readonly List<EnemyState> enemies = new();
        private readonly List<WaveRuntimeTelemetry> waveResults = new();
        private GameObject player;
        private Camera gameplayCamera;
        private Material playerMaterial;
        private Material enemyMaterial;
        private Material eliteMaterial;
        private int playerHealth;
        private int playerAttack;
        private int gold;
        private int currentWave;
        private float startedAt;
        private float nextBasicAttack;
        private float nextSkill;
        private string message = "Loading runtime contract...";
        private bool completed;
        private bool autoRun;
        private bool awaitingStart;
        private string combatFeedback = "";
        private float feedbackUntil;
        private float waveStartedAt;
        private int waveStartBasicAttacks;
        private int waveStartSkillUses;
        private int waveStartDamageDealt;
        private int waveStartDamageTaken;
        private int waveStartDefeated;
        private RuntimeRunSettings runSettings;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Bootstrap()
        {
            if (FindFirstObjectByType<RuntimeDemoBootstrap>() == null)
            {
                new GameObject("GameConfig Runtime Demo").AddComponent<RuntimeDemoBootstrap>();
            }
        }

        private void Start()
        {
            try
            {
                runSettings = RuntimeRunSettings.FromArgs(Environment.GetCommandLineArgs());
                autoRun = runSettings.AutoRun;
                UnityEngine.Random.InitState(runSettings.RandomSeed);
                Application.runInBackground = true;
                QualitySettings.vSyncCount = 0;
                Application.targetFrameRate = 60;
                Time.fixedDeltaTime = 1f / 60f;
                contract = GameConfigLoader.Load();
                awaitingStart = !autoRun;
                CreateArena();
                playerHealth = contract.runtime_scenario.player.max_health;
                playerAttack = contract.configs.weapon_config[0].base_attack;
                telemetry = new RuntimeTelemetry
                {
                    scenario_id = contract.runtime_scenario.scenario_id,
                    contract_version = contract.contract_version,
                    status = "running",
                    run_mode = runSettings.RunMode,
                    random_seed = runSettings.RandomSeed,
                    final_attack = playerAttack,
                    wave_results = Array.Empty<WaveRuntimeTelemetry>(),
                };
                startedAt = Time.time;
                SpawnNextWave();
                message = autoRun ? "Auto validation is running." : "按 W/A/S/D 开始试玩";
                if (Environment.GetCommandLineArgs().Contains("--screenshot-output")) StartCoroutine(CapturePreview());
            }
            catch (Exception exception)
            {
                message = "Config load failed: " + exception.Message;
                Debug.LogException(exception);
            }
        }

        private void Update()
        {
            if (contract == null || completed) return;
            if (awaitingStart)
            {
                if (HasGameplayInput())
                {
                    awaitingStart = false;
                    startedAt = Time.time;
                    message = "战斗开始：靠近敌人后使用普通攻击或技能";
                }
                else
                {
                    return;
                }
            }
            if (autoRun) return;
            UpdateManualPlayer();
            UpdateEnemies();
            if (enemies.Count == 0) SpawnNextWave();
        }

        private void FixedUpdate()
        {
            if (!autoRun || contract == null || completed) return;
            telemetry.simulation_ticks++;
            UpdateAutoPlayer();
            UpdateEnemies();
            if (enemies.Count == 0) SpawnNextWave();
        }

        private void LateUpdate()
        {
            if (player == null || gameplayCamera == null) return;
            Vector3 focus = player.transform.position + new Vector3(0, 0, 2.5f);
            Vector3 desired = player.transform.position + new Vector3(0, 13, -10);
            gameplayCamera.transform.position = Vector3.Lerp(gameplayCamera.transform.position, desired, 8f * Time.deltaTime);
            gameplayCamera.transform.LookAt(focus);
        }

        private void CreateArena()
        {
            gameplayCamera = Camera.main;
            if (gameplayCamera == null) gameplayCamera = new GameObject("Main Camera").AddComponent<Camera>();
            gameplayCamera.tag = "MainCamera";
            gameplayCamera.clearFlags = CameraClearFlags.SolidColor;
            gameplayCamera.backgroundColor = new Color(0.035f, 0.055f, 0.07f);
            gameplayCamera.fieldOfView = 52f;
            gameplayCamera.transform.position = new Vector3(0, 13, -10);

            Light light = new GameObject("Directional Light").AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.4f;
            light.transform.rotation = Quaternion.Euler(45, -30, 0);

            Shader shader = Resources.Load<Shader>("SolidColor");
            if (shader == null) throw new InvalidDataException("GameConfig/SolidColor shader was not included in the build.");
            Material floorMaterial = CreateMaterial(shader, new Color(0.09f, 0.13f, 0.15f));
            playerMaterial = CreateMaterial(shader, new Color(0.1f, 0.75f, 0.95f));
            enemyMaterial = CreateMaterial(shader, new Color(0.96f, 0.63f, 0.18f));
            eliteMaterial = CreateMaterial(shader, new Color(0.92f, 0.2f, 0.18f));

            GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            floor.name = "Trial Arena";
            floor.transform.position = new Vector3(0, -0.15f, 0);
            floor.transform.localScale = new Vector3(12, 0.15f, 12);
            floor.GetComponent<Renderer>().sharedMaterial = floorMaterial;

            CreateArenaMarkers(shader);

            CharacterViewResolution playerView = CharacterViewResolver.Resolve(new Vector3(0, 1, 0), playerMaterial);
            player = playerView.View;
            if (!playerView.UsesLocalAsset) player.transform.localScale = new Vector3(0.85f, 1f, 0.85f);

            GameObject direction = GameObject.CreatePrimitive(PrimitiveType.Cube);
            direction.name = "Player Direction";
            direction.transform.SetParent(player.transform, false);
            direction.transform.localPosition = new Vector3(0, 0.15f, 0.85f);
            direction.transform.localScale = new Vector3(0.18f, 0.18f, 0.7f);
            direction.GetComponent<Renderer>().sharedMaterial = CreateMaterial(shader, new Color(0.75f, 0.95f, 1f));
            Destroy(direction.GetComponent<Collider>());
        }

        private void UpdateManualPlayer()
        {
            float horizontal = (Input.GetKey(KeyCode.D) ? 1f : 0f) - (Input.GetKey(KeyCode.A) ? 1f : 0f);
            float vertical = (Input.GetKey(KeyCode.W) ? 1f : 0f) - (Input.GetKey(KeyCode.S) ? 1f : 0f);
            Vector3 direction = new(horizontal, 0, vertical);
            if (direction.sqrMagnitude > 0.01f)
            {
                player.transform.position += direction.normalized * contract.runtime_scenario.player.move_speed * Time.deltaTime;
                player.transform.rotation = Quaternion.Slerp(player.transform.rotation, Quaternion.LookRotation(direction), 14f * Time.deltaTime);
            }
            ClampPlayerToArena();
            if (Input.GetKey(KeyCode.Space)) BasicAttack(Input.GetKeyDown(KeyCode.Space));
            if (Input.GetKeyDown(KeyCode.Q)) UseSkill();
            if (Input.GetKeyDown(KeyCode.U)) TryUpgrade();
        }

        private void UpdateAutoPlayer()
        {
            EnemyState target = enemies.OrderBy(PlanarDistanceTo).FirstOrDefault();
            if (target == null) return;
            Vector3 offset = target.View.transform.position - player.transform.position;
            offset.y = 0;
            if (PlanarDistanceTo(target) > contract.runtime_scenario.player.attack_range * 0.75f)
            {
                player.transform.position += offset.normalized * contract.runtime_scenario.player.move_speed * Time.deltaTime;
                ClampPlayerToArena();
            }
            else if (Time.time >= nextBasicAttack)
            {
                BasicAttack(false);
                if (Time.time >= nextSkill && enemies.Count > 1) UseSkill();
            }
        }

        private void BasicAttack(bool showCooldownFeedback)
        {
            if (Time.time < nextBasicAttack)
            {
                if (showCooldownFeedback) ShowFeedback($"普通攻击冷却中：{nextBasicAttack - Time.time:0.0}s");
                return;
            }
            nextBasicAttack = Time.time + contract.runtime_scenario.player.attack_cooldown;
            telemetry.basic_attacks++;
            EnemyState target = enemies.Where(InBasicRange).OrderBy(PlanarDistanceTo).FirstOrDefault();
            if (target != null)
            {
                DamageEnemy(target, playerAttack);
                ShowFeedback($"普通攻击 -{playerAttack}");
            }
            else ShowFeedback("没有敌人在攻击范围内");
        }

        private void UseSkill()
        {
            if (Time.time < nextSkill) return;
            nextSkill = Time.time + contract.runtime_scenario.skill.cooldown;
            telemetry.skill_uses++;
            EnemyState[] targets = enemies.Where(InSkillRange).ToArray();
            foreach (EnemyState enemy in targets) DamageEnemy(enemy, contract.runtime_scenario.skill.damage);
            ShowFeedback(targets.Length > 0 ? $"技能命中 {targets.Length} 个敌人" : "技能范围内没有敌人");
        }

        private float PlanarDistanceTo(EnemyState enemy) => CombatRangePolicy.PlanarDistance(player.transform.position, enemy.View.transform.position);
        private bool InBasicRange(EnemyState enemy) => CombatRangePolicy.IsInRange(player.transform.position, enemy.View.transform.position, contract.runtime_scenario.player.attack_range);
        private bool InSkillRange(EnemyState enemy) => CombatRangePolicy.IsInRange(player.transform.position, enemy.View.transform.position, contract.runtime_scenario.skill.range);

        private void DamageEnemy(EnemyState enemy, int damage)
        {
            enemy.Health -= damage;
            telemetry.damage_dealt += damage;
            if (enemy.Health > 0) return;
            enemies.Remove(enemy);
            Destroy(enemy.View);
            telemetry.enemies_defeated++;
        }

        private void UpdateEnemies()
        {
            foreach (EnemyState enemy in enemies.ToArray())
            {
                Vector3 offset = player.transform.position - enemy.View.transform.position;
                offset.y = 0;
                if (offset.magnitude > 1.6f)
                {
                    enemy.View.transform.position += offset.normalized * enemy.Config.move_speed * Time.deltaTime;
                }
                else if (Time.time >= enemy.NextAttackTime)
                {
                    enemy.NextAttackTime = Time.time + 1.0f;
                    playerHealth -= enemy.Config.attack;
                    telemetry.damage_taken += enemy.Config.attack;
                    if (playerHealth <= 0) Finish("failed");
                }
            }
        }

        private void SpawnNextWave()
        {
            if (currentWave > 0) CompleteCurrentWave();
            if (currentWave >= contract.runtime_scenario.waves.Length)
            {
                RewardConfig reward = contract.configs.reward_config.FirstOrDefault();
                gold += GoldRewardAmount(reward);
                telemetry.gold_earned = gold;
                TryUpgrade();
                Finish("completed");
                return;
            }

            WaveConfig wave = contract.runtime_scenario.waves[currentWave++];
            EnemyConfig config = contract.runtime_scenario.enemies.First(enemy => enemy.enemy_id == wave.enemy_id);
            BeginWaveTelemetry();
            for (int index = 0; index < wave.count; index++)
            {
                GameObject view = GameObject.CreatePrimitive(currentWave == contract.runtime_scenario.waves.Length ? PrimitiveType.Cylinder : PrimitiveType.Cube);
                view.name = config.display_name;
                float spawnJitter = UnityEngine.Random.Range(-0.25f, 0.25f);
                view.transform.position = new Vector3((index - (wave.count - 1) * 0.5f) * 3.0f, currentWave == contract.runtime_scenario.waves.Length ? 1f : 0.75f, 7.0f + spawnJitter);
                view.transform.localScale = currentWave == contract.runtime_scenario.waves.Length ? new Vector3(1.6f, 2f, 1.6f) : new Vector3(1.25f, 1.5f, 1.25f);
                view.GetComponent<Renderer>().sharedMaterial = currentWave == contract.runtime_scenario.waves.Length ? eliteMaterial : enemyMaterial;
                enemies.Add(new EnemyState { Config = config, View = view, Health = config.max_health });
            }
            telemetry.waves_completed = currentWave - 1;
            message = $"Wave {currentWave}/{contract.runtime_scenario.waves.Length}: {config.display_name}";
        }

        private void BeginWaveTelemetry()
        {
            waveStartedAt = Time.time;
            waveStartBasicAttacks = telemetry.basic_attacks;
            waveStartSkillUses = telemetry.skill_uses;
            waveStartDamageDealt = telemetry.damage_dealt;
            waveStartDamageTaken = telemetry.damage_taken;
            waveStartDefeated = telemetry.enemies_defeated;
        }

        private void CompleteCurrentWave()
        {
            WaveConfig wave = contract.runtime_scenario.waves[currentWave - 1];
            waveResults.Add(new WaveRuntimeTelemetry
            {
                wave = wave.wave,
                enemy_id = wave.enemy_id,
                enemies_spawned = wave.count,
                enemies_defeated = telemetry.enemies_defeated - waveStartDefeated,
                basic_attacks = telemetry.basic_attacks - waveStartBasicAttacks,
                skill_uses = telemetry.skill_uses - waveStartSkillUses,
                damage_dealt = telemetry.damage_dealt - waveStartDamageDealt,
                damage_taken = telemetry.damage_taken - waveStartDamageTaken,
                duration_seconds = Time.time - waveStartedAt,
            });
            telemetry.waves_completed = currentWave;
            telemetry.wave_results = waveResults.ToArray();
        }

        private void ClampPlayerToArena()
        {
            const float arenaRadius = 10f;
            Vector2 planar = new(player.transform.position.x, player.transform.position.z);
            if (planar.magnitude > arenaRadius) planar = planar.normalized * arenaRadius;
            player.transform.position = new Vector3(planar.x, 1f, planar.y);
        }

        private void TryUpgrade()
        {
            UpgradeConfig upgrade = contract.configs.upgrade_config.OrderBy(row => row.level).FirstOrDefault();
            if (upgrade == null) return;
            CostItem goldCost = upgrade.cost_items.FirstOrDefault(item => item.item_id == "item_gold");
            if (goldCost == null || gold < goldCost.amount) return;
            gold -= goldCost.amount;
            telemetry.gold_spent += goldCost.amount;
            playerAttack += upgrade.attack_bonus;
            telemetry.final_attack = playerAttack;
            ShowFeedback($"升级成功：攻击力提升至 {playerAttack}");
        }

        private static Material CreateMaterial(Shader shader, Color color)
        {
            Material material = new(shader);
            material.SetColor("_Color", color);
            return material;
        }

        private void CreateArenaMarkers(Shader shader)
        {
            Material lineMaterial = CreateMaterial(shader, new Color(0.14f, 0.24f, 0.27f));
            for (int value = -8; value <= 8; value += 4)
            {
                GameObject horizontal = GameObject.CreatePrimitive(PrimitiveType.Cube);
                horizontal.transform.position = new Vector3(0, 0.01f, value);
                horizontal.transform.localScale = new Vector3(20, 0.02f, 0.08f);
                horizontal.GetComponent<Renderer>().sharedMaterial = lineMaterial;
                Destroy(horizontal.GetComponent<Collider>());

                GameObject vertical = GameObject.CreatePrimitive(PrimitiveType.Cube);
                vertical.transform.position = new Vector3(value, 0.01f, 0);
                vertical.transform.localScale = new Vector3(0.08f, 0.02f, 20);
                vertical.GetComponent<Renderer>().sharedMaterial = lineMaterial;
                Destroy(vertical.GetComponent<Collider>());
            }
        }

        private static int GoldRewardAmount(RewardConfig reward)
        {
            if (reward == null || !reward.once_only) return 0;
            if (reward.reward_items == null || reward.reward_items.Length == 0) return 300;
            return reward.reward_items.Where(item => item != null && item.item_id == "item_gold").Sum(item => item.amount);
        }

        private bool HasGameplayInput()
        {
            return Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.A) || Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.D)
                || Input.GetKeyDown(KeyCode.Space) || Input.GetKeyDown(KeyCode.Q);
        }

        private void ShowFeedback(string value)
        {
            combatFeedback = value;
            feedbackUntil = Time.time + 1.5f;
        }

        private void Finish(string status)
        {
            if (completed) return;
            completed = true;
            telemetry.status = status;
            telemetry.frame_count = Time.frameCount;
            telemetry.waves_completed = status == "completed" ? contract.runtime_scenario.waves.Length : currentWave - 1;
            telemetry.wave_results = waveResults.ToArray();
            telemetry.completion_time_seconds = Time.time - startedAt;
            telemetry.exported_at_utc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture);
            string path = ResolveTelemetryPath();
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, JsonUtility.ToJson(telemetry, true));
            message = $"Run {status}. Telemetry: {path}";
            Debug.Log(message);
            if (autoRun) StartCoroutine(QuitAfterCleanup(status == "completed" ? 0 : 1));
        }

        private static IEnumerator QuitAfterCleanup(int exitCode)
        {
            yield return new WaitForEndOfFrame();
            yield return null;
            Application.Quit(exitCode);
        }

        private static string ResolveTelemetryPath()
        {
            string[] args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, "--telemetry-output");
            return index >= 0 && index + 1 < args.Length
                ? Path.GetFullPath(args[index + 1])
                : Path.Combine(Application.persistentDataPath, "telemetry.json");
        }

        private IEnumerator CapturePreview()
        {
            yield return null;
            yield return new WaitForEndOfFrame();
            string[] args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, "--screenshot-output");
            string path = index >= 0 && index + 1 < args.Length
                ? Path.GetFullPath(args[index + 1])
                : Path.Combine(Application.persistentDataPath, "runtime_preview.png");
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            const int width = 1280;
            const int height = 720;
            RenderTexture target = new(width, height, 24);
            Texture2D image = new(width, height, TextureFormat.RGB24, false);
            RenderTexture previous = RenderTexture.active;
            gameplayCamera.targetTexture = target;
            gameplayCamera.Render();
            RenderTexture.active = target;
            image.ReadPixels(new Rect(0, 0, width, height), 0, 0);
            image.Apply();
            File.WriteAllBytes(path, image.EncodeToPNG());
            gameplayCamera.targetTexture = null;
            RenderTexture.active = previous;
            Destroy(target);
            Destroy(image);
            Debug.Log($"Runtime preview written: {path}");
            if (args.Contains("--screenshot-only")) Application.Quit(0);
        }

        private void OnGUI()
        {
            GUI.Box(new Rect(18, 18, 440, 170), "GameConfig Agent | Unity 运行验证");
            GUI.Label(new Rect(36, 50, 405, 24), message);
            if (contract == null) return;
            GUI.Label(new Rect(36, 76, 405, 24), $"武器：训练剑 | 攻击力：{playerAttack}");
            GUI.Label(new Rect(36, 100, 405, 24), $"生命：{Mathf.Max(0, playerHealth)}/{contract.runtime_scenario.player.max_health} | 金币：{gold}");
            GUI.Label(new Rect(36, 124, 405, 24), $"波次：{Mathf.Min(currentWave, contract.runtime_scenario.waves.Length)}/{contract.runtime_scenario.waves.Length} | 剩余敌人：{enemies.Count}");
            EnemyState nearest = enemies.OrderBy(PlanarDistanceTo).FirstOrDefault();
            if (nearest != null) GUI.Label(new Rect(36, 148, 405, 24), $"最近目标：{nearest.Config.display_name} | 距离：{PlanarDistanceTo(nearest):0.0}");

            GUI.Box(new Rect(Screen.width * 0.5f - 230, Screen.height - 66, 460, 44), "WASD 移动   |   Space 普通攻击   |   Q 技能   |   U 升级");
            if (Time.time < feedbackUntil) GUI.Box(new Rect(Screen.width * 0.5f - 150, 34, 300, 38), combatFeedback);

            foreach (EnemyState enemy in enemies)
            {
                Vector3 screen = gameplayCamera.WorldToScreenPoint(enemy.View.transform.position + Vector3.up * 1.8f);
                if (screen.z <= 0) continue;
                float x = screen.x - 55;
                float y = Screen.height - screen.y;
                GUI.Box(new Rect(x, y, 110, 20), enemy.Config.display_name);
                GUI.color = new Color(0.95f, 0.2f, 0.18f);
                GUI.DrawTexture(new Rect(x, y + 21, 110 * Mathf.Clamp01(enemy.Health / enemy.Config.max_health), 6), Texture2D.whiteTexture);
                GUI.color = Color.white;
            }
        }
    }
}
