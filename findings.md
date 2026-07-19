# Findings

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
- 自动检索整个仓库会扩大提示词、权限和错误归因范围。本阶段由开发者显式选择最多 3 个运行时 C# 文件，更适合作为可解释的最小权限原型。
- 生成 Provider 与质量审查 Provider 应分离：真实模型负责提出候选，确定性规则和 Mock Review 负责稳定门禁，避免一次模型调用同时充当作者和批准者。
- Mock 只有固定 recipe 时必须返回 `needs_clarification` 处理其他需求；用固定补丁响应任意需求会制造虚假的 Agent 能力。
- 真实模型即使返回合法 JSON，也可能声明或实际修改未授权文件；必须同时检查 `target_files` 字段和 unified diff 中的真实路径。
- 代码生成失败不是接口异常：JSON parse、Prompt Contract、目标范围和 Patch Safety Gate 失败都应形成含原始输出的 badcase。
- 当前允许列表不包含 `Assets/Editor`，是为了防止候选补丁改变构建/校验器本身；被测运行时代码和测试工具必须保持权限分离。
