# DevQuality Agent 演示流程

## 演示目标

用一个 Git Diff 展示从任务创建、数据库队列、Agent 审查、结构化校验、报告生成到人工反馈的完整链路。

## 服务职责

| 组件 | 作用 |
| --- | --- |
| Demo Console | 输入 Diff、选择工作流和模型、轮询状态、展示结果、提交反馈 |
| Go Backend | API、限流、DB-backed queue、worker pool、任务状态和唯一数据库写入 |
| Python Agent Service | diff parser、static checker、Mock/Real LLM、schema、validator、报告生成 |
| PostgreSQL | 保存任务输入快照、findings、test suggestions、agent runs、报告和反馈 |
| Redis | 限流、任务锁和运行任务计数，不作为任务队列 |

## 启动顺序

推荐在项目根目录执行：

```powershell
cd D:\Desktop\DevQuality-Agent
.\scripts\check_local.ps1
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_local.ps1
```

脚本按以下依赖检查或启动：

1. PostgreSQL `5432`。
2. Redis `6379`。
3. Python Agent Service `8010`。
4. Go Backend `18080`。
5. Frontend `5173`。

首次数据库初始化还需执行 `001_init.sql`、`002_real_llm.sql`、`003_real_llm_debug.sql`。每个组件的独立 PowerShell 命令和错误定位见 `docs/WINDOWS_LOCAL_RUNBOOK.md`。

## MockLLM 演示

1. 打开 Demo Console，点击“载入示例”。
2. 选择 Go、Review/Test 双 Agent、MockLLM。
3. 点击“运行代码审查”。
4. 观察任务从 `pending` 到 `running`，最终进入 `succeeded`。
5. 查看风险项和关联测试建议；切换“报告”和“JSON”检查结构化输出。
6. 在风险项下选择“有帮助”或“不准确”，可附加中文备注；成功后页面显示“已写入”。

## Real LLM 演示

1. 选择“真实模型”。
2. 选择 Python `.env` 的服务端默认配置，或填写本次请求临时覆盖配置。
3. 提交后，浏览器只把配置发送给本机 Go Backend；浏览器不直接调用厂商。
4. Go worker 在内存中读取一次性配置并调用 Python Agent Service。
5. Python 调用 Chat Completions；若首次 JSON/schema 无效，会执行一次 schema repair。
6. 最终结果必须经过现有 Pydantic schema 和确定性 validator，才能持久化为成功任务。

## 结果解读

- **风险项**：文件、行号、严重程度、证据、建议、置信度和来源。
- **测试建议**：必须通过 `finding_index` 关联已验证 finding。
- **报告**：由结构化结果渲染，不包含 API key。
- **JSON**：展示任务、findings、test suggestions 和 agent runs。
- **评测基准**：展示 Phase 4A mock evaluation 与本机 load test 图表。

当前 mock evaluation 只验证 workflow、schema、validator、deterministic rules 和 backend pipeline，不代表真实 LLM 准确率。
