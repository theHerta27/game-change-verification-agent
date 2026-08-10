# Milestone 8：UE5 跨引擎最小垂直切片

## 结论

Milestone 8 complete。项目已在保留 Unity 弹幕闭环的前提下，完成真实 UE5 C++ Windows Player 跨引擎验证：

- UE 5.8.1 工程真实编译并打包；
- `BulletHellUE.exe` 完成 Baseline / Candidate 双跑；
- 使用同一 Bullet Hell 1.0 契约、同一 seed、固定轨迹、36 秒时长和 10/20/30 秒截图；
- Telemetry、截图、配置哈希和运行日志全部通过校验；
- `UnrealEngineRunner` 当前返回 `verified`。

## 本机环境

- Unreal Editor：`D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe`
- UE 版本：`5.8.1-56057345+++UE5+Release-5.8`
- Visual Studio 2022 Build Tools：17.14
- MSVC：14.44.35207
- Windows SDK：10.0.26100.0
- 注册 Player：`game-unreal\BulletHellUE\Builds\Windows\BulletHellUE.exe`

## 工程边界

`game-unreal/BulletHellUE/` 是独立最小垂直切片：

- `BulletHellContract.cpp` 使用 `FJsonSerializer + FJsonObject` 严格读取 `bullet_hell_contract_version: "1.0"`；
- 支持 `ring`、`aimed_fan`、`spiral`、`petal` 四种 Pattern，未知字段和越界数值直接返回错误；
- `BulletHellSimulation` 在 C++ 中执行固定步长确定性模拟、固定轨迹、碰撞、Boss 阶段和 Telemetry；
- Blueprint 只负责 Level、玩家、Boss 和子弹表现；
- 自动运行接受命令行指定的 config、telemetry、log、seed、run id、variant、config hash 和截图目录。

## Runner 与安全限制

`services/agent-python/workflow/engines/unreal.py` 实现统一 `EngineRunner`：

- 状态区分 `unavailable / build_required / available / verified / failed`；
- 只启动仓库预注册 Player，不接受任意 EXE 或任意命令；
- 自动运行路径必须位于 `runtime-artifacts`；
- 校验 Telemetry JSON、`config_hash`、完成状态、异常日志、截图和 `capture_manifest.json`；
- 缺引擎、缺 Build、超时、缺 Telemetry、哈希不一致、缺截图和 unsupported Pattern 均返回真实失败证据；
- 原始 Unity artifact 字段不修改，跨引擎公共字段写入规范化证据。

## 真实运行证据

使用以下脚本完成构建与运行：

```powershell
.\scripts\build-unreal.ps1
.\scripts\smoke-unreal.ps1
```

最新成功运行：

```text
runtime-artifacts/ue5-verification/ue5_smoke_20260731_231202/
```

### Baseline / Candidate 指标

| 指标 | Baseline | Candidate |
|---|---:|---:|
| total_bullets_spawned | 592 | 992 |
| peak_alive_bullets | 70 | 192 |
| player_hits | 1 | 0 |
| player_survival_seconds | 36 | 36 |
| average_fps | 59.6563 | 59.8583 |
| low_percentile_fps | 59.8874 | 59.9995 |
| minimum_fps | 20.5058 | 21.6646 |
| runtime_error_count | 0 | 0 |

### 真实工作流证据

除 smoke 外，真实 Web/API workflow `bullet_20260731_230825_8c13b17d` 已用 `engine=unreal` 完成 Baseline + `candidate_1`：

- 状态：`evidence_ready`；
- 候选运行数：`runs_used=1`；
- Config Diff：phase_2 `bidirectional false -> true`、`bullets_per_wave 12 -> 16`；
- Candidate Telemetry：峰值存活子弹 `158`、受击 `3`、生存 `36s`、低分位 FPS `59.9977`、异常日志 `0`；
- `visual_comparison.json`：Baseline/Candidate 各 3 张截图，10/20/30 秒对齐。

### 阶段覆盖

Baseline 与 Candidate 使用同 seed、同固定轨迹，阶段结构一致：

- phase_1 `ring`：0–12.6833s；
- phase_2 `spiral`：12.6833–26.5664s；
- phase_3 `petal`：26.5664–36s。

第 10、20、30 秒截图分别对应 phase_1、phase_2、phase_3。已人工核验：

- 20 秒处 Baseline 为单向螺旋，Candidate 为双向螺旋，候选更密；
- 30 秒处两侧均为花瓣弹幕，Candidate 明显更密集；
- 画面非黑屏、非占位错误，UE 渲染有效。

## Web / API

- `GET /api/bullet-hell/capabilities` 返回 `unreal.status=verified`；
- Web 策划视图支持 Unity 6 / Unreal Engine 5 切换，未就绪时禁用运行按钮；
- 自动画面对比组件按 engine 调用统一 Runner，并排展示 Baseline / Candidate 截图；
- 手动试玩接口只允许当前 workflow 的 baseline / candidate 快照。

## 验收

- Python 全量：`164 passed`，1 条既有 Starlette/httpx 弃用告警；
- Web production build：通过，`1585 modules transformed`；
- UE5 C++ Windows Player：真实构建通过；
- UE5 Baseline / Candidate：真实双跑通过；
- Telemetry 与六张截图：全部存在并通过配置哈希校验；
- `runner_verification.json`：`verified`。
- `verification_manifest.json`：最新 smoke 双跑证据完整。

## 边界说明

- UE C++ 是灰盒确定性验证切片，不是完整商业游戏或表现层成品；
- 跨引擎数值不逐帧比较，只验证同一契约、同条件趋势和证据完整性；
- 固定轨迹结果只代表该轨迹下的可重复证据，不宣称所有玩家体验；
- `runtime-artifacts/` 与 UE `Builds/` 等本地产物不提交 Git。

## 手动试玩与目录说明

- `game-unreal/BulletHellUE/Build/` 是 Unreal Build Tool 生成或使用的构建辅助元数据，不是可直接运行的游戏。
- `game-unreal/BulletHellUE/Builds/Windows/` 是本项目脚本约定的 Windows 打包归档目录，网页只允许启动其中注册的 `BulletHellUE.exe`。
- 不要直接双击 `BulletHellUE.exe`。Player 需要工作流快照、版本、随机种子、Telemetry 和日志路径等受控命令行参数；缺少参数时会主动退出。正确入口是 Web 策划视图中的“手动体验修改前/修改后”。
- 手动模式使用可见窗口，不传 `-RenderOffscreen`；自动 A/B 验证继续离屏运行。后端只有在 Player 日志出现 `Bullet Hell run initialized` 后才返回启动成功，提前退出或初始化超时会向页面返回具体错误。
- 手动 Player 在角色死亡或配置时长结束后正常退出。自动模式仍根据验证结果返回成功或失败状态码。
- Blueprint 表现资源通过 `DefaultGame.ini` 显式 Cook；打包日志和 Player 日志中不应出现 `/Game/Presentation/BP_*` 缺失。
- 模拟层使用 X/Z 玩法坐标，UE 表现层统一将玩法正 Z 映射为屏幕向上。不要通过反转 W/S 输入修补相机方向，否则会造成手动操作与固定自动轨迹语义不一致。
