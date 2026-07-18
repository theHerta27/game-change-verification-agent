# 演示脚本

## 启动准备

打开两个 PowerShell 窗口。

后端：

```powershell
cd D:\Desktop\GameConfig-Agent
.\scripts\start_backend.ps1
```

前端：

```powershell
cd D:\Desktop\GameConfig-Agent
.\scripts\start_frontend.ps1
```

如果提示 5173 被占用：

```powershell
.\scripts\start_frontend.ps1 -Port 5174
```

打开前端页面：

```text
http://127.0.0.1:5173
```

注意：`http://127.0.0.1:8000` 是后端 API，不是前端页面。后端窗口需要保持打开；关闭窗口或按 `Ctrl+C` 会停止服务。前端页面从 `http://127.0.0.1:5173` 打开。

## 投屏顺序

1. 先打开 Web Console 首页，确认默认处于“策划 / QA 视图”和中文界面。
2. 展示左侧控制区：经典案例、配置需求、模型提供方、超时时间和运行按钮。
3. 模型提供方保持 `mock`，保证演示结果稳定。
4. 默认选择 `case_01_baseline_trial`，点击“生成并校验当前需求”。
5. 先展示“运行验证”：它把策划目标、Unity 实测、状态和证据路径放在同一张表中。失败项是配置偏差，不是程序崩溃。
6. 点击“准备本次 Unity 测试”，说明系统创建了独立 `run_id` 和本次配置快照。
7. 点击“打开 Unity 手动试玩”，完成三波战斗后回到 Web Console。
8. 展示“本次验证结论”：通过或未通过、关键风险数量和下一步建议。
9. 展示策划结果表：目标、实测、结果、影响和建议。先讲业务结论，不打开 JSON。
10. 切换到“开发者调试”视图，打开本次 `telemetry.json`、`runtime_evaluation_report.md` 和改进建议。
11. 展示“工作流摘要”，说明最终校验、trace 步骤数、修复动作数和测试场景数量。
12. 展示“Agent / Tool 时间线”。“发现配置问题”表示草案进入修复，不表示工具异常。
13. 依次展示：
   - 黑板追踪
   - 配置草案
   - 校验错误
   - 审查发现
   - 修复动作
   - 最终配置
   - 测试场景
14. 回到策划视图并切换 `case_02_reward_overgrant`。可以准备新的独立 run，展示首通经济评估；系统用 Gold 和 Refine Stone 同时计算连续两次升级可支付性。
15. 切换 `case_03_combat_too_fast`。准备并运行新的独立 run，展示实测通关时间相对 60-90 秒目标的偏差。
16. 在开发者调试视图点击“运行离线回归评测（10 个固定样本）”，展示指标和坏例，并明确它不启动 Unity。
17. 需要展示静态校验能力时切换 `case_04_missing_reference`，展示 Trial Medal 缺失引用与受约束修复；该案例不允许启动 Unity。
18. 需要讨论技能引导边界时切换 `case_05_skill_guidance_balance`。当前只以技能次数和通关时间作弱验证，不宣称已证明教学效果。
19. 如需要面向技术面试官，可切换英文界面；JSON 字段和 artifact 路径始终保持英文契约。

## 案例与证据边界

- 主线：`case_01 -> case_02 -> case_03`。
- 专项展示：`case_04 -> case_05`。
- Mock 只产生确定性的 Training Sword 配置，案例选择改变需求文本和评估重点。
- Guided Run 会为 `case_01/02/03` 分别创建独立 `run_id`、contract 和 telemetry；旧的案例证据概览仍可能读取历史 latest telemetry，只作为兼容展示。
- 手动修改预设需求后，选择器自动切换到“手动输入”，保留自由演示能力。

## 讲解重点

### 业务问题

策划配置生成不是简单让模型写一段 JSON。真实研发中，配置需要满足结构、引用、规则、数值和测试要求。这个项目把生成结果放进可校验、可修复、可评测的流程里。

### 多 Agent Blackboard

Generator、Reviewer、Repairer、Test Scenario Agent 不直接互相传隐式状态，而是围绕同一个 blackboard 读写：需求、结构化需求、草案配置、校验错误、审查发现、修复动作、最终配置和 trace。

### Repair Loop

系统会故意生成不完美草案。确定性工具发现 schema、引用和规则问题。Reviewer 只做审查，不改配置。Repairer 在受限范围内做局部修复，并记录 before/after。

### Benchmark 与 Badcases

Phase 3 有 10 个样本，覆盖正常配置和 hardcase。badcase 不是隐藏失败，而是暴露系统边界，方便说明当前能力和后续改进方向。

### MockLLM 与真实 Provider

MockLLM 是默认路径，用于稳定演示和测试。OpenAI-compatible provider 是可选真实路径，凭据来自环境变量或 `.env`。真实输出必须经过 JSON 解析、schema 校验、引用校验、规则校验和 badcase 记录。

## 收尾讲法

最后不要说“这个系统已经完整替代策划”。更好的讲法是：

“这个原型验证了策划配置生成在研发管线里的关键闭环：生成、校验、修复、测试、评测和可追踪。下一步我会优先补真实配置样本、历史设计参考和更贴近业务的平衡性指标，而不是继续堆更多页面或 Agent。”
