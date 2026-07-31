# 简历叙事与项目证据矩阵

## 结论

“跨引擎游戏研发变更验证与自动化测试智能体”这条主线成立，但必须区分三种状态：

- **已真实验证**：Unity 弹幕测试床、隔离 Before/After、Telemetry、固定轨迹截图、有限修复与人工决策。
- **已实现并通过自动测试**：有界双 Agent、四层确定性校验、统一 EngineRunner、Unity Runner 等价适配。
- **已真实验证**：UE5 C++ 工程、Blueprint 表现层、Windows Player、UE Baseline/Candidate 和真实截图。

因此，UE 段落现在可以进入最终投递版简历，但仍需按下方“需要收紧的表述”限定证据边界。

## 需要收紧的表述

1. 使用“受控 Before/After 回归对比”，不使用容易被理解为统计实验的“A/B 测试”。
2. 使用“中央状态机编排的有界双 Agent”，不宣称自治多智能体系统。
3. `100%` 必须写成“20 个固定脚本化护栏样本路由匹配率 100%”，不解释为真实模型总体准确率。
4. 最新可复现案例填写：峰值存活子弹 `66 → 198`、低分位 FPS `58.65`、异常日志 `0`。
5. 当前 Python 测试为 `164 passed`，不是原草稿中的 `153`。
6. UE JSON 已准确写成 `FJsonSerializer + FJsonObject`；截图通过 `FScreenshotRequest::RequestScreenshot` 在 10/20/30 秒固定时间点输出。若简历仍写 `FHighResScreenshotManager`，应改成 `FScreenshotRequest::RequestScreenshot`，因为 UE5 实际源码未使用该类名。

## 证据矩阵

| 简历主张 | 当前状态 | 源代码 | 测试 | 运行证据 / 演示 |
|---|---|---|---|---|
| 自建 Unity 2.5D 弹幕 Boss 战测试床 | 已真实验证 | `game-unity/Assets/Scripts/BulletHellRuntimeBootstrap.cs`、`PatternEmitter.cs`、`ProjectilePool.cs` | Unity smoke 与 Python contract 回归 | `runtime-artifacts/bullet-hell-workflows/bullet_20260728_111919_0485bf8c/` |
| 环形、扇形、螺旋、花瓣四种配置化弹幕 | 已真实验证 | `game-unity/Assets/Scripts/BulletHellPatternMath.cs`、`services/agent-python/gameconfig_agent/bullet_hell.py` | `test_bullet_hell_contract.py` | Unity 场景可手动试玩；固定轨迹运行覆盖主演示模式 |
| 手写有界 Agent Loop | 已实现并测试 | `services/agent-python/workflow/bullet_hell_workflow.py` | `test_bullet_hell_workflow.py` | 最多 3 次候选运行、4 次模型调用、最终人工决策 |
| Requirement Agent | 已实现并测试 | `gameconfig_agent/agents/bullet_hell_agents.py`、`prompts/bullet_hell_requirement_agent.md` | Fake OpenAI-compatible 双 Prompt 测试 | Web 显示 Agent 名称、Provider、Prompt 和输出 artifact |
| Quality Review Agent | 已实现并测试 | `gameconfig_agent/agents/bullet_hell_agents.py`、`prompts/bullet_hell_quality_review_agent.md` | 审查成功与 malformed output badcase 测试 | 双 Agent 契约已接入工作流；真实 Provider 调用需配置 `.env` |
| 四层确定性校验 | 已实现并测试 | `validate_bullet_hell_proposal()` | Schema、引用缺失、越权修改测试 | `validation_results.json.layers` |
| 模型不直接计算修复数值 | 已验证 | Agent 只输出 `repair_action`；`apply_repair()` 计算数值 | 策略门与修复回归 | `quality_reviews.json` + `repair_history.json` |
| 隔离 Before/After 公平对比 | 已真实验证 | 固定 seed、60Hz 逻辑步、固定轨迹和 36 秒运行 | 固定 seed 双跑 smoke | Baseline/Candidate Telemetry 与 10/20/30 秒六张截图 |
| 运行指标采集 | 已真实验证 | `BulletHellTelemetryRecorder.cs` | Telemetry schema / evaluator 测试 | 峰值子弹、受击、生存、阶段、FPS、异常日志 |
| 受限 Player 启动 | 已真实验证 | `bullet_hell_workflow.py`、`UnityEngineRunner` | variant、artifact 和路径拒绝测试 | Web 手动启动只允许当前 workflow 的 baseline/candidate |
| Mock / OpenAI-compatible Provider | 已实现并测试 | `providers/openai_compatible.py`、两个 Agent Prompt | JSON 漂移、超时、坏例和双 Prompt 测试 | 真实 Provider 候选生成已有历史证据；新版双 Agent 真实 smoke 待补 |
| 20 样本护栏路由匹配率 100% | 已验证但范围有限 | `workflow/bullet_hell_benchmark.py`、`evals/` | `test_bullet_hell_benchmark.py` | 仅代表固定脚本化工程回归，不代表真实模型质量 |
| 统一 EngineRunner | 已实现并测试 | `workflow/engines/base.py`、`unity.py`、`unreal.py`、`telemetry.py` | `test_engine_runners.py` | Unity 本轮 Licensing 阻塞但历史闭环已验证；UE5 当前返回 `verified` |
| 引擎无关配置契约 | Unity 与 UE5 均已真实验证 | `configs/bullet-hell/baseline.json`、`BulletHellContract` | Pydantic contract 测试 | UE5 实际读取相同 `bullet_hell_contract_version: 1.0` |
| UE5 C++ JSON / CLI / 固定种子 / Telemetry | 已真实验证 | `game-unreal/BulletHellUE/Source/` | `scripts/build-unreal.ps1`、`scripts/smoke-unreal.ps1` | `ue5_smoke_20260731_231202`，Telemetry 与配置哈希校验通过 |
| Blueprint Level / 玩家 / Boss 表现层 | 已真实验证 | `game-unreal/BulletHellUE/Content/` | UE5 打包与自动截图 | Baseline/Candidate 各 3 张 10/20/30 秒截图 |
| UE Baseline/Candidate 自动运行与结果比对 | 已真实验证 | `UnrealEngineRunner` | 真实 UE5 smoke 与单元测试 | Baseline `70` / Candidate `192` 峰值存活子弹，受击 `1 -> 0` |

## 当前可安全使用的项目介绍

> 我先用 Unity 6 自建了一个可配置的 2.5D 弹幕 Boss 战测试床，再围绕它实现中央状态机编排的有界双 Agent 变更验证闭环。Requirement Agent 生成结构化目标和候选配置，确定性 Schema、引用、规则与安全门拦截非法变更；人工授权后，引擎以相同 seed、固定轨迹和时长运行修改前后版本。Quality Review Agent 只基于需求、Config Diff 和 Telemetry 选择接受、有限修复或人工复核，具体数值由确定性工具计算，最多复测三轮，所有调用和证据均落盘可回放。

跨引擎部分完成真实 UE5 验证后，再补充：

> 同一 Bullet Hell 1.0 候选通过统一 EngineRunner 分别交给 Unity 和 Unreal Engine 5 执行；两个引擎不比较逐帧数值一致性，只验证契约可读取、同条件 Before/After 趋势和证据完整性。

当前该段已经成立：UE5.8.1 C++ Windows Player 已完成 Baseline/Candidate 双跑，`runner_verification.json` 状态为 `verified`。
