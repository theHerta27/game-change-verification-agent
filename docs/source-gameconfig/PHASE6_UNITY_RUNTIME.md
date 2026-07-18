# Phase 6：Unity Runtime Validation

## 目标

Phase 6 将 GameConfig Agent 从“配置生成与静态校验原型”推进为“可在真实游戏运行时验证的工具链”。

第一版采用小型新手 RPG 试玩关卡，验证以下闭环：

```text
策划需求 -> final_configs -> Unity Runtime Contract -> 试玩/自动战斗
         -> telemetry.json -> Runtime Evaluator -> 目标偏差
```

## 当前范围

- Unity 版本：`6000.3.19f1`
- 场景：三波新手训练竞技场
- 玩家能力：移动、普通攻击、一个范围技能
- 配置影响：武器基础攻击、升级攻击增量、升级金币消耗、首次奖励
- 运行指标：波次、击杀、攻击次数、技能次数、伤害、金币、最终攻击和通关时间
- 不包含：联网、复杂美术、动画系统、开放世界、商业游戏 IP 或数据库

敌人和波次目前属于 Runtime Scenario 基线，用来验证现有武器、升级和奖励配置。后续再将角色、技能、敌人和关卡纳入 Agent Schema，避免第一步同时扩大生成域和运行域。

## 启动试玩

在项目根目录运行：

```powershell
.\scripts\start_unity_demo.ps1
```

首次运行会构建 Windows 演示程序，后续会直接启动。操作方式：

- `WASD`：移动
- `Space`：普通攻击
- `Q`：技能
- `U`：升级

## 手动导出 Runtime Contract

```powershell
python -m gameconfig_agent.cli export_unity_runtime_config `
  --config outputs\phase0\final_configs.json `
  --output unity\GameConfigRuntimeDemo\Assets\StreamingAssets\game_config.json
```

## 运行评测

Unity 自动运行会输出 `outputs/unity/telemetry.json`。评测命令：

```powershell
python -m gameconfig_agent.cli evaluate_unity_runtime `
  --contract unity\GameConfigRuntimeDemo\Assets\StreamingAssets\game_config.json `
  --telemetry outputs\unity\telemetry.json `
  --output outputs\unity
```

评测未通过时命令返回非零，但仍会生成：

- `outputs/unity/runtime_evaluation.json`
- `outputs/unity/runtime_evaluation_report.md`

## 首次真实结果

- Unity 运行状态：完成
- 完成波次：3
- 击败敌人：5
- 通关时间：约 16.45 秒
- 获得金币：300
- 第一次升级花费：100
- 最终攻击力：55
- Runtime target pass rate：60%

未通过项：

1. 通关时间低于 20 秒目标下限，关卡节奏过快。
2. 首通奖励支付第一次升级后仍足够支付第二次升级，不符合经济目标。

这些偏差是 Phase 6 的有效产出。下一步应让 Reviewer / Repairer 根据运行指标调整相关配置，再重新运行 Unity 验证，而不是手工修改报告。

## 手动试玩 Hotfix

首次手动试玩暴露了以下问题：默认运行时材质在 Windows Build 中变成粉紫色；玩家与敌人无法从地面中辨认；旧 Axis 输入与固定镜头使 WASD 缺少反馈。

修复内容：

- 新增项目内置 `GameConfig/SolidColor` Shader，避免依赖构建时被裁剪的默认 Shader。
- 深色网格地面、蓝色玩家、橙色普通敌人、红色精英敌人使用明确阵营色。
- WASD 改为直接读取 `KeyCode.W/A/S/D`，移动时角色面向移动方向。
- 摄像机跟随玩家并持续看向前方战斗区域。
- 开局暂停敌人逻辑，等待玩家首次输入后再开始战斗。
- HUD 增加中文状态、最近目标、距离、头顶血条和攻击/技能反馈。
- 启动脚本会比较 Assets 与可执行文件时间，源码更新后自动重新构建。

修复版已通过 Unity 编译、Windows Build、离屏真实渲染和自动战斗回归。预览图输出为 `outputs/unity/runtime_preview_hotfix.png`。

## 经典案例与运行验证证据链

Web Console 提供 5 个固定案例。它们用于固定系统能力和评估视角，不代表五套不同 Mock 输出，也不代表五个独立 Unity 关卡：

- `case_01`：完整基线，允许部分 runtime target 失败。
- `case_02`：基于 Classic Case Evaluation Profile 的多资源首通经济计算，同时检查 Gold 与 Refine Stone。
- `case_03`：用最近一次 Unity 通关时间检查 60-90 秒节奏目标。
- `case_04`：Trial Medal 缺失引用的 Reference Checker 与 Repair Actions 静态证据，不使用 Unity telemetry。
- `case_05`：技能使用和通关时间的弱验证，`validation_strength=weak`。

`RuntimeTelemetryNormalizer` 只在读取后规范化字段别名，不修改原始 `telemetry.json`。字段缺失时返回 `unavailable`，不会用 0 伪造实测值。

只读 API：

```text
GET /api/classic-cases
GET /api/evaluation-evidence?case_id=case_01_baseline_trial
```

证据面板会展示 telemetry 来源、评估视角、检查项、策划目标、实际结果、状态和证据路径。产物不存在时显示生成提示，不构造虚假结果。

## 贴身攻击修复

贴身攻击无伤害不是设计意图。命中与选敌已统一改为 XZ 平面距离，目标按平面最近距离选择，距离 0 仍可命中。`Space` 支持点按和按住连续攻击，冷却期间显示剩余时间。

构建时距离 smoke 固定验证：`0`、`1.0`、`3.2` 命中，`3.21` 不命中。修复后自动战斗仍能完成三波并生成 telemetry；最终仍需用户在可视窗口手动复测贴身攻击手感。
