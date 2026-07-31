# Agentic Game R&D Lab

AI Agent 驱动的 Unity 游戏研发与质量保障实验室。项目将策划配置生成、代码质量审查、Unity 可控运行环境和 telemetry 证据放进同一个本地单仓库。

**Milestone 0–7 已完成。** 当前主线是面向 Unity 2.5D 弹幕玩法的 Game Change Verification Agent：自然语言需求先形成候选弹幕配置，经过静态安全门、人工授权和 Unity 前后双跑，再根据 telemetry 有限修复并由人决定接受或回滚。Training Sword 旧流程继续保留。

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
- 真实代码评测配置：`GET /api/code-change-agent/real-evaluation/config`
- 真实代码评测数据集：`GET /api/code-change-agent/real-evaluation/dataset`
- 最近一次真实代码评测：`GET /api/code-change-agent/real-evaluation/latest`
- 运行真实代码评测：`POST /api/code-change-agent/real-evaluation`
- 离线重放最近结果：`POST /api/code-change-agent/real-evaluation/replay`
- 弹幕能力清单：`GET /api/bullet-hell/capabilities`
- 创建弹幕变更工作流：`POST /api/bullet-hell/workflows`
- 加载最近一次弹幕验证：`GET /api/bullet-hell/workflows/latest`
- 生成固定轨迹画面对比：`POST /api/bullet-hell/workflows/{workflow_id}/visual-comparison`
- 受限启动修改前/修改后：`POST /api/bullet-hell/workflows/{workflow_id}/play/{baseline|candidate}`
- 运行弹幕离线回归：`POST /api/bullet-hell/benchmark`

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

策划视图默认进入弹幕变更验证，推荐流程：

```text
填写弹幕需求 -> 生成候选并静态校验 -> 人工授权最多三轮隔离运行
-> Unity 同条件运行 baseline / candidate -> 查看 telemetry 和自动修复
-> 生成 10/20/30 秒固定轨迹截图并排对比
-> 接受 / 要求修订 / 回滚
```

可直接使用以下主演示需求：

```text
第二阶段改为双向螺旋弹，提高密度，但同时存在的子弹不能超过350发，最低帧率不能低于55 FPS。
```

弹幕 Mock 不会自由创作：它从已提交的弹幕基线出发，只应用支持范围内的确定性映射。真实 Provider 只负责提出候选 JSON，仍必须经过同一套静态校验、人工授权和 Unity 运行证据。详见 `docs/MILESTONE7_BULLET_HELL_CHANGE_VERIFICATION.md`。

页面把证据分为三层：自动截图回答“肉眼改了什么”，telemetry 回答“约束是否达标”，手动试玩只补充主观操作感受。手动路线不同，不作为严格的 Before / After 证明。

开发者调试视图另提供人工 C# Diff 闭环：安全门和 Quality Review Agent 审查开发者写好的补丁，批准后只在 `runtime-artifacts/code-workflows` 的 Unity 副本中应用和验证。“接受”不会自动合并主仓库。详见 `docs/MILESTONE3B_CSHARP_DIFF_WORKFLOW.md`。

Milestone 4 在这条闭环前增加受控候选生成：开发者显式选择最多 3 个运行时 C# 文件，Agent 只能基于这些文件返回结构化候选 Diff；默认 Mock 只支持一个空参数保护 recipe。详见 `docs/MILESTONE4_CONTROLLED_CODE_CHANGE_AGENT.md`。

Milestone 5 使用 12 个固定样本验证需求门禁、JSON 契约、目标范围、安全门和 badcase 路由。默认 `scripted_fixture` 只评测工程护栏，不代表真实模型代码能力。运行：

```powershell
cd D:\Desktop\agentic-game-rd\services\agent-python
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli run_code_change_benchmark --output ..\..\runtime-artifacts\code-change-benchmark
```

详见 `docs/MILESTONE5_CODE_CHANGE_BENCHMARK.md`。

Milestone 6 使用 5 个小型 Unity C# 防御式需求评测真实 Provider。它记录 JSON、契约、安全、质量、补丁可应用性、固定语义证据、延迟与 usage，但不会自动审批或启动 Unity：

```powershell
cd D:\Desktop\agentic-game-rd\services\agent-python
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli run_real_code_evaluation --output ..\..\runtime-artifacts\real-code-evaluation --timeout-seconds 60
```

重新运行本地检查而不调用模型：

```powershell
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli replay_real_code_evaluation --output ..\..\runtime-artifacts\real-code-evaluation
```

环境变量使用根目录 `.env` 中的 `GAMECONFIG_LLM_BASE_URL`、`GAMECONFIG_LLM_API_KEY` 和 `GAMECONFIG_LLM_MODEL`。详见 `docs/MILESTONE6_REAL_CODE_EVALUATION.md`。

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

### 弹幕自动验证测试床

运行 Bullet Hell Windows Build 和固定种子双跑：

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\smoke-bullet-hell.ps1
```

证据保存到 `runtime-artifacts/bullet-hell-smoke/`。Unity 批处理没有拿到 Hub 许可证令牌时，脚本会明确失败；即使 Unity 进程返回 0，只要没有生成 `BulletHellDemo.exe` 就不会误报成功。

离线 20 样本工程回归：

```powershell
cd D:\Desktop\agentic-game-rd\services\agent-python
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli run_bullet_hell_benchmark --output ..\..\runtime-artifacts\bullet-hell-benchmark
```

该 benchmark 使用脚本化故障验证路由、护栏和有限修复，不代表真实 Unity 或真实模型质量。

当前主演示实测中，候选双向螺旋首次未满足固定轨迹受击目标，系统两次降低弹速并自动复测；最终峰值存活子弹 `196/350`、玩家受击 `0/3`、生存 `36/36s`、低分位 FPS 约 `58.8/55`，随后由人工接受。页面刷新后可使用“加载最近验证”恢复该证据。

## 验证

```powershell
.\scripts\test-all.ps1
```

也可以分别运行：

```powershell
.\scripts\test-python.ps1
.\scripts\test-web.ps1
.\scripts\smoke-unity.ps1
.\scripts\smoke-bullet-hell.ps1
.\scripts\verify-repo-clean.ps1
```

## 当前边界

- 不使用 DevQuality 旧 Go 后端、旧前端、PostgreSQL 或 Redis。
- Code Change Agent 只生成候选 Diff，不能读取未授权文件、写主仓库或自动合并。
- 人工 C# Diff 只在审批后的隔离 Unity 副本中应用，系统不自动生成或合并补丁。
- 配置候选只写入 `runtime-artifacts/change_workflows` 和独立 Unity run，不覆盖已提交基线。
- 弹幕候选只写入 `runtime-artifacts/bullet-hell-workflows`；人工“接受”当前只记录决策，不自动覆盖 `configs/bullet-hell/baseline.json`。
- 不公开分发灵梦模型、贴图或本地音频。
- 单次 Unity 前后对比不宣称为统计学 A/B 实验。

详细来源、工具链和迁移结果见 `docs/`。
