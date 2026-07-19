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
