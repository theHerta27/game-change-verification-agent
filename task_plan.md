# Agentic Game R&D Lab 项目计划

## 项目目标

构建一个由统一 Python Agent 运行时、Unity 可控战斗测试床和 React 控制台组成的本地游戏研发 Agent 实验室。系统以配置变更、质量审查、确定性自动试玩和 telemetry 证据形成可回放闭环。

## High-Level Roadmap

| Milestone | 目标 | 状态 |
|---|---|---|
| Milestone 0 | 单仓库迁移与集成 | complete |
| Milestone 1 | 灰盒自动战斗测试床 | complete |
| Milestone 2 | 灵梦角色表现层 | planned |
| Milestone 3A | 配置变更闭环 | planned |
| Milestone 3B | 人工 C# Diff 质量闭环 | planned |
| Post-MVP | 受控 Code Change Agent | deferred |

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
