# Agentic Game R&D Lab 项目计划

## 项目目标

构建一个由统一 Python Agent 运行时、Unity 可控战斗测试床和 React 控制台组成的本地游戏研发 Agent 实验室。系统以配置变更、质量审查、确定性自动试玩和 telemetry 证据形成可回放闭环。

## High-Level Roadmap

| Milestone | 目标 | 状态 |
|---|---|---|
| Milestone 0 | 单仓库迁移与集成 | complete |
| Milestone 1 | 灰盒自动战斗测试床 | planned |
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

`Milestone 0 complete；下一阶段为 Milestone 1 灰盒自动战斗测试床。`

## 遇到的错误

| 日期 | 错误 | 尝试次数 | 处理 |
|---|---|---:|---|
| 2026-07-18 | 合并两个测试目录时，源目录中的 `__pycache__` 发生同名冲突 | 1 | 清理新仓库缓存，改为按相对路径只迁移测试源文件和 fixtures |
| 2026-07-18 | 来源清单脚本中的反斜杠路径表达式触发 PowerShell ParserError | 1 | 改用显式字符码 92/47 分两步标准化路径 |
| 2026-07-18 | PowerShell 中的 `python` 指向 Hermes venv，缺少 pytest | 1 | 检测到 `D:\anaconda\python.exe` 与 pytest，统一脚本增加 Python 解释器解析 |
| 2026-07-18 | 沙箱网络限制导致 pip 无法下载 `setuptools` 构建依赖 | 1 | 保留仓库 `.venv`，申请受控网络权限后重跑 bootstrap |
| 2026-07-18 | setuptools 拒绝自动发现统一运行时中的多个顶层包 | 1 | 在 `pyproject.toml` 显式包含四个运行包并排除 tests/examples |
| 2026-07-18 | Unity batchmode 返回 198，Licensing Client 无 access token/entitlement | 1 | 增强错误分类，并在沙箱外复测以区分进程隔离与本机 Hub 授权问题 |
