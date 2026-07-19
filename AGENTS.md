# Agentic Game R&D Lab 工程约束

## 权威目录

- Python Agent、API、校验和评测：`services/agent-python/`
- Unity 运行时与自动试玩：`game-unity/`
- React 控制台：`web-console/`
- 稳定数据契约：`contracts/`
- 固定配置、场景和评测：`configs/`、`scenarios/`、`evals/`

旧目录 `D:\Desktop\GameConfig-Agent` 与 `D:\Desktop\DevQuality-Agent` 仅作为只读来源。不得从新项目任务中修改它们。

## 当前阶段

Milestone 3A 配置变更闭环已完成。下一阶段为 Milestone 3B 人工 C# Diff 质量闭环；统一 `workflow` 只负责确定性编排、人工门禁和证据持久化，不替代已有 Agent 与 Tool。

禁止：

- 新增 Boss、构筑、掉落、养成或其他玩法内容。
- 处理灵梦模型、动画、物理或正式美术表现。
- 新增 Go 服务、数据库、Redis、Docker 或微服务。
- 实现 Code Change Agent 或自动应用代码补丁。
- 修改已有 GameConfig API、JSON artifact 和 Unity runtime contract 字段。
- 绕过人工审批把候选配置直接送入 Unity，或覆盖已提交的 `game_config.json` 基线。
- 提交 `.env`、密钥、第三方模型、贴图、音频、运行产物或构建缓存。

发现架构冲突、契约不兼容或需要扩大范围时，停止并记录到 `findings.md`，不要自行大规模重构。

## 必须执行的验收

```powershell
.\scripts\test-python.ps1
.\scripts\test-web.ps1
.\scripts\smoke-unity.ps1
.\scripts\verify-repo-clean.ps1
```

完成整个 Milestone 时执行：

```powershell
.\scripts\test-all.ps1
```

Milestone 2 本地资产通路可单独执行：

```powershell
.\scripts\bootstrap-blender.ps1
.\scripts\convert-reimu.ps1
.\scripts\import-reimu-unity.ps1
.\scripts\smoke-reimu-presentation.ps1
```

## 本地资产

- `local-assets/` 和 `game-unity/Assets/Resources/LocalThirdParty/` 永不提交。
- 已提交的 Scene 或 Prefab 不得序列化引用本地角色 Prefab。
- 角色表现通过运行时路径解析，缺少本地模型时必须回退到已提交占位角色。
