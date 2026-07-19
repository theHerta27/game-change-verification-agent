# Workflow

此目录用于统一的确定性研发状态机，不是额外 Agent。

Milestone 3A 当前包含：

- `config_change.py`：能力门禁、白名单约束映射、Config Diff、静态校验和配置质量审查。
- `change_workflow.py`：文件状态机、人工审批、隔离 Unity run、telemetry 证据同步和最终决策。

运行状态只写入根目录 Git 忽略的 `runtime-artifacts/change_workflows`。候选配置未经人工审批不得进入 Unity，也不得覆盖已提交基线。
