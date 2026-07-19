# Agentic Game R&D Lab

AI Agent 驱动的 Unity 游戏研发与质量保障实验室。项目将策划配置生成、代码质量审查、Unity 可控运行环境和 telemetry 证据放进同一个本地单仓库。

**Milestone 0–5 已完成。** 测试床能够对同一配置执行固定种子双跑，并在本机存在第三方模型时动态替换占位角色；受控 Code Change Agent 只生成候选补丁，必须经过人工审批与隔离 Unity 验证。

## 当前组成

- `services/agent-python`：唯一 Python 运行时，包含 GameConfig 配置能力与 DevQuality Python 质量审查能力。
- `game-unity`：从 GameConfig Runtime Demo 迁移的 Unity 6 测试床。
- `web-console`：唯一 React 控制台。
- `runtime-artifacts`：本地运行证据，不提交 Git。
- `local-assets`：灵梦 PMX、转换文件和其他第三方本地资产，不提交 Git。

## 首次准备

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\bootstrap.ps1
```

## 启动后端

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\start-backend.ps1
```

后端入口：

- Health：`http://127.0.0.1:8000/api/health`
- OpenAPI：`http://127.0.0.1:8000/docs`
- 配置工作台 API：保留原 GameConfig 路由。
- 质量审查：`POST /api/quality/review`
- 配置变更提案：`POST /api/change-workflows`
- 人工 C# Diff 提案：`POST /api/code-workflows`
- Code Change Agent 候选生成：`POST /api/code-change-agent/proposals`
- Code Change Benchmark 数据集：`GET /api/code-change-agent/benchmark/dataset`
- 运行 Code Change Benchmark：`POST /api/code-change-agent/benchmark`

## 启动前端

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\start-web.ps1
```

打开 `http://127.0.0.1:5173`。

端口被占用时可以成对指定，例如：

```powershell
.\scripts\start-backend.ps1 -Port 8001
.\scripts\start-web.ps1 -Port 5174 -BackendPort 8001
```

策划视图的推荐流程：

```text
填写需求 -> 创建变更提案 -> 查看 Config Diff 与质量审查 -> 人工批准
-> 准备隔离 Unity 测试 -> 手动试玩或固定种子自动试玩
-> 查看 telemetry 证据 -> 接受 / 要求修订 / 回滚
```

可直接使用以下需求验证字段变化：

```text
将新手试炼武器基础攻击力改为 45，通关目标 60-90 秒，击败 5 个敌人，技能至少使用 1 次。
```

Mock 不会自由创作配置：它从已提交的 Training Sword 基线出发，只应用能力清单内的明确约束。真实 Provider 仍必须经过相同的静态校验、人工审批和 Unity 运行证据。详见 `docs/MILESTONE3A_CONFIG_CHANGE_WORKFLOW.md`。

开发者调试视图另提供人工 C# Diff 闭环：安全门和 Quality Review Agent 审查开发者写好的补丁，批准后只在 `runtime-artifacts/code-workflows` 的 Unity 副本中应用和验证。“接受”不会自动合并主仓库。详见 `docs/MILESTONE3B_CSHARP_DIFF_WORKFLOW.md`。

Milestone 4 在这条闭环前增加受控候选生成：开发者显式选择最多 3 个运行时 C# 文件，Agent 只能基于这些文件返回结构化候选 Diff；默认 Mock 只支持一个空参数保护 recipe。详见 `docs/MILESTONE4_CONTROLLED_CODE_CHANGE_AGENT.md`。

Milestone 5 使用 12 个固定样本验证需求门禁、JSON 契约、目标范围、安全门和 badcase 路由。默认 `scripted_fixture` 只评测工程护栏，不代表真实模型代码能力。运行：

```powershell
cd D:\Desktop\agentic-game-rd\services\agent-python
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli run_code_change_benchmark --output ..\..\runtime-artifacts\code-change-benchmark
```

详见 `docs/MILESTONE5_CODE_CHANGE_BENCHMARK.md`。

## Unity

在 Unity Hub 中添加：

```text
D:\Desktop\agentic-game-rd\game-unity
```

项目锁定 Unity `6000.3.19f1`。没有本地灵梦模型时使用仓库内占位角色；本地模型后续通过 `CharacterViewResolver` 动态替换，不改变战斗逻辑。

### 本地灵梦表现层

第三方模型只保留在 Git 忽略目录。首次准备和转换：

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\bootstrap-blender.ps1
.\scripts\convert-reimu.ps1
.\scripts\import-reimu-unity.ps1
.\scripts\smoke-reimu-presentation.ps1
```

脚本使用 Blender `4.5.11 LTS` portable 与 MMD Tools `v4.5.10`，自动完成 PMX 导入、FBX 导出、Unity 材质绑定、本地 Prefab 创建、固定种子回归和截图像素检查。Portable 版本与安装版具备相同建模和转换功能，本项目不需要另装完整版。工具链、模型、FBX、贴图和 Prefab 都不会进入 Git。

### 灰盒自动战斗测试床

测试画像位于 `scenarios/milestone1/starter_trial_baseline.json`，固定场景、随机种子和验收指标。运行：

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\smoke-unity.ps1
```

脚本会构建一次 Unity Windows Player，使用同一 seed 自动运行两次，并在 `runtime-artifacts/unity-smoke/` 生成：

- `telemetry.json`
- `telemetry_repeat.json`
- `testbed_evaluation.json`
- `testbed_evaluation_report.md`

该证据证明自动测试可重复，不等同于真实玩家体验或统计学平衡结论。详细说明见 `docs/MILESTONE1_GREYBOX_TESTBED.md`。

## 验证

```powershell
.\scripts\test-all.ps1
```

也可以分别运行：

```powershell
.\scripts\test-python.ps1
.\scripts\test-web.ps1
.\scripts\smoke-unity.ps1
.\scripts\verify-repo-clean.ps1
```

## 当前边界

- 不使用 DevQuality 旧 Go 后端、旧前端、PostgreSQL 或 Redis。
- Code Change Agent 只生成候选 Diff，不能读取未授权文件、写主仓库或自动合并。
- 人工 C# Diff 只在审批后的隔离 Unity 副本中应用，系统不自动生成或合并补丁。
- 配置候选只写入 `runtime-artifacts/change_workflows` 和独立 Unity run，不覆盖已提交基线。
- 不公开分发灵梦模型、贴图或本地音频。
- 单次 Unity 前后对比不宣称为统计学 A/B 实验。

详细来源、工具链和迁移结果见 `docs/`。
