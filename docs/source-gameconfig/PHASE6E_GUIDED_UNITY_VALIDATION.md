# Phase 6E：引导式 Unity 运行验证

## 目标

Phase 6E 不新增 Agent、不扩展玩法。它只解决一个工程问题：把一次配置生成、一次 Unity 试玩、一次 telemetry 和一次运行评测绑定成同一个可追踪任务。

## 运行目录

每次准备 Unity 测试都会创建：

```text
outputs/runtime_runs/{run_id}/
  run_manifest.json
  requirement.txt
  final_configs.json
  unity_contract.json
  telemetry.json
  runtime_evaluation.json
  runtime_evaluation_report.md
  improvement_suggestions.json
  pipeline/
```

`pipeline/` 保存本次静态生成、校验和修复产物。其余文件是 Unity 运行证据。

## 状态机

```text
prepared
  -> launched
  -> evaluated

prepared / launched
  -> failed
```

- `prepared`：静态校验通过，本次 contract 已导出。
- `launched`：Unity Player 已由用户明确点击启动。
- `evaluated`：telemetry 已写入并完成 Runtime Evaluation。
- `failed`：启动失败，或 Unity 在生成 telemetry 前退出。

业务目标未通过不会把任务状态写成 `failed`。只要 Unity 正常完成并产出 telemetry，任务就是 `evaluated`；具体策划目标通过与否由 `runtime_evaluation.passed` 表示。

## API

```text
POST /api/runtime-runs
POST /api/runtime-runs/{run_id}/launch
GET  /api/runtime-runs/{run_id}
POST /api/runtime-runs/{run_id}/evaluate
GET  /api/runtime-runs/{run_id}/artifacts/{name}
```

准备请求：

```json
{
  "case_id": "case_01_baseline_trial",
  "requirement_text": "...",
  "provider": "mock"
}
```

真实 Provider 的准备请求还包含本次已通过校验的快照：

```json
{
  "case_id": "case_01_baseline_trial",
  "requirement_text": "...",
  "provider": "openai_compatible",
  "structured_requirement": {},
  "final_configs": {},
  "model": "configured-model-name"
}
```

这里的空对象只用于说明字段位置；实际请求必须传入完整结构，后端会重新校验。

启动请求：

```json
{
  "mode": "manual"
}
```

`mode=manual` 打开可视 Unity Player，由用户试玩。`mode=auto` 启动自动战斗，用于稳定回归。

## 安全边界

- FastAPI 只启动项目内固定的 `GameConfigRuntimeDemo.exe`。
- API 不接受任意可执行文件路径或任意命令行参数。
- 每次运行只读取自己的 `unity_contract.json` 并写入自己的 `telemetry.json`。
- Unity 仍保留 StreamingAssets fallback，旧 CLI 和手动启动方式不变。
- Player 必须包含 `guided_runtime_version.txt` 标记，否则后端拒绝启动，避免旧构建错误读取全局 contract。
- `case_04_missing_reference` 是静态引用校验案例，不允许伪装成 Unity 运行。
- Guided Run 接受 deterministic Mock 配置，也接受本次真实 Provider 已通过 Final Validation 的配置。
- 真实配置在 prepare 时必须携带 `structured_requirement`、`final_configs` 和 model，并由后端重新执行 Schema、Reference、Rule 校验；前端校验结果不能直接绕过后端质量门禁。

## 首次构建

先确认 Unity Hub 或 Unity Editor 登录并具有有效许可证，再运行：

Unity Hub 3.19 的“导入项目”入口按所选目录的下一层批量扫描项目。使用这个入口时请选择父目录：

```text
D:\Desktop\GameConfig-Agent\unity
```

Hub 会在其中识别 `GameConfigRuntimeDemo`。如果使用“从磁盘添加项目”入口，则直接选择：

```text
D:\Desktop\GameConfig-Agent\unity\GameConfigRuntimeDemo
```

也可以绕过 Hub 的项目列表，直接用指定 Editor 打开：

```powershell
& 'E:\Unity6\6000.3.19f1\Editor\Unity.exe' `
  -projectPath 'D:\Desktop\GameConfig-Agent\unity\GameConfigRuntimeDemo'
```

项目根目录必须直接包含 `Assets`、`Packages` 和 `ProjectSettings`；当前仓库中的目录结构已经满足该要求。

```powershell
cd D:\Desktop\GameConfig-Agent
.\scripts\build_unity_demo.ps1
```

成功后应存在：

```text
unity/GameConfigRuntimeDemo/Builds/Windows/guided_runtime_version.txt
```

## Web Console 操作

开始操作前先访问：

```text
http://127.0.0.1:8000/api/health
```

支持真实配置交接 Unity 的后端应包含：

```json
{
  "backend_version": "phase6g-real-runtime-handoff",
  "capabilities": {
    "real_provider_runtime_handoff": true
  }
}
```

如果只看到 `status` 和 `service`，说明 8000 端口仍是修改前启动的旧 Python 进程。源文件更新不会自动替换已加载到内存中的 FastAPI 应用；需要在后端 PowerShell 窗口按 `Ctrl+C`，再运行 `.\scripts\start_backend.ps1`。前端也会在真实配置交接前检查该能力并给出重启提示。

1. 选择一个经典案例。
2. 选择 Mock 或真实 provider。
3. 点击“生成并校验当前需求”；真实 provider 必须通过本次 Final Validation。
4. 最终静态校验通过后点击“准备本次 Unity 测试”。
5. 选择“打开 Unity 手动试玩”或“运行 Unity 自动回归”。
6. 手动模式下完成三波战斗，不要在完成前关闭 Player。
7. 页面轮询本次 run；telemetry 出现后自动执行评测。
8. 查看策划目标、实际结果、状态、改进建议和本次运行证据。

## 当前限制

- Mock 仍固定生成 Training Sword。
- Unity 仍只有一个 Training Sword 试玩场景。
- 改进建议是确定性规则映射，尚未自动回写配置。
- 真实 Provider 进入 Unity 只证明当前配置通过静态门禁并能在该固定场景运行，不代表模型已适配任意游戏配置类型。
- 修复前后运行对比尚未实现。
- 当前没有数据库；运行状态完全由 `outputs/runtime_runs` 文件保存。
