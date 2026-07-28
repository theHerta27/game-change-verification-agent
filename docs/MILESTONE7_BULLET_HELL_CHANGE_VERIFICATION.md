# Milestone 7：弹幕变更自动验证闭环

## 1. 这一阶段解决什么问题

这一阶段把项目主线从固定的 Training Sword 配置演示，扩展为一个更接近游戏研发工作的流程：

```text
策划描述弹幕变更
-> Agent 生成候选配置
-> 确定性工具检查结构、引用、数值和性能边界
-> 人工授权隔离测试预算
-> Unity 用同一基线、种子和轨迹运行修改前与修改后
-> 系统比较 telemetry
-> 必要时选择有限修复策略，由确定性工具调参
-> 最多复测三轮
-> 人工接受、要求修订或回滚
```

它的目的不是让大模型直接控制游戏，而是让大模型负责理解目标和提出候选，让可测试的程序负责守边界、运行和出证据。

## 2. 系统由哪些部分组成

### 弹幕配置契约

`configs/bullet-hell/baseline.json` 是已提交的正式测试基线。`gameconfig_agent/bullet_hell.py` 定义独立的 `bullet_hell_contract_version: "1.0"`，包含：

- 场景与运行时长；
- 玩家移动、判定点与自动射击；
- Boss 与阶段；
- `ring`、`aimed_fan`、`spiral`、`petal` 四种 Pattern；
- 最大存活子弹、阶段数和参数安全边界；
- 玩家受击、存活时间、低分位 FPS 等运行目标。

Agent 只生成完整候选 JSON，不修改旧 Training Sword artifact，也不修改 C#、Scene、Prefab 或项目设置。

### Python 工作流

`workflow/bullet_hell_workflow.py` 保存每次工作流的状态和证据。主要状态为：

```text
awaiting_authorization
-> authorized
-> running_baseline
-> running_candidate
-> analyzing
-> repairing
-> evidence_ready | budget_exhausted | blocked | failed
-> accepted | revision_requested | rolled_back
```

一次人工授权最多允许三次候选 Unity 运行。每轮都先重新执行静态校验。修复动作只能从有限集合选择，例如降低单波子弹、增加发射间隔或降低子弹寿命，实际数值由确定性工具计算。

### Unity 测试床

`BulletHellDemo` 是独立的 2.5D XZ 平面场景：

- 正交俯视相机；
- 本地灵梦模型存在时只替换玩家表现，不存在时使用占位角色；
- 手动模式支持 WASD、Shift 低速移动和自动射击；
- 自动模式使用固定种子和固定轨迹；
- 对象池管理子弹；
- 输出总子弹数、峰值存活子弹、玩家受击、阶段结果、FPS 和异常日志。

固定轨迹结果只表示相同条件下的回归证据，不代表所有玩家都能躲避，也不等同于“游戏好玩”。

### Web Console

策划视图默认进入“弹幕变更验证”，提供：

1. 三个固定演示方向与手动需求；
2. Mock / 真实 Provider 和超时设置；
3. 候选变化及静态安全结果；
4. 一次性隔离测试授权；
5. baseline / candidate 指标对比；
6. 自动修复记录；
7. 接受、要求修订和回滚；
8. 原始 JSON、日志和 telemetry 入口。

开发者视图保留 Training Sword、代码审查、Badcase 和离线 benchmark 等调试能力。

## 3. Mock 与真实模型

- **Mock**：通过固定规则理解已支持的弹幕表达，产生可重复候选，适合回归与演示。它不是通用语言理解模型。
- **OpenAI Compatible Provider**：根据 Prompt Contract 返回候选 JSON。输出仍必须经过与 Mock 相同的 Schema、安全规则、人工授权和 Unity 证据。
- **不相关需求**：例如“讲一个笑话”会被能力门判断为不属于弹幕配置变更，不会被硬塞进 Schema。
- **危险需求**：例如极端发射频率和数量会在 Unity 启动前被安全门阻止。
- **信息不足**：无法形成明确变更目标时进入澄清或阻塞状态，不猜测正式配置。

## 4. Before / After 证据

baseline 和 candidate 必须使用相同的：

- Unity Player；
- 随机种子；
- 固定玩家轨迹；
- 运行时长；
- 本机环境。

核心比较包括：

| 证据 | 用途 |
|---|---|
| `total_bullets_spawned` | 判断总发射规模 |
| `peak_alive_bullets` | 判断对象池和视觉密度峰值 |
| `player_hits` | 判断固定轨迹受击变化 |
| `player_survival_seconds` | 判断固定轨迹能否存活 |
| `phase_results` | 判断所有阶段是否正常运行 |
| `average_fps` | 观察总体性能 |
| `low_percentile_fps` | 排除部分瞬时抖动后观察低帧表现 |
| `minimum_fps` | 保留原始最低帧证据，但不单独下硬结论 |
| `exception_log_count` | 检查运行时错误 |

## 5. API

```text
GET  /api/bullet-hell/capabilities
POST /api/bullet-hell/workflows
GET  /api/bullet-hell/workflows/{workflow_id}
GET  /api/bullet-hell/workflows/latest
POST /api/bullet-hell/workflows/{workflow_id}/authorize
POST /api/bullet-hell/workflows/{workflow_id}/run
POST /api/bullet-hell/workflows/{workflow_id}/play
POST /api/bullet-hell/workflows/{workflow_id}/decision
GET  /api/bullet-hell/workflows/{workflow_id}/artifacts/{name}
GET  /api/bullet-hell/benchmark/dataset
POST /api/bullet-hell/benchmark
```

所有工作流证据保存在 Git 忽略的 `runtime-artifacts/bullet-hell-workflows/`，不会覆盖 `configs/bullet-hell/baseline.json`。

## 6. 本地运行

启动后端和前端：

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\start-backend.ps1
.\scripts\start-web.ps1
```

运行离线工程回归：

```powershell
cd D:\Desktop\agentic-game-rd\services\agent-python
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli run_bullet_hell_benchmark --output ..\..\runtime-artifacts\bullet-hell-benchmark
```

构建 Bullet Hell Player，并用同一配置和种子自动运行两次：

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\smoke-bullet-hell.ps1
```

若 Unity Hub 显示有许可证但批处理日志出现 `Access token is unavailable` 或 `LicensingClient has failed validation`，表示 Editor 批处理进程没有拿到 Hub 登录令牌。脚本会明确失败，不会把 Unity 返回码 0 但未生成 Player 误报为成功。

## 7. 三个主演示案例

1. **双向螺旋主案例**：第二阶段改为更密的双向螺旋，同时要求存活子弹和 FPS 不越界。
2. **高密度修复观察**：首次候选造成指标不通过，系统选择有限策略调参并复测。
3. **危险需求拦截**：极端发射频率在 Unity 启动前被安全门拒绝。

## 8. 离线 Benchmark 的准确含义

`evals/bullet_hell_benchmark_v1.json` 有 20 个固定样本，用脚本化输入和脚本化运行故障检查：

- 需求路由；
- Schema；
- 安全门；
- 有限修复；
- 预算和失败路由；
- 错误接受。

它是工程回归，不是实时 Unity 测试，也不是大模型质量评测。报告中的高通过率只能说明预设规则按预期执行。

## 9. 当前边界和后续方向

- 正式基线只读，接受动作当前只记录人工结论，不自动覆盖仓库。
- 第一版不允许 Agent 修改 C#。
- 自动轨迹不能替代真人试玩，应将自动回归和人工体验评审并列使用。
- Unity Test Framework 尚未正式覆盖全部运行模块。
- 后续应先积累真实策划需求、人工评价和 Unity telemetry，再调整规则与 Prompt，而不是继续堆叠 Agent 名称。

## 10. Milestone 7 最终验收

- Python：151 项测试通过。
- Web：production build 通过。
- Unity：Bullet Hell C# 编译和 Windows Build 通过。
- 固定步长双跑：总子弹 `592`、峰值存活子弹 `66`、玩家受击 `2`，三个阶段的 Pattern、发射数、受击数和峰值逐项一致。
- Training Sword：旧固定种子双跑重复率 100%。
- Web 主案例：baseline/candidate 和两轮自动修复全部由真实 Unity Player 执行，最终进入 `evidence_ready` 并完成人工接受。
- 页面：中文/英文切换、最近证据恢复、指标格式化、artifact 链接和时间线通过浏览器验收。
