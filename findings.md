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
