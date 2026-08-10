# Milestone 1：灰盒自动战斗测试床

## 目标

Milestone 1 把迁移时已有的 Unity 自动战斗 smoke 固化为可重复测试床。它回答的是：

> 同一份经过校验的游戏配置，能否在受控 Unity 环境中重复运行，并产出可比较的运行证据？

它不负责证明真实玩家觉得游戏有趣，也不把一次自动试玩解释为统计学平衡实验。

## 三类数据

### 1. Unity runtime contract

路径：`game-unity/Assets/StreamingAssets/game_config.json`

它由已校验配置导出，包含武器、升级、奖励、敌人、技能、波次和策划目标。它回答“这次要运行什么内容”。

### 2. Test profile

路径：`scenarios/milestone1/starter_trial_baseline.json`

它属于测试基础设施，固定：

- `profile_id`
- `scenario_id`
- `run_mode=auto`
- `seed=20260718`
- 预期完成波次和击败数
- 必须保持一致的 telemetry 字段
- 两次通关时间允许的误差

它回答“用什么条件验证，以及怎样算通过”。

### 3. Telemetry evidence

路径：`runtime-artifacts/unity-smoke/`

每次 Unity Player 运行独立写出 telemetry。除旧有字段外，Milestone 1 向后兼容地增加：

- `run_mode`
- `random_seed`
- `frame_count`
- `simulation_ticks`
- `wave_results`

`wave_results` 保存每波生成数、击败数、普攻、技能、造成伤害、承受伤害和耗时。

## 确定性设计

手动试玩继续在 `Update()` 读取玩家输入。自动模式改为在 `FixedUpdate()` 中推进移动、攻击和敌人逻辑，步长固定为 `1/60s`。

启动时执行：

```text
Random.InitState(seed)
Time.fixedDeltaTime = 1 / 60
run_mode = auto
```

固定 seed 控制生成位置的微小扰动；固定模拟步长消除渲染帧调度对攻击次数和承伤次数的影响。纯 telemetry 自动运行使用 Player 的 `-batchmode -nographics`，不让图形驱动退出路径影响逻辑回归；角色截图则单独使用 D3D11 图形模式。

## 运行流程

```text
读取 test profile
-> Unity 编译与资源检查
-> 固定 seed 自动运行 A
-> 写出 telemetry.json
-> 固定 seed 自动运行 B
-> 写出 telemetry_repeat.json
-> Python Testbed Evaluator 比较证据
-> 写出 evaluation JSON 和中文报告
```

执行命令：

```powershell
cd <repository-root>
.\scripts\smoke-unity.ps1
```

也可以单独评测已有 telemetry：

```powershell
cd <repository-root>\services\agent-python
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli evaluate_milestone1_testbed `
  --profile ..\..\scenarios\milestone1\starter_trial_baseline.json `
  --telemetry ..\..\runtime-artifacts\unity-smoke\telemetry.json `
  --repeat-telemetry ..\..\runtime-artifacts\unity-smoke\telemetry_repeat.json `
  --output ..\..\runtime-artifacts\unity-smoke
```

## 当前基线

固定种子 `20260718` 的两次运行均得到：

| 指标 | 结果 |
|---|---:|
| simulation_ticks | 999 |
| waves_completed | 3 |
| enemies_defeated | 5 |
| basic_attacks | 30 |
| skill_uses | 1 |
| damage_dealt | 1700 |
| damage_taken | 268 |
| completion_time_seconds | 16.6333 |

可重复性检查为 `10/10`，时间差为 `0s`。

## 工程边界

- 固定种子自动玩家是回归测试工具，不模拟真实玩家行为分布。
- 一次基线只能暴露明显配置偏差，不能替代真人 playtest。
- `completion_time_seconds` 允许画像定义的小幅容差；行为计数必须严格一致。
- 测试画像与 runtime contract 分离，避免把测试期望硬编码进游戏场景。
- 本阶段继续使用占位角色，不处理灵梦模型和正式表现层。
