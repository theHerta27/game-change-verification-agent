# Python 运行时约束

- `gameconfig_agent` 与 `agent_service` 是同一 Python 运行时中的两个迁移能力包，不得拆成独立微服务。
- `api/server.py` 是唯一 FastAPI 启动入口。
- `workflow` 只实现确定性状态机；Validator、Parser、Evaluator 和 Gate 不命名为 Agent。
- 保留现有 GameConfig API、artifact 字段和两个源包的 Mock 行为。
- Milestone 3B 只审查人工 C# Diff；候选补丁只允许应用到 `runtime-artifacts/code-workflows` 的隔离副本。
- Milestone 4 Code Change Agent 只读取用户显式选择的最多 3 个 `game-unity/Assets/Scripts/**/*.cs` 文件并生成候选 Diff。
- Milestone 5 只增加版本化 benchmark、失败分类和只读报告；脚本化 Provider 成绩不得表述为真实模型质量。
- Milestone 6 真实评测必须逐样本保存 provider/model/prompt/latency/usage、原始坏例和语义断言；环境缺失时生成 blocked 报告而不是 traceback。
- 已保存的真实输出只允许通过离线 replay 重算本地指标；不得把 replay 伪装为新的模型调用。
- Milestone 7 弹幕工作流使用独立 `/api/bullet-hell` 命名空间和 contract；一次人工授权后最多自动运行三个候选，最终仍需人工接受或回滚。
- 弹幕自动修复只能从有限动作中选择，并由确定性调参器修改候选 JSON；不得修改 C# 或正式基线。
- Requirement Agent 只生成结构化目标和候选配置；Quality Review Agent 只审查需求、Diff、Telemetry 和历史，不得直接计算或写入配置数值。
- Quality Review Agent 的输出必须通过确定性策略门；硬指标失败时禁止模型直接接受。
- EngineRunner 只能启动仓库预注册的固定 Player 和当前 workflow 快照；不得接收任意 EXE、命令或配置路径。
- Unity 原始 Telemetry 字段保持兼容；跨引擎公共字段写入新增规范化证据，不得重命名旧 artifact。
- 不直接写数据库，不引入 Go、Redis、队列或主仓库自动代码修改。
- 变更后必须在本目录运行 `python -m pytest tests`。
