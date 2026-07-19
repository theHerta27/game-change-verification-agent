# Progress

## 2026-07-18 Milestone 0

### 已完成

- 阅读并采用 `planning-with-files-zh` 工作方式。
- 核对两个旧项目均不是 Git 仓库。
- 核对 Unity、Python、React、DevQuality Python 的迁移来源和排除目录。
- 创建 `D:\Desktop\agentic-game-rd` 目录骨架。
- 创建根 `task_plan.md`、`findings.md` 和 `progress.md`。

### 进行中

- 已迁移主要 Python、React、Unity、文档、示例产物和本地模型压缩包。
- 测试缓存冲突已通过只迁移源文件解决。
- 来源清单脚本首次执行发生 PowerShell 路径解析错误，已改为显式字符标准化，等待重跑。
- 来源清单已成功生成，包含 215 个导入文件。
- Python 测试首次被 Hermes venv 缺少 pytest 阻断；已发现本机 Anaconda Python，正在修正统一脚本的解释器选择。
- 已建立仓库 `.venv`；首次依赖安装被沙箱网络策略阻断，等待受控网络重试。
- 网络重试成功进入打包阶段；已发现并修正多顶层包的显式 package discovery。
- Python 统一测试通过：91 passed，1 warning。
- React production build 通过：Vite built in 14.69s。
- Unity 首次 batch smoke 在编译前被许可证 access token/entitlement 阻断，正在执行沙箱外复测。

### 尚未执行

- 无。Milestone 0 已完成，后续工作进入 Milestone 1 前需由用户确认。

### 最终结果

- `source-manifest.json`：215 个文件，来源哈希验证通过。
- Python：91 passed，1 warning。
- Web：Vite production build 通过，最终验证 2.61s。
- Unity：Windows Build、角色回退/替换分支和自动战斗通过。
- Telemetry：completed，3 波，5 击败，27 次普攻，2 次技能，15.1531s。
- FastAPI：GameConfig health 与 Quality Review health 均为 HTTP 200。
- 仓库清洁：通过。

## 2026-07-18 Milestone 1

### 已完成

- 新增版本化测试画像 `starter_trial_baseline.json`，固定 seed `20260718`。
- Unity 场地改为圆形灰盒竞技场，角色移动按圆形边界约束。
- 新增自动/手动运行模式和 seed 参数解析。
- 自动战斗迁移到 `FixedUpdate()` 固定步长，手动输入保持原路径。
- telemetry 新增 run mode、seed、simulation ticks 和三波明细。
- 新增 Python Testbed Evaluator、CLI 和 3 项单元测试。
- smoke 脚本改为同 seed 双跑并生成 JSON/Markdown 可重复性报告。
- 修复 Unity 完成运行后立即退出导致的偶发访问冲突。

### 当前验证

- 两次结果：999 ticks、3 波、5 击败、30 普攻、1 技能、1700 伤害、268 承伤、16.6333s。
- Python：94 passed，1 warning。
- Web：Vite production build 通过，3.46s。
- Unity：Windows Development Build、固定种子双跑和分波次 telemetry 通过。
- Testbed Evaluation：10/10，通过率 100%，两次通关时间差 0s。
- FastAPI 实进程：`/api/health` 与 `/api/quality/health` 均为 HTTP 200。
- 仓库清洁与两个旧来源目录 SHA256：通过。

### 最终状态

`Milestone 1 complete。下一阶段为 Milestone 2 灵梦角色表现层。`

## 2026-07-18 Milestone 2

### 已完成

- 自动下载并锁定 Blender 4.5.11 portable 与 MMD Tools v4.5.10。
- 后台导入 `R_spring.pmx`，导出 FBX、Blend、贴图和转换报告。
- Unity 自动导入 FBX、归一化身高并生成本地 Reimu Prefab。
- 12 个材质全部绑定贴图，unsupported shader 和 missing texture 均为 0。
- CharacterViewResolver 实际本地模型分支通过。
- 新增轻量待机/移动摆动、御札/阴阳玉占位表现和命中脉冲。
- 调整运行镜头并完成 1280x720 截图人工检查。
- 像素检查通过：非背景 31.9%，红色像素 3835，中央亮色像素 2705。
- Milestone 1 固定种子双跑保持 100% 可重复。
- 逻辑双跑改为无图形模式，避免 Unity 图形设备退出的间歇性访问冲突。

### 最终验收

- Blender PMX 转换：通过，1 Mesh / 301 Blender Bones / 15,913 Vertices / 12 Materials。
- Unity 导入：通过，297 Unity Bones / 12 Bound Textures / 0 Missing / 0 Unsupported Shaders。
- Reimu runtime preview：通过人工检查和像素检查。
- Placeholder `--force-placeholder` 实际 Player 回退：通过。
- Python：94 passed，1 warning。
- Web：Vite production build 通过，2.57s。
- Unity：Windows Build、无图形固定种子双跑、D3D11 截图均通过。
- Milestone 1 Repeatability：10/10，100%。
- 仓库清洁和旧来源 SHA256：通过。

### 最终状态

`Milestone 2 complete。下一阶段为 Milestone 3A 配置变更闭环。`

## 2026-07-19 Milestone 3A

### 已开始

- 核对现有 Requirement Intake、Mock 生成、Schema/Reference/Rule 校验、RuntimeRunService 和统一 FastAPI 入口。
- 确认现有 MockLLM 是固定 Training Sword 样例，Milestone 3A 需要增加确定性的约束映射和逐字段 Config Diff，不能把固定输出包装成按需生成。
- 确认 RuntimeRunService 已提供隔离配置快照、Unity 启动、telemetry 回收和运行评测能力，可作为审批后的执行层复用。
- 冻结 Milestone 3A 状态机、人工审批门禁和隔离回滚语义。

### 进行中

- 实现 Change Feasibility Gate、候选配置映射、配置差异、质量审查和文件状态机。

### 已完成

- 新增 `workflow/config_change.py`，实现能力门禁、受支持约束映射、逐字段 Config Diff、静态校验、需求覆盖审查和测试建议。
- 新增 `workflow/change_workflow.py`，实现文件状态机、人工审批、隔离 Unity run、telemetry 同步与接受/修订/回滚决策。
- RuntimeRunService 新增已审批精确快照入口，不重新调用 Mock，不覆盖已提交基线。
- FastAPI 新增 `/api/change-workflows` 提案、审批、运行、启动、决策和 artifact 接口。
- 策划视图收敛为一条配置变更闭环；旧 Phase 0/1/2/3 控件保留在开发者调试视图。
- 新增可指定端口的 `start-backend.ps1` 和 `start-web.ps1`；前端端口变化时可同步指定后端代理端口。
- 新增中文原理与操作文档 `docs/MILESTONE3A_CONFIG_CHANGE_WORKFLOW.md`。

### 最终验收

- Python：`101 passed`，1 条既有 Starlette/httpx 弃用告警。
- Web：1579 modules transformed，production build 通过，最终复测 3.41s；CSS 20.54 kB，JS 260.98 kB。
- API：8001 实进程 health 返回 `milestone3a-change-workflow`，策划页面通过 5174 代理访问。
- 页面全流程：创建 Mock 提案、人工审批、隔离准备、Unity 固定种子自动试玩、telemetry 回收、风险展示和“要求修订”决策全部通过。
- Unity：沙箱外 Windows Build 与固定种子双跑通过，repeatability 100%。本次约 16.63s，不满足 60–90s 目标，系统正确建议修订。
- 响应式：390px 视口无横向溢出。

### 最终状态

`Milestone 3A complete。下一阶段为 Milestone 3B 人工 C# Diff 质量闭环。`

## 2026-07-19 Milestone 3B

### 已完成

- 新增 C# Patch Safety Gate，限制路径、文件生命周期、变更规模和危险 API。
- 新增精确 hunk 应用器与最小 Unity 源工程复制器，主仓库修改文件前后 SHA256 保持一致。
- DevQuality 静态规则新增 C# 性能、错误处理、安全和固定种子确定性检查。
- 新增 `CodeWorkflowService` 文件状态机：提案、审批、隔离应用、后台 Unity 验证和最终人工决策。
- FastAPI 新增 `/api/code-workflows` 命名空间，现有 API 不变。
- Web Console 开发者视图新增“人工 C# Diff 质量闭环”，策划视图不显示代码补丁。
- 新增安全补丁与危险补丁示例、Python/API 回归和中文说明文档。
- 后台验证新增异常退出兜底，PowerShell BOM JSON 可正常读取。

### 当前验证

- Python 完整回归：118 passed，1 条既有 Starlette/httpx 弃用告警。
- Web production build：1580 modules transformed，通过；CSS 21.05 kB，JS 277.48 kB。
- 隔离 Unity C# Diff：Windows Build、编辑器确定性 smoke、两次固定 seed Player 自动试玩均通过。
- Testbed repeatability：100%。
- Runtime target pass rate：60%，作为既有配置效果证据保留，不误判为代码编译失败。
- 主仓库 C# 基线未被候选补丁修改。

### 最终验收

- `scripts/test-all.ps1`：通过。
- Python：118 passed，1 条既有 Starlette/httpx 弃用告警。
- Web：production build 通过；中文开发者视图完整走通提交、审查、审批和隔离准备，390px 无横向溢出，浏览器控制台无错误。
- Unity：主工程灵梦表现/Placeholder 回退和固定种子双跑通过；隔离 C# 补丁 Windows Build、编辑器 smoke 和 Player 双跑通过。
- 隔离补丁证据：repeatability 100%，runtime target pass rate 60%，主仓库基线未修改。
- 仓库清洁与旧来源 SHA256：通过。

### 最终状态

`Milestone 3B complete。Post-MVP Code Change Agent 保持 deferred，等待单独范围确认。`

## 2026-07-19 Milestone 4

### 已完成

- 新增 Code Change Agent Prompt Contract，输出固定为 summary、assumptions、target_files 和 unified diff。
- 新增目标文件最小权限清单，最多读取 3 个 `Assets/Scripts` C# 文件。
- 新增 deterministic Mock 空参数保护 recipe，其他 Mock 需求返回 needs_clarification。
- 新增真实 OpenAI Compatible 候选生成、JSON/字段/目标范围校验和 badcase 落盘。
- 候选 Diff 自动进入 Milestone 3B Patch Safety Gate、Quality Review 和人工审批闭环。
- FastAPI 新增 capabilities、proposal create/get 接口。
- Web Console 开发者视图新增受控 Code Change Agent，并自动把成功候选载入下方 C# Diff 闭环。
- 保留人工粘贴 Diff 的能力，策划视图不显示代码生成入口。

### 当前验证

- Python：126 passed，1 条既有 Starlette/httpx 弃用告警。
- Web production build：1581 modules transformed，通过；CSS 21.45 kB，JS 288.15 kB。
- 浏览器 Mock 闭环：候选生成、确定性安全门、质量审查、人工批准和隔离工作区准备通过。
- 隔离 Unity 候选验证：Windows Build、编辑器 smoke、两次固定 seed Player 自动试玩均通过。
- 隔离候选证据：repeatability 100%，runtime target pass rate 60%，主仓库 `RuntimeRunSettings.cs` 未被修改。
- 响应式：390px 视口无页面级横向溢出，浏览器控制台无错误。

### 最终验收

- `scripts/test-all.ps1`：通过。
- Python：126 passed，1 条既有 Starlette/httpx 弃用告警。
- Web：production build 通过。
- Unity：主工程固定种子回归、灵梦表现层、Placeholder 回退和隔离候选验证全部通过。
- 仓库清洁与两个旧来源 SHA256：通过。
- 真实 OpenAI Compatible Provider 未消耗真实额度做 smoke；结构化契约、越界拒绝和 badcase 路径由 fake provider 自动测试覆盖。

### 最终状态

`Milestone 4 complete。下一步优先建立代码变更 benchmark、失败分类与可比较指标，不继续扩大 Agent 权限。`

## 2026-07-19 Milestone 5

### 已完成

- 新增 `code_change_guardrail_benchmark_v1`，固定 12 个合法、越界、契约漂移和危险补丁样本。
- 新增脚本化 Provider 与统一 runner，明确只评测护栏和失败路由。
- 新增预期匹配、可行性准确率、badcase 捕获、越权阻断、有效候选接受、错误放行/拒绝和仓库哈希指标。
- 输出 `benchmark_results.json`、`evaluation_report.md`、`badcases.md` 和 `sample_summary.csv`。
- 新增 CLI、数据集 API、运行 API 和开发者视图评测表格。
- 修复 CLI 顶层导入引起的循环依赖，改为命令分支内延迟导入。

### 当前验证

- 固定样本：12。
- 预期匹配率、门禁决策准确率、badcase 捕获率、越权阻断率、有效候选接受率：均为 100%。
- 错误放行：0；错误拒绝：0；badcase：7；主仓库未修改。
- 定向 Python：22 passed，1 条既有 Starlette/httpx 弃用告警。
- Web production build：1582 modules transformed，通过；CSS 21.76 kB，JS 293.92 kB。

### 最终验收

- `scripts/test-all.ps1`：通过。
- Python：130 passed，1 条既有 Starlette/httpx 弃用告警。
- Web：1582 modules transformed，production build 通过；CSS 21.76 kB，JS 293.99 kB。
- 浏览器：实际点击运行 12 个样本并展示完整表格；390px 无页面级横向溢出，控制台无错误。
- Unity：固定 seed 双跑、灵梦预览像素验证和 Placeholder 回退通过。
- 仓库清洁、两个旧来源 SHA256 和 benchmark 前后 C# 源文件哈希：通过。

### 最终状态

`Milestone 5 complete。后续真实 Provider 代码评测必须单独立项并与 scripted_fixture 成绩分开。`

## 2026-07-19 Milestone 6

### 已完成

- 新增 `real_code_generation_v1`，包含 5 个不新增玩法的 Unity C# 防御式需求。
- 新增真实 Provider runner，记录 Provider/JSON/契约/安全/质量/补丁应用/语义阶段、latency、usage 和源码哈希。
- 新增语义工作区，只复制样本目标源文件并精确应用候选补丁，不修改主仓库。
- Code Change Agent badcase 新增 `provider_evidence`，JSON 解析失败仍保留 latency/usage。
- 新增 CLI、配置/数据集/运行 API 和独立开发者面板。
- 新增中文文档，明确 candidate_ready 不等于编译、Unity 试玩或自动合并。

### 当前验证

- 定向 Python：28 passed，1 条既有 Starlette/httpx 弃用告警。
- Web production build：1583 modules transformed，通过；CSS 22.39 kB，JS 303.28 kB。
- Fake Provider：合法补丁静态语义链通过；malformed JSON 生成 badcase 且保留 latency。
- 无密钥 CLI smoke：`run_status=blocked`，5 个样本未调用，生成 JSON/Markdown/CSV/badcases，返回非零状态。

### 待完成

- 无。Milestone 6 已完成，下一阶段需由用户确认范围。

### 框架验收

- `scripts/test-all.ps1`：通过。
- Python：137 passed，1 条既有 Starlette/httpx 弃用告警。
- Web：1583 modules transformed，production build 通过；CSS 22.39 kB，JS 303.33 kB。
- 浏览器：配置缺失、blocked 报告、空指标和四份产物路径展示正确；390px 无页面级横向溢出，控制台无错误。
- Unity：固定 seed 双跑、灵梦预览像素验证和 Placeholder 回退通过。
- 仓库清洁与旧来源 SHA256：通过。

### 真实 Provider 验收

- 用户已明确授权将选中的 C# 源码和 Prompt 发送到 `.env` 配置的外部服务。
- `.env` 已复制到新仓库并保持 Git 忽略；未打印或写入任何密钥值。
- 模型：`deepseek-v4-flash`；样本数：5。
- Provider、JSON、契约、安全、目标范围、质量审查和语义意图命中率：100%。
- 严格补丁应用率、应用后语义通过率、候选就绪率：60%。
- Badcases：2，均为 unified diff 上下文不准确导致的 `patch_apply` 拒绝；主仓库未修改。
- 总延迟：141,578 ms；Provider usage：19,842 total tokens。
- 新增离线 replay 后重算结果一致，未再次调用外部模型。
- Web Console 自动读取最近一次结果，浏览器显示指标与坏例正确，控制台错误为 0，无页面级横向溢出。
- 最终 `scripts/test-all.ps1` 退出码为 0：Python、Web、Unity、灵梦/Placeholder 和仓库清洁检查全部通过。

### 最终状态

`Milestone 6 complete。真实模型结果与 Milestone 5 scripted fixture 已分开记录；下一阶段必须另行确认范围。`
