# 来源组件清单

## 来源状态

两个来源目录都不是 Git 仓库，因此没有 commit、branch 或 dirty 状态可记录。新仓库使用 `source-manifest.json` 保存逐文件 SHA256；迁移后的首次 Git 提交是第一份版本化基线。

来源项目只读：

```text
GameConfig-Agent
DevQuality-Agent
```

## GameConfig-Agent

已导入：

- `gameconfig_agent` Python 包。
- Python tests 与 examples/classic_cases。
- React 前端源码和唯一 package lock。
- Unity `Assets`、`Packages`、`ProjectSettings` 及 `.meta`。
- 项目文档和 phase0/1/2/3/final 演示产物。

未导入：

- `.env`、IDE 与 pytest 缓存。
- `node_modules`、`dist` 和 TypeScript 构建中间文件。
- Unity `Library`、`Temp`、`Logs`、`Builds`、`UserSettings`。
- runtime runs、进程日志和临时输出。

## DevQuality-Agent

已导入：

- `agent_service` Python 包。
- Diff Parser、Static Checker、Review/Test Agent、Finding/Test Suggestion schema、Validator 和 evaluator。
- Python tests、patch examples 和 real LLM smoke cases。
- 必要文档。

未导入：

- Go backend、`.gocache` 和可执行文件。
- DevQuality 旧 React 前端和 design-system。
- PostgreSQL、Redis、部署与旧启动脚本。
- `.env`、logs、outputs 和缓存。

## 迁移后的边界

`services/agent-python` 是唯一 Python 运行时。迁移保留旧包名只是兼容措施，不代表两个独立服务。统一入口为：

```text
services/agent-python/api/server.py
```
