# Python 运行时约束

- `gameconfig_agent` 与 `agent_service` 是同一 Python 运行时中的两个迁移能力包，不得拆成独立微服务。
- `api/server.py` 是唯一 FastAPI 启动入口。
- `workflow` 只实现确定性状态机；Validator、Parser、Evaluator 和 Gate 不命名为 Agent。
- Milestone 0 保留现有 GameConfig API、artifact 字段和两个源包的 Mock 行为。
- 不直接写数据库，不引入 Go、Redis、队列或自动代码修改。
- 变更后必须在本目录运行 `python -m pytest tests`。

