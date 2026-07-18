# Agentic Game R&D Lab

AI Agent 驱动的 Unity 游戏研发与质量保障实验室。项目将策划配置生成、代码质量审查、Unity 可控运行环境和 telemetry 证据放进同一个本地单仓库。

**Milestone 0：单仓库迁移与集成已完成。** 当前下一阶段为 Milestone 1 灰盒自动战斗测试床。本轮没有新增 Boss、Roguelite 构筑或自动代码修改。

## 当前组成

- `services/agent-python`：唯一 Python 运行时，包含 GameConfig 配置能力与 DevQuality Python 质量审查能力。
- `game-unity`：从 GameConfig Runtime Demo 迁移的 Unity 6 测试床。
- `web-console`：唯一 React 控制台。
- `runtime-artifacts`：本地运行证据，不提交 Git。
- `local-assets`：灵梦 PMX、转换文件和其他第三方本地资产，不提交 Git。

## 首次准备

```powershell
cd D:\Desktop\agentic-game-rd
.\scripts\bootstrap.ps1
```

## 启动后端

```powershell
cd D:\Desktop\agentic-game-rd\services\agent-python
..\..\.venv\Scripts\python.exe -m uvicorn api.server:app --host 127.0.0.1 --port 8000
```

后端入口：

- Health：`http://127.0.0.1:8000/api/health`
- OpenAPI：`http://127.0.0.1:8000/docs`
- 配置工作台 API：保留原 GameConfig 路由。
- 质量审查：`POST /api/quality/review`

## 启动前端

```powershell
cd D:\Desktop\agentic-game-rd\web-console
npm run dev -- --host 127.0.0.1 --port 5173
```

打开 `http://127.0.0.1:5173`。

## Unity

在 Unity Hub 中添加：

```text
D:\Desktop\agentic-game-rd\game-unity
```

项目锁定 Unity `6000.3.19f1`。没有本地灵梦模型时使用仓库内占位角色；本地模型后续通过 `CharacterViewResolver` 动态替换，不改变战斗逻辑。

## 验证

```powershell
.\scripts\test-all.ps1
```

也可以分别运行：

```powershell
.\scripts\test-python.ps1
.\scripts\test-web.ps1
.\scripts\smoke-unity.ps1
.\scripts\verify-repo-clean.ps1
```

## 当前边界

- 不使用 DevQuality 旧 Go 后端、旧前端、PostgreSQL 或 Redis。
- 不实现 Code Change Agent。
- 不公开分发灵梦模型、贴图或本地音频。
- 单次 Unity 前后对比不宣称为统计学 A/B 实验。

详细来源、工具链和迁移结果见 `docs/`。
