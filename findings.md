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
