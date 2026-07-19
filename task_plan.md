# Agentic Game R&D Lab 项目计划

## 项目目标

构建一个由统一 Python Agent 运行时、Unity 可控战斗测试床和 React 控制台组成的本地游戏研发 Agent 实验室。系统以配置变更、质量审查、确定性自动试玩和 telemetry 证据形成可回放闭环。

## High-Level Roadmap

| Milestone | 目标 | 状态 |
|---|---|---|
| Milestone 0 | 单仓库迁移与集成 | complete |
| Milestone 1 | 灰盒自动战斗测试床 | complete |
| Milestone 2 | 灵梦角色表现层 | complete |
| Milestone 3A | 配置变更闭环 | complete |
| Milestone 3B | 人工 C# Diff 质量闭环 | complete |
| Milestone 4 | 受控 Code Change Agent | complete |

## Milestone 3A：配置变更闭环

### 目标

- [x] 将策划需求转换为可审查的配置变更提案，而不是直接覆盖运行配置。
- [x] 使用 Change Feasibility Gate 拒绝超出 Starter Trial 能力清单的需求，并要求不完整需求补充信息。
- [x] 生成逐字段 Config Diff、需求一致性审查、测试建议和确定性静态校验结果。
- [x] 增加人工审批门禁；未经批准的候选配置不得进入 Unity 运行验证。
- [x] 将批准后的候选配置复制到独立 runtime run，完成 Unity 编译/试玩、telemetry 评测和证据审查。
- [x] 支持接受、要求修订和回滚三种最终决策，并保留完整时间线与不可变快照。
- [x] 在 Web Console 中以策划可理解的步骤展示提案、变化、审批、试玩和结论。
- [x] 完成 Python、Web、Unity 和仓库清洁回归。

### 状态机

`proposed -> approved -> runtime_prepared -> runtime_launched -> evidence_ready -> accepted | revision_requested | rolled_back`

`needs_clarification`、`rejected` 和 `failed` 为不可进入 Unity 的终止或人工处理状态。

### 边界

- 不新增游戏玩法、Code Change Agent、Go 服务、数据库、微服务或自动代码修改。
- 不重构已有 GameConfig、Quality Review 和 RuntimeRun 主流程；统一 workflow 只负责编排和持久化状态。
- Mock 仍是确定性 Training Sword 基线；需求中的受支持约束由确定性映射器落到候选配置，不伪装成自由生成模型。
- 不覆盖 `game-unity/Assets/StreamingAssets/game_config.json`；候选配置只进入忽略目录中的独立运行快照。
- 所有现有 API、artifact 和 Unity runtime contract 字段保持兼容；Milestone 3A 使用新增命名空间。

### 当前阶段

`Milestone 3A complete。下一阶段为 Milestone 3B 人工 C# Diff 质量闭环。`

## Milestone 3B：人工 C# Diff 质量闭环

### 目标

- [x] 接收开发者人工编写的 Unity C# unified diff，不由 Agent 自动生成或直接修改主仓库。
- [x] 使用 Patch Safety Gate 限制路径、文件类型、变更规模和高风险 API，并输出结构化拒绝原因。
- [x] 扩展 Quality Review Agent 的 C# 静态规则，生成 Finding 与 Test Suggestion。
- [x] 增加人工批准门禁；未经批准的补丁不得创建隔离验证工作区。
- [x] 在 `runtime-artifacts/code-workflows/` 复制最小 Unity 源工程并精确应用补丁，保证已提交基线不变。
- [x] 对隔离工作区执行 Unity C# 编译/Windows Build、编辑器确定性 smoke、固定种子自动试玩和 telemetry 评测。
- [x] 支持接受、要求修订和回滚三种最终决策，并保存补丁、审查、日志和运行证据。
- [x] 在 Web Console 开发者视图提供补丁审查与验证流程，策划视图不暴露代码细节。
- [x] 完成 Python、Web、Unity 和仓库清洁回归。

### 状态机

`proposed -> approved -> workspace_prepared -> validation_running -> evidence_ready -> accepted | revision_requested | rolled_back`

`rejected` 和 `failed` 不得进入 Unity 验证；验证失败会保留日志和结构化失败证据，不修改主仓库。

### 边界

- 不实现 Code Change Agent，不让 LLM 生成或自动应用补丁，不新增游戏玩法。
- 仅允许修改 `game-unity/Assets/**/*.cs` 中已存在的文件；禁止新增、删除、重命名、二进制补丁、路径穿越和超限变更。
- 主仓库和已提交 Unity 基线始终只读；所有候选修改只进入 Git 忽略的隔离工作区。
- 当前 Unity 工程没有 Unity Test Framework 套件。本阶段如实记录“编辑器确定性 smoke + 编译构建 + Player 自动试玩”，不虚构 EditMode/PlayMode 测试结果。
- 保持现有 API、artifact 和 Unity runtime contract 兼容；Milestone 3B 使用新增命名空间。

### 当前阶段

`Milestone 3B complete。Post-MVP Code Change Agent 保持 deferred，需单独确认后才进入。`

## Milestone 4：受控 Code Change Agent

### 目标

- [x] 接收开发者代码变更需求和显式目标文件，不让模型自行浏览整个仓库。
- [x] 新增 Code Change Feasibility Gate；Mock 只支持确定性的运行参数空值保护 recipe。
- [x] 新增 Code Change Generator Prompt Contract，真实 Provider 只能返回结构化 JSON 和 unified diff。
- [x] 对 JSON 解析、输出契约、目标文件越界和 Patch Safety Gate 失败记录 badcase。
- [x] 生成候选 Diff 后复用 Milestone 3B 的质量审查、人工审批、隔离应用和 Unity 验证。
- [x] Web Console 开发者视图展示“需求 -> Agent 候选 Diff -> 受控审查闭环”，策划视图保持不变。
- [x] 完成 Python、Web、Unity、浏览器和仓库清洁回归。

### 状态与边界

- Agent 只生成候选补丁；`patch_applied_to_repository` 仍始终为 `false`。
- 默认 Provider 为 deterministic Mock；Mock 固定 recipe 必须明确标注，不能宣称理解任意 C# 需求。
- 真实 Provider 只能读取用户显式选择的最多 3 个 `game-unity/Assets/Scripts/*.cs` 文件。
- 不新增玩法，不开放 `Assets/Editor`、第三方本地资产、网络、进程、原生调用、文件删除或主仓库写权限。
- 生成层不复制审批、Validator 或 Unity Tool；所有候选必须进入既有 `/api/code-workflows` 闭环。

### 当前阶段

`Milestone 4 complete。下一阶段应先建设代码变更 benchmark 与失败分类，不扩大 Agent 写权限。`

## Milestone 0：单仓库迁移与集成

### 目标

- [x] 冻结两个非 Git 源项目的 SHA256 来源清单。
- [x] 迁移 GameConfig Python、React、Unity 和必要演示证据。
- [x] 迁移 DevQuality Python 质量审查核心，不导入 Go、旧前端和数据库部署。
- [x] 建立唯一 Python 运行时和统一 FastAPI 入口。
- [x] 建立根 `AGENTS.md`、子系统规范、统一脚本和中文文档。
- [x] 本地归档灵梦原始资产，不提交第三方模型。
- [x] 完成 Python、前端、Unity 和仓库清洁验收。
- [x] 初始化 Git 并创建可复现迁移基线提交。

### 边界

- 不修改 `D:\Desktop\GameConfig-Agent` 和 `D:\Desktop\DevQuality-Agent`。
- 不新增玩法、Boss、Roguelite 构筑或 Code Change Agent。
- 不引入 Go 服务、数据库、Redis、微服务或 Docker。
- 不修改现有 GameConfig API 与 artifact 字段。
- 不把本地模型、贴图、音频、密钥和运行产物提交 Git。

### 当前阶段

`Milestone 0 complete。`

## Milestone 1：灰盒自动战斗测试床

### 目标

- [x] 建立版本化测试画像，固定场景 ID、随机种子、运行模式和验收指标。
- [x] 将 Unity 场地固化为圆形灰盒竞技场，不引入新玩法或美术依赖。
- [x] 固定自动运行帧率和随机种子，使同一配置可重复执行。
- [x] 保留基础敌人、技能和三波战斗，并输出分波次 telemetry。
- [x] 连续运行同一固定种子两次，比较稳定计数并检查时间容差。
- [x] 生成机器可读评测结果和中文 Markdown 证据报告。
- [x] 完成 Python、Web、Unity、API 和仓库清洁回归。

### 边界

- 不新增 Boss、构筑、掉落、角色养成或其他玩法系统。
- 不处理灵梦模型、动画、裙摆物理、表情和技能特效。
- 不重构 GameConfig / DevQuality 既有业务流程，不实现统一 Agent 编排。
- 不修改既有 API、artifact 和 Unity runtime contract 字段名；telemetry 仅允许向后兼容地增加证据字段。
- 固定种子用于保证测试环境可复现，不把一次自动试玩解释为真实玩家体验统计。

### 验收标准

- 相同 contract 与相同 seed 的两次自动运行均完成 3 波并击败 5 个敌人。
- `status`、`scenario_id`、`random_seed`、波次数、击败数、攻击/技能计数和伤害计数稳定一致。
- 通关时间允许小幅帧调度误差，默认差值不超过测试画像定义的容差。
- 每个完成波次均包含生成数、击败数、攻击/技能次数、伤害和耗时证据。
- `runtime-artifacts/unity-smoke/` 生成两份 telemetry、评测 JSON 和中文报告，但不进入 Git。

### 当前阶段

`Milestone 1 complete；下一阶段为 Milestone 2 灵梦角色表现层。`

## Milestone 2：灵梦角色表现层

### 目标

- [x] 锁定 Blender `4.5.11 LTS` 与 MMD Tools `v4.5.10`，记录来源、commit 和 SHA256。
- [x] 建立免安装、可重复执行的本地工具链，不要求用户手工配置 Blender 插件。
- [x] 验证 `R_spring.pmx -> Blender -> FBX -> Unity` 完整通路。
- [x] 在 Git 忽略目录生成本地 Reimu Prefab，已提交 Scene/Prefab 不直接引用其 GUID。
- [x] 保持 `CharacterViewResolver` 的本地模型替换与 Placeholder 回退路径。
- [x] 提供基础待机/移动表现、御札或阴阳玉占位表现和命中反馈，不改变战斗数值逻辑。
- [x] 无本地模型时自动战斗仍能运行；有本地模型时完成 Unity 导入与构建检查。
- [x] 更新中文工具链、资产边界和复现文档。

### 边界

- 第三方 PMX、贴图、FBX、Prefab、动画和 Blender 工具链均不提交 Git。
- 本阶段只做角色表现层，不新增敌人、技能数值、Boss、构筑、掉落或养成玩法。
- 不处理复杂裙摆物理、MMD 刚体还原、高级表情和完整动画状态机。
- 模型仅用于个人本地学习、测试和面试演示；不公开分发。
- MMD Tools 采用官方当前稳定版 `v4.5.10`；原规划中的 `v4.5.11` 经核对不存在，不虚构版本。

### 验收标准

- Blender 可通过脚本无界面导入 `R_spring.pmx` 并导出非空 FBX。
- 转换报告记录 Blender/MMD Tools 版本、模型网格/骨骼/材质数量和文件哈希。
- Unity 自动创建本地 Reimu Prefab，但 Git 跟踪文件不包含其 GUID。
- Unity 构建同时验证 Placeholder 回退和本地模型替换分支。
- 固定种子灰盒自动战斗与 Milestone 1 可重复性指标不回退。

### 当前阶段

`Milestone 2 complete；下一阶段为 Milestone 3A 配置变更闭环。`

## 遇到的错误

| 日期 | 错误 | 尝试次数 | 处理 |
|---|---|---:|---|
| 2026-07-18 | 合并两个测试目录时，源目录中的 `__pycache__` 发生同名冲突 | 1 | 清理新仓库缓存，改为按相对路径只迁移测试源文件和 fixtures |
| 2026-07-18 | 来源清单脚本中的反斜杠路径表达式触发 PowerShell ParserError | 1 | 改用显式字符码 92/47 分两步标准化路径 |
| 2026-07-18 | PowerShell 中的 `python` 指向 Hermes venv，缺少 pytest | 1 | 检测到 `D:\anaconda\python.exe` 与 pytest，统一脚本增加 Python 解释器解析 |
| 2026-07-18 | 沙箱网络限制导致 pip 无法下载 `setuptools` 构建依赖 | 1 | 保留仓库 `.venv`，申请受控网络权限后重跑 bootstrap |
| 2026-07-18 | setuptools 拒绝自动发现统一运行时中的多个顶层包 | 1 | 在 `pyproject.toml` 显式包含四个运行包并排除 tests/examples |
| 2026-07-18 | Unity batchmode 返回 198，Licensing Client 无 access token/entitlement | 1 | 增强错误分类，并在沙箱外复测以区分进程隔离与本机 Hub 授权问题 |
| 2026-07-18 | Unity 双跑中 damage_taken 为 280 / 292，固定 seed 仍未保证行为稳定 | 1 | 自动模式从渲染帧 Update 迁移到固定步长 FixedUpdate |
| 2026-07-18 | Unity 写完 telemetry 后退出偶发 0xC0000005 | 2 | 固定 D3D11，并把 Application.Quit 延迟到待销毁对象清理后的下一帧 |
| 2026-07-18 | 清洁脚本中的 git ls-files 被 dubious ownership 拒绝但未使脚本失败 | 1 | 使用命令级 safe.directory 并显式检查 Git 退出码 |
| 2026-07-18 | MMD Tools 复制到 Blender 安装目录后无法被 4.5 搜索 | 1 | 使用项目级 BLENDER_USER_SCRIPTS/addons 目录 |
| 2026-07-18 | git ls-remote 查询 MMD Tools tag 超时 | 1 | 改用 GitHub REST API，后续优先复用本地 lock |
| 2026-07-18 | GitHub REST API 重跑触发匿名限额 | 1 | 安装脚本先读取本地 toolchain-lock，首次安装才访问 API |
| 2026-07-18 | Unity FBX 材质可用但全部未绑定主贴图 | 1 | 根据 Blender 材质报告生成 12 个本地 Standard 材质并 remap |
| 2026-07-18 | 图形 Player 完成 telemetry 后偶发 0xC0000005 | 2 | 逻辑双跑改为 -batchmode -nographics，截图独立使用 D3D11 |
