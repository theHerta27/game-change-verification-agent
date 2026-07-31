# Unreal Engine 子系统约束

- 使用仓库现有 `bullet_hell_contract_version: "1.0"`，不得创建平行字段。
- C++ 负责配置解析、确定性模拟、Telemetry、截图和退出状态。
- 表现层只允许使用仓库内原创几何体、材质或 Blueprint。
- 自动运行只接受命令行指定的当前 workflow 配置和输出目录。
- 真实 Windows Player、Telemetry、截图和 Baseline/Candidate 双跑已通过；修改 C++、Blueprint 或打包流程后必须重新执行 `scripts/smoke-unreal.ps1`，保留真实证据后才能继续声明 `verified`。
- 未生成真实 Windows Player、Telemetry 和截图前，不得将 Runner 标记为 `verified`。
- `Binaries/`、`Intermediate/`、`Saved/`、`DerivedDataCache/` 和 `Builds/` 不得提交。
