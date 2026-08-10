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

## 2026-07-27 Milestone 7 启动

- 用户批准将项目主线收敛为面向 Unity 2.5D 弹幕玩法的 Game Change Verification Agent。
- 已确认配置变更优先、Training Sword 并行保留、固定轨迹加手动试玩、一次授权后隔离自动验证、Agent 选修复策略并由确定性工具调参。
- 已更新根路线图和各子系统 AGENTS 约束；当前进入 Milestone 7A。
- 新增 Bullet Hell 1.0 Pydantic 契约、基线配置、确定性需求映射、安全校验、Telemetry 评估和有限修复工具；定向测试 6 passed。
- 新增独立 Unity Bullet Hell 场景、四种 Pattern 计算、对象池、Boss 阶段、固定轨迹玩家和 Telemetry 记录模块。
- 首次 Unity batch build 被本机许可证令牌阻塞：日志为 `Access token is unavailable`，未生成 EXE；已记录并继续非 Unity 实现。
- 完成 Bullet Hell 工作流状态机、一次授权与三轮预算、baseline/candidate 双跑编排、有限修复动作、最终人工决策和工作流 artifacts。
- 新增 `/api/bullet-hell` 工作流、手动试玩、artifact、能力清单和 benchmark 接口。
- Web 策划视图默认进入“弹幕变更验证”，可直接切换 Mock/真实 Provider、设置超时、查看 Config Diff、授权、运行证据、修复历史和人工决策。
- 新增 20 样本离线工程回归；预期匹配、完整闭环、自动修复和危险需求拦截均为 100%，错误接受为 0，平均候选运行 1.308 次。该结果明确不代表真实 Unity 或真实模型质量。
- 新增 `scripts/smoke-bullet-hell.ps1`，能够识别 Unity 返回成功码但未生成 Player 的假成功，并执行固定 seed 双跑稳定字段比较。
- Python 全量测试：150 passed，1 条既有 Starlette/httpx 弃用告警。
- Web production build：1585 modules transformed，通过；CSS 24.65 kB，JS 328.30 kB。
- 浏览器 smoke：默认中文弹幕页、Provider/超时控件、Mock 候选、结构化目标、Config Diff、授权门和 artifact 链接均正常。
- 本地 API smoke：`/api/health`、Web 首页和 `/api/bullet-hell/capabilities` 均可访问。
- Unity 最终验收仍阻塞：Licensing Client 报告 `Access token is unavailable`、`0 free entitlements` 和 `No valid Unity Editor license found`，C# 编译与 Bullet Hell Player 双跑尚未得到证据。
- 同一 Unity smoke 已在受限环境外重试，仍在编译前被相同 Hub entitlement 问题阻断，排除本轮命令等待或端口占用。
- Unity 退出前曾把默认 Build Settings 改成仅 Bullet Hell；已收紧 Builder，使项目设置同时保留 RuntimeDemo 与 BulletHellDemo，而弹幕 Build 只显式构建自己的场景。
- 用户从 Unity Hub 打开项目后，日志成功识别 Unity Personal；修复 smoke 对瞬时 access-token warning 的误判，并在构建前删除旧 Player，防止复用陈旧 EXE。
- Bullet Hell C# 编译、Windows Player、固定 seed 双跑和逐阶段稳定字段全部通过；总子弹 592、峰值 66、受击 2、三个阶段结果一致。
- 修复工作流把 `status=failed` 的有效玩法 telemetry 错当作基础设施异常的问题；Player 非零退出但存在可用 telemetry 时继续进入 Evaluator 和自动修复。
- 自动模式从渲染帧 `Update()` 迁移到固定 60Hz `FixedUpdate()`；两次运行的总计和逐阶段玩法数据一致，真实 FPS 继续独立采集。
- 真实 Web/API 主案例完成 baseline + 3 次 candidate Unity 运行；两轮 `REDUCE_BULLET_SPEED` 后进入 `evidence_ready`，最终峰值 196、受击 0、生存 36 秒、低分位 FPS 约 58.8，并完成人工接受。
- 新增“加载最近验证”，刷新页面后可从磁盘恢复最新 workflow，不依赖数据库。
- 最终 Python：151 passed；Web production build 通过；Training Sword 固定 seed 回归重复率 100%。

### 最终状态

`Milestone 7 complete。当前版本可从 Web Console 执行配置提案、静态校验、人工授权、Unity 前后双跑、有限自动修复、证据展示和人工决策。`

## 2026-07-28 Milestone 7 UX

### 已完成

- 仅修改 Web 策划视图，新增默认新手模式、专业模式切换和浏览器持久化。
- 新增顶部安全演示说明、三个案例的中文结果预告、授权边界、只读最近演示和重新开始入口。
- 新增五步安全引导，可随时跳过；跳过或切换专业模式后刷新不再强制播放，设置中可主动重新查看。
- 新手模式将 Baseline/Candidate 显示为“修改前/修改后”，Mock 显示为“固定演示模型（免费、结果可重复）”；专业术语通过问号解释保留。
- 新增修改前/修改后人工试玩区；没有截图或录像时如实显示空状态，两个入口分别选择 `baseline_config.json` 与 `candidate_config.json`，不伪造媒体。
- 修复步骤圆圈被横向滚动容器裁剪的问题，并补充移动端布局和减少动画偏好。

### 验收

- Web production build：1585 modules transformed，通过；CSS 28.48 kB，JS 347.93 kB。
- 浏览器：模式切换跨刷新保留；跳过引导后刷新不重播；设置可重开引导。
- 浏览器：只读最近演示不运行模型或 Unity；两个试玩入口分别生成 Baseline/Candidate 快照命令。
- 桌面步骤圆圈完整；移动端实测 1～6 均为 24×24，全部位于进度容器内部，页面无横向溢出。
- 中英文步骤标签均可显示；浏览器缩放后圆圈仍完整位于进度容器内部。
- 浏览器控制台 warning/error：0。
- 后端、Unity、正式 baseline、workflow 状态定义与既有验收数据未修改。

### 最终状态

`Milestone 7 UX complete。策划视图已具备可持久化的新手/专业分级、可控引导和诚实的修改前后试玩证据入口。`

## 2026-07-28 Milestone 7 Visual

### 已完成

- Unity Bullet Hell 自动模式新增 10、20、30 秒截图序列和独立 `capture_manifest.json`。
- 新增工作流附加视觉证据服务；Baseline 与最终 Candidate 使用 seed `20260727`、固定轨迹、36 秒时长和固定正交相机依次运行。
- 新增 `visual_comparison.json`，记录状态、配置 SHA256、阶段、Pattern、时间点和截图文件。
- 新增自动画面对比与图片只读 API；图片路径、variant 和文件名均为服务端白名单。
- 新增受限手动启动 API，直接启动修改前或修改后快照，不再要求策划复制 PowerShell。
- Web 将证据明确分成自动截图、自动数据和真人手动体验三层；手动入口明确不作为严格比较。
- Web 并排展示三个相同时间点，并从真实 Config Diff 解释双向、每波数量和自动修复后速度变化。

### 真实证据

- 工作流：`bullet_20260728_111919_0485bf8c`。
- 视觉运行：Baseline/Candidate 均完成，六张 PNG 全部存在，随机种子、轨迹、时长、相机和阶段对齐。
- 第 20 秒：Baseline/Candidate 均为 phase_2、Boss 49%；截图内存活子弹约 52/172，双向螺旋差异明显。
- Web：六张图片全部加载，broken image 为 0；375px 移动端无页面级横向溢出。
- 手动入口：修改前和修改后均从页面成功启动固定 Unity Player；测试后已关闭 Player。
- API：PNG 返回 `200 image/png`；路径穿越请求 404，未知 variant 409。

### 回归

- Python：153 passed，1 条既有 Starlette/httpx 弃用告警。
- Web production build：1585 modules transformed；CSS 29.75 kB，JS 353.17 kB。
- Unity：Training Sword 固定 seed、灵梦/Placeholder 表现 smoke、Bullet Hell C# Build 和固定 seed 双跑全部通过。
- 仓库清洁与旧来源不可变检查通过。

### 最终状态

`Milestone 7 Visual complete。当前页面能用同条件截图回答“改了什么”，用 telemetry 回答“是否达标”，再用手动试玩补充主观体验。`

## 2026-07-31 Milestone 8 审计

### 已完成

- 读取 Milestone 8 UE5 跨引擎扩展要求，确认本轮必须以真实 UE5 Build、Player、Telemetry 和截图为完成标准。
- 审计 Git：当前分支 `main`，最近提交 `fd0a772`；11 个 Milestone 7 Visual 文件尚未提交，因此未创建功能分支。
- 定位现有 Unity 启动、配置读取、Telemetry、截图、工作流、API 和 Web 页面代码。
- 核对正式 Bullet Hell 1.0 契约，确认 UE5 必须读取同一字段，不创建平行 Schema。
- 检查本机环境：未发现 UE5；Visual Studio 2022 Build Tools、MSVC 14.44、Windows SDK 10.0.26100.0 和 MSBuild 已存在。
- 更新 Milestone 8A–8D 计划、预计修改文件和阻塞条件。

### 本轮真实基线

- Python：`153 passed`，1 条既有 Starlette/httpx 弃用告警。
- Web：production build 通过，`1585 modules transformed`，CSS 29.75 kB，JS 353.17 kB。
- Unity：本轮重建失败，原因是 Hub access token/entitlement 未传递给 batchmode；没有生成新的 `BulletHellDemo.exe`。
- Unity 历史证据：2026-07-28 baseline telemetry 为总子弹 592、峰值 66、受击 2、36 秒完成、低分位 FPS 58.73；该数据未冒充本轮复测结果。
- UE5：未安装，未创建工程、未编译、未运行、无 Telemetry、无截图。

### 当前状态

`Milestone 8 blocked。等待用户安装/选择 UE5 版本，并从 Unity Hub 打开当前 Unity 项目恢复批处理许可证；随后先冻结 Milestone 7 成功基线，再创建 feature/ue5-runtime-adapter 分支实施。`

### Unity Hub 复测

- 用户已从 Unity Hub 打开并关闭 `game-unity`，随后重新执行 `scripts/smoke-bullet-hell.ps1`。
- Unity Editor batchmode 在 300 秒后超时；`build.log` 显示 Licensing Client IPC 连续重连失败，并多次等待 60 秒。
- 本次仍未进入有效 Windows Build，也未生成新的 Player；问题属于本机 Hub/批处理许可证会话阻塞，不是端口占用或已确认的 C# 编译错误。
- Milestone 7 的 2026-07-28 真实运行证据继续保留，但不得冒充 2026-07-31 的新复测结果。

## 2026-07-31 Milestone 8A 实现

### 已完成

- 将 Milestone 7 Visual 冻结为本地提交 `fd7aa55`，创建 `feature/ue5-runtime-adapter` 分支。
- 主弹幕闭环新增独立 `RequirementAgent` 与 `QualityReviewAgent`；两者使用不同 Prompt、输入输出契约和 `agent_runs.json` 证据。
- Quality Review Agent 只输出接受、有限修复或人工复核意图；建议必须通过确定性策略门，数值仍由原 `apply_repair` 工具计算。
- 新增 Schema、引用、规则引擎和安全门四层候选校验；越权修改 Boss 等非允许字段会被阻断。
- 新增统一 `EngineRunner` 接口、`UnityEngineRunner`、跨引擎规范化 Telemetry 包装和诚实的 UE 不可用状态。
- `POST /api/bullet-hell/workflows` 新增可选 `engine` 字段，省略时仍默认 `unity`。

### 验收

- 双 Agent/四层校验/EngineRunner 定向测试：`22 passed`。
- Python 全量：`162 passed`，1 条既有 Starlette/httpx 弃用告警。
- Web production build：`1585 modules transformed`，CSS 29.75 kB，JS 353.17 kB。
- Unity 真实复测仍受 Licensing Client IPC 阻塞；本轮没有新增 Unity Build 或运行证据。
- UE5 尚未安装完成，`UnrealEngineRunner` 只报告 `unavailable`，没有伪造 Build、Telemetry 或截图。

### Web 与叙事收口

- Web 策划页新增 Unity 6 / Unreal Engine 5 选择；默认仍为 Unity，并显示 Runner 的真实状态和原因。
- UE 未安装时可以生成静态候选，但授权后运行按钮保持禁用，无法越过环境安全门。
- 新增 Agent 分工证据区，显示 Requirement Agent、Quality Review Agent、Provider、Prompt、延迟和确定性策略门结果。
- 项目对外名称、后端健康版本和启动脚本统一为 `Game Change Verification Agent`。
- 新增 `docs/RESUME_NARRATIVE_EVIDENCE_MATRIX.md`，逐项区分已真实验证、仅代码/测试完成和未完成的 UE 主张。
- 浏览器实测 Unreal 状态、静态候选、Requirement Agent 证据和禁用运行按钮正确，桌面页面无横向溢出；移动视口截图被浏览器本地页面安全策略中止，未绕过。
- 定向 Python：`24 passed`；Web production build：`1585 modules transformed`，CSS 30.85 kB，JS 359.73 kB。

### Milestone 8A 收口回归

- 修复引擎能力加载期间的运行按钮短暂可用问题；只有后端明确返回 `available` 或 `verified` 时才允许启动引擎运行。
- Python 全量：`162 passed`，1 条既有 Starlette/httpx 弃用告警。
- Web production build：`1585 modules transformed`，CSS 30.85 kB，JS 359.73 kB。
- 当前简历可验证口径固定为：Unity 闭环已真实验证；有界双 Agent、四层确定性校验和 EngineRunner 已实现并测试；UE5 真实 C++ Player 与跨引擎运行证据待安装完成后补齐。

## 2026-07-31 Milestone 8 完成

### 已完成

- 用户已安装 UE `5.8.1-56057345+++UE5+Release-5.8`，真实工程位于 `game-unreal/BulletHellUE/`。
- `scripts/build-unreal.ps1` 完成 UE5 C++ Windows Player 打包，`scripts/smoke-unreal.ps1` 完成真实 Baseline/Candidate 双跑。
- C++ 接受 `baseline` 与任意 `candidate*` variant，修复多轮候选 `candidate_1/2` 无法运行的问题；Runner 侧统一将 `candidate_1` 等规范化为 verification 的 `candidate`。
- 最新 smoke：`runtime-artifacts/ue5-verification/ue5_smoke_20260731_231202/`，`verification_manifest.json` 状态为 `verified`。
- UE Baseline/Candidate 均使用同一 Player、seed `20260727`、固定轨迹、36 秒时长和 10/20/30 秒截图；Telemetry、配置哈希、截图、日志与 `comparison_report.json` 全部通过校验。
- 真实 Web/API workflow：`bullet_20260731_230825_8c13b17d`，`engine=unreal`，`status=evidence_ready`，`runs_used=1`，所有 runtime target 通过。
- 该 workflow 已生成 `visual_comparison.json`：Baseline/Candidate 各 3 张截图，10/20/30 秒对应 phase_1/phase_2/phase_3；20 秒和 30 秒人工核验可见单向螺旋与双向螺旋差异，画面非黑屏。
- `UnrealEngineRunner` 当前返回 `verified`；Web 策划页可切换 Unity / Unreal，未就绪时仍禁用运行按钮。
- 更新 `docs/MILESTONE8_UE5_CROSS_ENGINE_VERIFICATION.md`、`docs/RESUME_NARRATIVE_EVIDENCE_MATRIX.md`、README、AGENTS 和规划记录，UE 简历主张逐项转为已真实验证。

### 最终证据

最新 UE5 smoke 指标：

| 指标 | Baseline | Candidate |
|---|---:|---:|
| total_bullets_spawned | 592 | 992 |
| peak_alive_bullets | 70 | 192 |
| player_hits | 1 | 0 |
| player_survival_seconds | 36 | 36 |
| average_fps | 59.6563 | 59.8583 |
| low_percentile_fps | 59.8874 | 59.9995 |
| minimum_fps | 20.5058 | 21.6646 |
| runtime_error_count | 0 | 0 |

### 回归

- Python 全量：`164 passed`，1 条既有 Starlette/httpx 弃用告警。
- Web production build：`1585 modules transformed`，通过。
- UE5 C++ Build、Baseline/Candidate 双跑、Telemetry、截图和 verification manifest：通过。
- Unity 2026-07-31 新复跑仍受本机 Licensing Client IPC 阻塞；Milestone 7 历史真实证据保留，不作为本轮 Unity 复测。
- `runtime-artifacts/` 与 UE 构建缓存目录均不入库，最终提交只包含源码、脚本、测试和文档。

### 最终状态

`Milestone 8 complete。真实 UE5 跨引擎验证链路已完成，Unity 原闭环保持可用；下一阶段按用户确认的简历叙事统一收口并提交本分支。`

## 2026-08-05 Milestone 8 Hotfix

- 已定位 UE 手动试玩不可见、假成功、残留进程和 Blueprint 未 Cook 四项根因。
- 已将 `-RenderOffscreen` 限定为自动运行，手动模式保留可见窗口参数。
- 已增加 UE 初始化日志握手；早退和超时不再返回 `launched`。
- 已让手动模拟结束后请求正常退出，并显式 Cook BulletHellDemo Map 与 Presentation 目录。
- 新增手动可见窗口、早退失败、自动离屏和打包配置回归测试。
- 定向测试：`19 passed`，1 条既有 Starlette/httpx 弃用告警。
- Python 全量：`167 passed`，1 条既有 Starlette/httpx 弃用告警；Web production build 通过，`1585 modules transformed`。
- UE5 C++ Windows Build 通过；最新真实自动 smoke 为 `runtime-artifacts/ue5-verification/ue5_smoke_20260805_143608/`，Baseline/Candidate 均正常结束且运行错误为 0。
- 新包日志未出现 `/Game/Presentation/BP_*` 缺失；受限手动启动已取得 `Bullet Hell run initialized` 握手，进程 `10316` 在角色死亡后通过 `RequestExitWithStatus(0)` 正常退出。
- 当前只剩用户从 Web 策划视图进行一次可见窗口与键盘操作确认；在此之前 Hotfix 保持 `in_progress`。
- 修复 UE 玩法坐标到世界坐标的垂直镜像：玩家、Boss 和子弹统一通过 `SimulationToWorld` 映射，模拟层、固定轨迹、碰撞和 Telemetry 不变。
- 重新完成 UE5 Windows Build；最新自动双跑 `ue5_smoke_20260805_150744` 为 `verified`，Baseline/Candidate 运行错误均为 0，自动截图确认 Boss 在上、玩家在下。
- 已启动修复后的可见手动 Player（PID `34316`）供用户确认 `W=屏幕向上`、`S=屏幕向下`。

## 2026-08-10 GitHub Release

- 完成公开发布前目录、Git、依赖、测试、敏感信息、体积和忽略规则只读审计。
- 在仓库外创建回退 bundle：`D:\Desktop\game-change-verification-agent-pre-public-20260810.bundle`，该文件不进入发布仓库。
- 将 14 个历史提交的 author/committer 邮箱统一改为 GitHub noreply，并同步重写 `main` 与 `feature/ue5-runtime-adapter`。
- 将 `source-manifest.json` 升级为公开 Schema 1.1，215 个条目只保留来源名称、相对路径和 SHA256；所有历史提交均无本机绝对来源路径。
- 参数化 `generate-source-manifest.ps1` 的本地来源输入，更新 `verify-repo-clean.ps1` 以验证公开清单结构和路径安全。
- 重写中文 README，补充架构、边界、Quick Start、真实指标以及 UE/Web 真实截图；统一 Python 与 Web 公开包名。
- 将 Unity/UE 编辑器位置改为 `GAMECHANGE_UNITY_EDITOR` / `GAMECHANGE_UE_EDITOR` 或显式脚本参数，清理当前权威文档中的旧项目绝对路径。
- 回归通过：Python `167 passed`、Web production build、UE5 smoke `ue5_smoke_20260810_233045`、`verify-repo-clean.ps1`、浏览器策划视图只读演示与无错误日志检查。
- 历史复核：14 个提交邮箱全部正确、历史 manifest 绝对路径为 0、高置信度密钥命中为 0；382 个跟踪文件无超过 10 MiB 的文件。
- 已完成发布前本地整理并准备 A-K 汇总；尚未 `git add`、提交发布整理、创建远程仓库或 Push，等待用户确认。
- 用户确认后创建两次真实提交：`24e3a23 fix: 修复 UE5 手动试玩与方向映射`、`5625756 chore: 整理 GitHub 公开发布内容`。
- 将 `feature/ue5-runtime-adapter` 快进合并到 `main`，创建公开仓库 `theHerta27/game-change-verification-agent` 并成功推送 `main`。
- GitHub Description 与 10 个 Topics 已按公开发布方案设置；License 继续保持未添加。
