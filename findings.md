# Findings

## 2026-07-27 Milestone 7

- 现有 Unity Training Sword 运行时集中在单个 `RuntimeDemoBootstrap`，无法仅通过替换 JSON 迁移为弹幕；最小风险方案是独立 Bullet Hell contract、场景和运行时模块，旧路径只增加模式隔离保护。
- 现有 `ChangeWorkflowService` 已具备文件状态机、候选快照、人工审批、隔离运行和最终决策，可复用其工程模式，但弹幕需要 baseline/candidate 双跑和多轮自动修复，因此使用独立 `/api/bullet-hell` 工作流。
- 固定轨迹只能形成相同轨迹下的可重复碰撞与生存证据，不能证明一般意义上的“可躲避”或“好玩”。
- 首次 Bullet Hell Unity batch build 未生成 EXE。日志显示 `LicensingClient has failed validation` 与 `Access token is unavailable`，进程却返回 0；该问题属于本机 Hub/batchmode 许可证令牌，不是已确认的 C# 编译错误。后续验收必须同时检查 EXE 是否存在，不能只相信退出码。
- 后台工作流初版直接覆盖 JSON，API 轮询可能在文件截断和写入之间读到空内容；已改为同目录临时文件写完后原子替换。

## 2026-07-18 来源核对

- `GameConfig-Agent` 与 `DevQuality-Agent` 均无 `.git`，不能记录源 commit；使用逐文件 SHA256、源路径和迁移时间建立可复现来源清单。
- GameConfig 的有效源由 Python 包、测试、前端源码、Unity `Assets/Packages/ProjectSettings` 和少量演示产物组成；其 `node_modules`、Unity `Library/Builds` 占据绝大部分体积，不应迁移。
- DevQuality 当前需要的领域能力全部位于 `agent_service` Python 目录；Go 后端、旧前端、PostgreSQL/Redis 和设计系统不进入新仓库。
- GameConfig 测试有少量旧 `outputs/phase0` 路径依赖，迁移时改为明确的测试 fixture，运行时数据统一写入 `runtime-artifacts`。
- Unity 版本为 `6000.3.19f1`。
- 灵梦资源包包含 `R_spring.pmx`、`R_winter.pmx`、武器 PMX 和贴图；原始说明允许自制游戏和渲染使用，但企业使用需联系权利方，因此只做本地资产，不公开分发。
- 本机未检测到 Blender；模型转换留待 Milestone 2，计划锁定 Blender 4.5 LTS 与 MMD Tools `v4.5.11`。

## 架构决策

- 两个旧目录作为外部只读来源，不在新仓库复制 `components` 或 `legacy-imports`。
- `services/agent-python` 是唯一 Python 运行时；Milestone 0 保留 `gameconfig_agent` 与 `agent_service` 包名以降低迁移风险。
- 统一 FastAPI 保留 GameConfig 现有路由，并以 `/api/quality/*` 暴露 DevQuality Python 能力。
- `workflow` 是确定性编排层，不是额外 Agent。
- 本地角色只能通过运行时路径解析，已提交 Scene/Prefab 不得引用被忽略资产的 GUID。

## 验收发现

- Unity batchmode 在沙箱内无法取得 Hub access token，返回 198；同一脚本在受控沙箱外运行后完成编译、构建和自动战斗，说明阻塞来自 Licensing Client 的进程隔离，不是项目许可证或 C# 错误。
- Unity 自动战斗结果为 3 波、5 击败、27 次普攻、2 次技能、15.1531 秒；它是迁移 smoke 证据，不代表后续平衡目标已经达成。
- 统一 Python 测试共 91 项；两个源能力可在同一解释器和 FastAPI 应用中共存，不需要两个服务或 Go 控制面。
- `pip install -e` 与 `tsc -b` 会生成 `*.egg-info`、`vite.config.js` 和 `vite.config.d.ts`；它们属于可再生构建文件，已纳入忽略与清洁检查。

## 2026-07-18 Milestone 1

- 固定随机种子本身不足以保证 Unity 自动战斗可重复；原实现把攻击和敌人行为放在渲染帧 `Update()`，两次运行的 `damage_taken` 分别为 280 和 292。
- 自动模式迁移到固定步长 `FixedUpdate()` 后，稳定字段完全一致；手动输入仍保留在 `Update()`，两条路径职责明确。
- Unity Player 在写完 telemetry 后立即从最后一个固定帧调用 `Application.Quit()`，偶发 `0xC0000005`；延迟到帧末和下一帧退出后消失。D3D11 作为 Windows 自动化的固定图形后端保留。
- 测试画像与 runtime contract 必须分离：前者定义验证条件，后者定义被测游戏配置。
- 固定种子双跑能证明回归稳定性，不能证明真实玩家体验、趣味性或统计学平衡。

## 2026-07-18 Milestone 2

- 官方当前版本是 Blender `4.5.11 LTS` 与 MMD Tools `v4.5.10`；原计划把两个补丁版本都写成 4.5.11，插件版本不存在。
- Blender 4.5 portable 不会自动扫描安装目录下的旧式 `scripts/addons`；通过项目级 `BLENDER_USER_SCRIPTS` 暴露 MMD Tools 后可稳定后台加载。
- GitHub tag archive 下载成功，但 `git ls-remote` 在本机网络超时；改用官方 REST API锁定完整 commit，并在后续运行优先复用本地 lock，避免匿名 API 限额。
- FBX 嵌入贴图进入 Unity 后材质 Shader 可用，但主贴图未自动绑定；根据 Blender 报告中的材质语义显式生成和 remap 本地 Unity 材质后，12/12 贴图成功绑定。
- 原高位镜头能够展示场地但角色过小；降低镜头后角色与两名敌人同时可辨认，固定种子 telemetry 未发生回退。
- MMD 物理存在稳定性和迁移成本，本阶段明确不导入；表现层只做可替换角色、轻量摆动和命中反馈。
- Windows Development Player 在完成 telemetry 后偶发于图形设备清理阶段返回 `0xC0000005`，即使延迟退出也不能完全消除；将逻辑双跑改为 `-batchmode -nographics` 后退出稳定，视觉截图继续独立使用 D3D11。

## 2026-07-19 Milestone 3A

- 当前 MockLLM 会忽略输入细节并固定生成 Training Sword 草稿；它适合回归，不足以证明需求驱动的配置变更。Milestone 3A 保留该基线，同时用白名单约束映射器显式修改支持字段。
- RuntimeRunService 已经具备隔离运行目录和精确 config hash，适合作为批准后执行层；缺失的是提案、审批、最终决策和跨阶段审计状态。
- DevQuality 的现有 Review Agent 面向代码 Diff，不能直接拿配置 JSON Diff 冒充代码审查。配置质量审查应在统一 workflow 中形成独立结构化契约，代码 Diff 审查保留给 Milestone 3B。
- 隔离执行意味着“回滚”不需要覆盖生产文件：丢弃候选运行并把工作流决策指向基线快照即可，风险小且证据可追溯。
- Windows PowerShell 通过 `npm run dev -- --host ... --port ...` 传参时，本机 npm/Vite 组合会把 host 和 port 变成位置参数并回退到 5173；启动脚本应直接调用 `node_modules/.bin/vite.cmd`。
- 只修改前端端口不能解决旧后端占用问题；Vite `/api` 代理也必须成对指向新后端端口。`start-web.ps1 -BackendPort` 现已显式完成该绑定。
- Unity Hub 显示 Personal 许可证并不保证受限沙箱进程可以读取 Licensing Client entitlement；同一 smoke 在沙箱外通过，说明项目与许可证有效，失败来自进程隔离。
- 完整闭环实测证明“静态校验通过”不等于策划目标通过：本次候选结构合法，但自动试玩约 16.63s，未达到 60–90s，最终被人工标记为需要修订。这正是 runtime evidence 的价值。

## 2026-07-19 Milestone 3B

- DevQuality 原静态规则只覆盖 Go/Python；C# Diff 可以复用 Parser、Finding、Test Suggestion 和 Validator 契约，但必须补充 Unity 特有的每帧 I/O、对象分配和固定种子风险规则。
- 人工补丁与自动代码生成必须分开：本阶段的 Agent 只负责审查，补丁作者、审批人和最终合并者仍是人。
- Unified diff 仅解析成功不代表可安全应用；必须同时校验路径、文件生命周期、变更规模、危险 API、审批后 SHA256 和 hunk 上下文。
- 隔离工作区只复制 Unity 源目录，不复制缓存和本地第三方角色；这既缩小输入面，也证明没有灵梦本地资源时 Placeholder 回退仍成立。
- Unity Test Framework 尚未接入，现有可靠证据是 C# 编译/Windows Build、编辑器确定性 smoke、Player 固定种子双跑和 telemetry；文档与 UI 不应将其称为 EditMode/PlayMode 测试。
- 后台 PowerShell 在短生命周期父进程中可能退出且不留结果；长运行 FastAPI 能正常托管，但状态机仍需检测“进程已退出且无结果”并生成 `ValidationProcessError`。
- Windows PowerShell 5 的 `Set-Content -Encoding UTF8` 会写 BOM，Python 工作流必须用 `utf-8-sig` 读取外部 JSON。
- 沙箱内 Unity 仍无法获得 Hub entitlement，沙箱外同一隔离工程通过，说明许可证与项目有效；脚本需要把该情况归类为许可证令牌问题。
- 真实隔离 smoke 的固定种子重复性为 100%，运行目标通过率为 60%。前者证明代码回归稳定，后者继续暴露 Training Sword 当前平衡目标偏差，两者不能混为一个指标。

## 2026-07-19 Milestone 4

- Code Change Agent 不需要复制 Milestone 3B 状态机；最小正确实现是在人工 Diff 闭环前增加“受限上下文 -> 候选 Diff”生成层。
- 浏览器实际闭环证明候选生成层可以复用同一套确定性安全门、质量审查和人工门禁；生成来源通过 `source=code_change_agent` 单独标识，避免把 Agent 输出误认为人工补丁。
- 隔离补丁 Unity 验证通过且主仓库源文件无 diff，说明当前“模型只提议、隔离副本执行”的权限边界有效。
- 当前真实 Provider 的最大缺口不是更多文件权限，而是缺少带预期补丁、拒绝样本和 Unity 结果的代码变更 benchmark。下一步应先量化生成质量和失败类型。

## 2026-07-19 Milestone 5

- 代码变更评测必须区分“护栏正确率”和“真实模型代码质量”。脚本化 Provider 可以稳定验证失败路由，但不能替代真实模型评测。
- 固定样本需要同时检查 status、stage 和 badcase；只统计“请求没有崩溃”会掩盖错误放行或错误分类。
- 越权风险既可能出现在模型声明的 `target_files`，也可能只出现在实际 Diff，因此声明校验和解析后路径校验都不可省略。
- CLI 顶层导入 workflow benchmark 会与既有 `runtime_runs -> cli` 形成循环依赖；延迟到具体命令分支导入可保持旧启动路径不变。
- 首轮 12 样本结果为 100% 预期匹配、100% badcase 捕获、100% 越权阻断、0 错误放行/拒绝，且运行前后 C# 源文件哈希一致。
- 浏览器验收发现纯数值判断会把计数 0 错误格式化为 0%，同时中文布尔值显示为 Yes；已改为按指标 key 区分比率/计数并跟随界面语言。
- `failure_stage_distribution` 不能混入成功候选的 `quality_workflow`；最终同时提供全量 `decision_stage_distribution` 与仅非 generated 样本的失败阶段分布。

## 2026-07-19 Milestone 6

- 真实代码评测不能复用 scripted fixture 的 expectation match 作为主指标；真实输出需要逐层记录 Provider、JSON、契约、安全、质量、可应用性和需求语义。
- 生成补丁通过安全门仍可能没有满足需求，因此增加基于补丁应用后源文件的固定语义断言；该断言仍不是编译或 Unity 运行证明。
- Provider 返回内容后即使 JSON 解析失败，也应保留 latency/usage；已将 `provider_evidence` 写入 Code Change Agent badcase。
- 当前新仓库没有 `.env` 或进程环境变量。无密钥 smoke 正确生成 `run_status=blocked`、provider configuration badcase 和四份报告，且没有模型调用。
- 旧 `GameConfig-Agent` 根目录存在 `.env`，但本阶段未读取或复制密钥，等待用户明确允许迁移。
- 自动检索整个仓库会扩大提示词、权限和错误归因范围。本阶段由开发者显式选择最多 3 个运行时 C# 文件，更适合作为可解释的最小权限原型。
- 生成 Provider 与质量审查 Provider 应分离：真实模型负责提出候选，确定性规则和 Mock Review 负责稳定门禁，避免一次模型调用同时充当作者和批准者。
- Mock 只有固定 recipe 时必须返回 `needs_clarification` 处理其他需求；用固定补丁响应任意需求会制造虚假的 Agent 能力。
- 真实模型即使返回合法 JSON，也可能声明或实际修改未授权文件；必须同时检查 `target_files` 字段和 unified diff 中的真实路径。
- 代码生成失败不是接口异常：JSON parse、Prompt Contract、目标范围和 Patch Safety Gate 失败都应形成含原始输出的 badcase。
- 当前允许列表不包含 `Assets/Editor`，是为了防止候选补丁改变构建/校验器本身；被测运行时代码和测试工具必须保持权限分离。

## 2026-07-28 Milestone 7

- 弹幕配置必须使用独立 contract，不能把 Training Sword 的武器、升级和奖励字段继续扩张成通用游戏 Schema。
- Mock 的价值是稳定复现候选与失败路径，不是模拟真实模型的自由理解能力；真实 Provider 也只能提出候选，不能跳过同一静态校验和 Unity 证据。
- baseline/candidate 的公平比较依赖相同 Player、配置外环境、随机种子、固定轨迹和时长。固定轨迹受击结果不能扩大解释为所有玩家体验。
- 自动修复应把“策略选择”和“数值计算”分开：Agent 只能选有限动作，确定性工具计算新值并重新校验。
- 离线脚本化 telemetry 适合验证状态机、预算和失败路由，但不能作为实时 Unity 性能、玩家体验或真实模型生成质量证据。
- Unity `-batchmode` 可能返回进程结果但没有完成构建；验收脚本必须同时检查许可证日志和目标 EXE 是否存在。
- 当前本机失败发生在 Unity 项目加载和 C# 编译之前：Licensing Client signature validation 后没有获得 access token/entitlement，因此不能由该日志推断弹幕 C# 成功或失败。
- 策划页面必须直接提供 Provider 和超时控件；只在开发者侧边栏设置会让主流程看起来不可控。
- 后端版本标识必须跟随当前演示主线更新，否则即使功能已上线，页头仍会误导为旧 Milestone。
- 新场景 Builder 不应让 `BuildPlayer` 复用全局 `EditorBuildSettings.scenes`，否则会把旧 Training Sword 场景一起打入弹幕 Player，或为了弹幕构建覆盖旧场景；应在构建调用中显式传入目标场景，同时让编辑器 Build Settings 保留两个入口。
- Unity Player 退出码 1 不一定代表基础设施崩溃；在本项目中它也表示自动轨迹未能存活。只要 telemetry 完整且状态为 `failed/completed`，就应交给 Evaluator，而不是提前中止修复闭环。
- 固定 seed 不能修复基于 `Update()` 的时间步波动。自动模式的弹幕、碰撞、轨迹和攻击必须在固定 60Hz 步长推进；FPS 采集则保持独立，避免把模拟帧率伪装成机器性能。
- 文件持久化工作流如果没有“最近一次”读取入口，浏览器刷新就会让演示证据看似消失；只读 latest API 足以解决本地单用户 demo，不需要引入数据库。

## 2026-07-19 Milestone 6

- 首次真实代码评测使用 `deepseek-v4-flash` 运行 5 个固定防御式 C# 样本。Provider 调用、JSON 解析、生成契约、安全门、目标范围和质量审查均为 100%。
- 5 个样本的关键代码意图均能在“基线源码 + Diff”中找到，因此语义意图命中率为 100%；只有 3 个补丁能被严格应用，所以应用后语义通过率和候选就绪率均为 60%。
- 两个失败样本不是需求理解失败，而是 unified diff hunk 行号/上下文与真实源文件不一致。严格应用器正确拒绝了候选，badcase 阶段均为 `patch_apply`。
- “模型写出了正确代码片段”和“补丁可以安全应用”必须分开计量。后续应考虑结构化编辑或由确定性工具生成 diff，不能通过放宽上下文校验换取表面成功率。
- 真实评测总延迟为 141,578 ms，Provider 报告总 usage 为 19,842 tokens；这些数据来自首次真实调用，后续页面刷新和 replay 不再次调用模型。
- CLI 文档和 Web API 曾使用不同的默认产物目录（连字符与下划线），导致页面读到旧 blocked 报告；统一为 `runtime-artifacts/real-code-evaluation` 后，页面能正确加载最近一次真实结果。
- 仓库清洁脚本原先把任何存在的 `.env` 都判为“未忽略”，没有实际调用 Git 检查规则；改为逐文件执行 `git check-ignore` 后，既能允许被忽略的本地配置，也会继续拒绝真正未忽略的密钥文件。

## 2026-07-28 Milestone 7 UX

- 步骤圆圈裁剪来自横向滚动容器：圆圈相对步骤条向上偏移 13px，但容器顶部没有安全内边距。为滚动区域预留 16px 顶部空间后，1～6 在桌面、移动端和缩放条件下均完整位于容器内部。
- 新手模式属于展示层，不应改变 `baseline/candidate`、workflow 状态或 artifact 字段；页面只把术语映射为“修改前/修改后”，专业模式继续显示原术语。
- 模式和引导状态适合用浏览器本地偏好保存：首次访问默认新手，引导跳过或切换专业模式后不再强制播放；设置入口只在用户主动操作时重开引导。
- 现有后端 `/play` 只允许特定状态下启动 Candidate，且浏览器不能直接启动任意本地 EXE。在“不改后端”的约束下，修改前/修改后入口必须分别生成精确的本地快照启动命令，不能把 Baseline 按钮伪装成 Candidate 启动。
- 最近一次已接受工作流不允许再次调用现有 `/play`，但其 `baseline_config.json` 和 `candidate_config.json` 快照仍可只读访问；命令式入口因此也适用于已完成演示。

## 2026-07-28 Milestone 7 Visual

- 手动试玩的输入轨迹不可复现，只能回答“主观玩起来怎样”；严格视觉比较必须与 telemetry 一样固定 seed、轨迹、时长、相机和采样时间。
- Unity 运行时原有单张截图钩子，但自动验证使用 `-nographics`，因此不能直接产生可展示画面。独立视觉证据运行保留图形设备，不改变原 telemetry 双跑和三轮修复预算。
- 10/20/30 秒对应当前基线的 phase_1/phase_2/phase_3；两侧在相同时间点记录相同阶段，说明画面比较没有混入不同阶段或不同观察时刻。
- 第 20 秒真实截图中，Baseline 存活子弹约 52，Candidate 约 172；玩家位置、Boss 49% 血量、相机和阶段一致，双向螺旋与更高密度可以直接辨认。
- 视觉运行读取工作流最终 `candidate_config.json`，不会重新调用模型、重新修复或写回正式 baseline；配置 SHA256 随视觉证据一起记录。
- 受限启动接口只接收 `baseline|candidate` 枚举，并在服务端选择固定 EXE 与工作流快照。路径分隔符请求在路由层 404，其他未知 variant 在服务层 409，不能执行任意程序或路径。
- 视频同步不是当前可靠性的必要前提。三组同条件定点截图已经能回答“相同时间和镜头下改了什么”，先稳定截图链比引入编码器、视频同步和更大的平台差异更务实。

## 2026-07-31 Milestone 8 审计

- 当前仓库目录已从 `agentic-game-rd` 改名为 `game-change-verification-agent`；本轮只以该整合仓库为目标。
- `main` 工作树包含 11 个未提交的 Milestone 7 Visual 文件，约 1353 行新增。不能把它们误认为干净提交基线，也不能在不确认的情况下丢弃。
- Python 基线为 `153 passed`，Web production build 为 `1585 modules transformed`；两者本轮真实通过。
- Unity Bullet Hell 本轮真实重建被 Hub access token/entitlement 阻断。脚本已删除旧 Player 并拒绝把旧 EXE 当作新 Build，因此当前 Player 不存在；历史 Telemetry 仍只能作为 2026-07-28 的既有证据。
- Epic Launcher 的 `LauncherInstalled.dat` 中 `InstallationList` 为空，常见路径与命令行均未发现 `UnrealEditor.exe`、`UnrealBuildTool` 或 `RunUAT`，当前不具备真实 UE5 Build 条件。
- 本机已有 Visual Studio 2022 Build Tools 17.14、MSVC 14.44.35207、Windows SDK 10.0.26100.0 和 MSBuild；这些版本满足 UE 5.8 官方最低要求和 Epic 构建农场工具链口径，主要缺口是 UE5 引擎本体。
- 现有正式契约字段为 `scenario.scenario_id`、`phases[].pattern.wave_interval_ms`、`bullet_lifetime_seconds`；随机种子由命令行传入。UE5 不得另建 `scene_id`、`fire_interval` 或平行 Schema。
- Unity 原始 Telemetry 使用 `scenario_id/status/run_mode/random_seed/...`，并不包含新提案中的 `engine_name/config_hash/build_id/run_id/completed`。跨引擎层应生成规范化证据包装，不应破坏或重命名现有 Unity artifact。
- 现有 Unity 启动、自动双跑、截图和 artifact 白名单集中在 `workflow/bullet_hell_workflow.py`；API 位于 `api/server.py`；Unity 配置读取与证据分别位于 `BulletHellConfigLoader.cs`、`BulletHellRuntimeBootstrap.cs`、`BulletHellTelemetryRecorder.cs`；Web 主入口为 `BulletHellWorkflowPanel.tsx`。
- UE5 首期只实现 spiral 是合理垂直切片，但当前正式 baseline 同时含 ring、spiral、petal。Runner 必须明确验证能力：首期 UE5 运行应使用从正式只读 baseline 派生、仅保留/聚焦 phase_2 spiral 的兼容快照，或者在工作流层明确拒绝完整三 Pattern 运行，不能静默忽略 phase_1/phase_3。
- “进程返回 0”不足以判定引擎运行成功。跨引擎 Runner 必须同时验证可执行文件、超时、Telemetry JSON、配置哈希、完成状态、必要截图和关键错误日志。
- 仅“从 Hub 打开并关闭 Editor”仍不足以保证命令行 batchmode 获得许可证。本次日志显示 `LicenseClient-Administrator` IPC 通道拒绝连接，随后每轮重连等待约 60 秒；再次验收时应保持 Unity Hub 登录且进程处于运行状态，并把 Licensing Client 初始化单独纳入环境检查。
