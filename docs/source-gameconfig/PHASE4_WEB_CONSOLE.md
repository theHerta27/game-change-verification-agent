# Phase 4 Web Console 与 Agent Trace 可视化

## 范围

Phase 4 新增本地 Web Console，用于检查现有 GameConfig Agent workflow。不重构 Phase 0 / Phase 1 / Phase 2 / Phase 3 核心 pipeline。

> 当前界面已在 Phase 6F 演进为双层信息架构：默认“策划 / QA 视图”用于查看业务结论、风险和改进建议；“开发者调试”视图用于查看 Agent Trace、Blackboard、JSON、离线回归和 artifacts。详见 [PHASE6F_PLANNER_VIEW.md](PHASE6F_PLANNER_VIEW.md)。本页保留 Phase 4 的基础架构与启动说明。

## 架构

```text
React + Vite + TypeScript 前端
        |
        | HTTP
        v
FastAPI 本地 API wrapper
        |
        v
现有 GameConfig Agent pipeline 模块
```

不引入数据库、登录、Docker 或复杂部署。

## 后端启动

```powershell
.\scripts\start_backend.ps1
```

默认地址：

```text
http://127.0.0.1:8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

注意：后端根路径不是前端页面。后端 `/` 会返回一个 JSON 提示，真正的前端页面地址是 `http://127.0.0.1:5173`。

后端脚本支持临时端口：

```powershell
.\scripts\start_backend.ps1 -Port 8001
```

但前端 Vite 代理默认指向 `http://127.0.0.1:8000`。如果后端改到 8001，前端页面本身仍从 5173 打开，但页面里的 API 调用需要同步修改 `frontend/vite.config.ts`。

## API

- `GET /`
- `GET /api/health`
- `POST /api/runs/demo`
- `POST /api/runs/benchmark`
- `GET /api/artifacts/{phase}`
- `GET /api/reports/{phase}/{name}`

Demo endpoint 支持：

- `requirement_text`
- `provider`: `mock` 或 `openai_compatible`
- `timeout_seconds`

## 前端启动

```powershell
.\scripts\start_frontend.ps1
```

如果 5173 被占用：

```powershell
.\scripts\start_frontend.ps1 -Port 5174
```

打开：

```text
http://127.0.0.1:5173
```

脚本使用 `--strictPort`，不会在 5173 被占用时静默切换端口。若切到 5174，需要打开 `http://127.0.0.1:5174`。

生产构建：

```powershell
cd frontend
npm run build
```

## 页面功能

Web Console 支持：

- Requirement text 输入
- Provider 选择
- Timeout 设置
- 单样本 demo run
- Phase 3 benchmark run
- Workflow Summary
- Agent / Tool Timeline
- Blackboard Trace
- Draft Config
- Final Config
- Validation Errors
- Review Findings
- Repair Actions
- Test Scenarios
- Evaluation Metrics
- Badcases
- Markdown report preview
- Artifact list

## Phase 3 Benchmark 展示

UI 展示：

- `sample_count`
- `schema_pass_rate`
- `reference_pass_rate`
- `rule_pass_rate`
- `repair_success_rate`
- `test_scenario_coverage_rate`
- `badcase_count`
- `unresolved_count`
- `avg_repair_actions`

## 边界

- 默认 provider 是 `mock`。
- 真实 provider 是可选能力，并带 timeout 与错误提示。
- 已有 CLI 命令继续保留。
- 不引入持久化数据库。
