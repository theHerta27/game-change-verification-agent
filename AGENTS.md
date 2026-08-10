# Game Change Verification Agent 工程约束

## 权威目录

- Python Agent、API、校验和评测：`services/agent-python/`
- Unity 运行时与自动试玩：`game-unity/`
- Unreal Engine 最小验证切片：`game-unreal/`
- React 控制台：`web-console/`
- 稳定数据契约：`contracts/`
- 固定配置、场景和评测：`configs/`、`scenarios/`、`evals/`

原始 `GameConfig-Agent` 与 `DevQuality-Agent` 项目仅作为只读来源。不得从本项目任务中修改它们。

## 当前阶段

Milestone 8 已完成。Unity 弹幕闭环、统一 EngineRunner 和真实 UE5 C++ Windows Player 跨引擎验证均已落地；Training Sword 旧回归继续保留。

禁止：

- 在已批准的 2.5D 弹幕 Boss 测试床之外新增构筑、掉落、养成或其他玩法。
- 扩展灵梦模型、动画、物理或正式美术表现；只允许复用现有本地可选表现层。
- 新增 Go 服务、数据库、Redis、Docker 或微服务。
- 让模型浏览未授权文件，或向主仓库自动应用代码补丁。
- 在隔离工作区之外应用候选 C# Diff，或绕过人工审批启动 Unity 验证。
- 修改已有 GameConfig API、JSON artifact 和 Unity runtime contract 字段。
- 用 Mock、Unity 产物或编辑器手工截图冒充 UE5 Build、Telemetry 或自动截图。
- 在真实 UE5 Baseline/Candidate、Telemetry 和截图再次通过前，把新修改后的 Unreal Runner 标为 `verified`。
- 未经一次明确授权启动弹幕隔离测试，或绕过最终人工决策覆盖任何已提交基线。
- 提交 `.env`、密钥、第三方模型、贴图、音频、运行产物或构建缓存。

发现架构冲突、契约不兼容或需要扩大范围时，停止并记录到 `findings.md`，不要自行大规模重构。

## 必须执行的验收

```powershell
.\scripts\test-python.ps1
.\scripts\test-web.ps1
.\scripts\smoke-unity.ps1
.\scripts\smoke-unreal.ps1
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
- `game-unreal/**/Binaries`、`DerivedDataCache`、`Intermediate`、`Saved` 和本地 UE Build 永不提交。
- 已提交的 Scene 或 Prefab 不得序列化引用本地角色 Prefab。
- 角色表现通过运行时路径解析，缺少本地模型时必须回退到已提交占位角色。
