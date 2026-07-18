# GameConfig Agent 初学者端到端理解指南

## 1. 先理解这个项目在做什么

这个项目不是“让大模型直接写一份 JSON，然后相信它”。它要解决的是一条游戏研发工作流：

```text
策划描述目标
-> Agent 生成候选配置
-> 确定性工具检查配置
-> Agent 解释和修复问题
-> 保存最终配置快照
-> Unity 读取这份配置并运行
-> Unity 记录真实运行数据
-> Python 比较策划目标与实测结果
-> 页面显示风险和改进建议
```

核心思想是把“模型擅长的模糊理解”和“程序擅长的精确判断”分开：

- LLM/Agent 负责理解文字、提出配置、解释问题和给出修复方案。
- Validator/Rule Engine 负责可以精确计算的规则，不能被模型的自信回答替代。
- Unity 负责证明配置在游戏运行时到底产生了什么结果。
- Web Console 负责把整个过程组织成策划和开发者都能理解的操作流程。

## 2. 先认识最重要的术语

### 进程

进程是正在运行的程序。这个项目至少有三个进程：

1. FastAPI 后端进程：运行 Python 业务逻辑。
2. Vite 前端进程：把 React 页面提供给浏览器。
3. Unity Player 进程：真正运行可玩的测试关卡。

关闭启动某个进程的 PowerShell 窗口，通常也会停止该进程。

### HTTP API

浏览器不能直接调用 Python 函数。前端通过 HTTP 请求后端，例如：

```text
POST /api/runs/demo
```

`POST` 表示提交数据，`GET` 表示读取数据。请求和响应主要使用 JSON。

### JSON

JSON 是跨语言传输结构化数据的文本格式。Python、TypeScript 和 C# 都能读取它。

```json
{
  "weapon_id": "weapon_training_sword",
  "base_attack": 50
}
```

JSON 语法正确不等于业务正确。`base_attack` 可以是合法数字，但数值可能不平衡；`upgrade_config` 可以是合法对象，但项目契约要求它必须是数组。

### Schema

Schema 是数据结构契约，规定有哪些字段、字段是什么类型。例如：

```text
weapon_config 必须是数组
每一行必须有 weapon_id、item_id、weapon_type、base_attack、strength_tier
base_attack 必须是整数
```

### Reference

Reference 是跨表引用。例如升级表写了 `item_refine_stone`，物品表就必须存在同 ID 的物品定义。

### Rule

Rule 是确定性业务规则。例如：

- 升级等级必须连续为 1、2、3。
- Gold 消耗不能为 0 或负数。
- 新手首通奖励必须 `once_only=true`。

### Artifact

Artifact 是一次处理产生、可以保存和检查的文件，例如最终配置、trace、telemetry 和报告。

### run_id

`run_id` 是一次 Unity 验证的唯一编号。每次点击“准备本次 Unity 测试”都会创建新目录，旧目录不会自动覆盖。

## 3. 项目如何启动

### 后端入口

运行：

```powershell
cd D:\Desktop\GameConfig-Agent
.\scripts\start_backend.ps1
```

脚本最终执行：

```text
python -m uvicorn gameconfig_agent.server:app --host 127.0.0.1 --port 8000
```

调用关系是：

```text
scripts/start_backend.ps1
-> uvicorn
-> 导入 gameconfig_agent/server.py
-> 找到 app = create_app()
-> 开始监听 http://127.0.0.1:8000
```

`127.0.0.1` 表示只允许本机访问，不是部署到互联网。

### 前端入口

另开一个 PowerShell 窗口运行：

```powershell
cd D:\Desktop\GameConfig-Agent
.\scripts\start_frontend.ps1
```

调用关系是：

```text
scripts/start_frontend.ps1
-> Vite
-> frontend/index.html
-> frontend/src/main.tsx
-> React 创建页面
```

浏览器打开 `http://127.0.0.1:5173`。Vite 会把以 `/api` 开头的请求转发给 8000 端口的 FastAPI。

## 4. “标准新手试炼关卡”从哪里开始

页面加载后，`frontend/src/main.tsx` 首先请求：

```text
GET /api/classic-cases
```

后端 `gameconfig_agent/server.py` 调用 `list_classic_cases()`，读取 `gameconfig_agent/data/classic_cases.py` 中的注册表。

默认案例是：

```text
case_01_baseline_trial
```

它的详细文字保存在：

```text
examples/classic_cases/case_01_baseline_trial.md
```

经典案例固定的是“需求方向和验收目标”，不是固定伪造的 Unity 结果。

## 5. 点击“生成并校验当前需求”后发生什么

前端 `runDemo()` 发送：

```text
POST /api/runs/demo
```

请求大致是：

```json
{
  "requirement_text": "设计一个 Training Sword 新手试炼关卡……",
  "provider": "openai_compatible",
  "timeout_seconds": 60
}
```

后端入口是 `gameconfig_agent/server.py` 中的 `run_demo()`。

### Mock 模式

Mock 模式调用 `gameconfig_agent/cli.py` 的 `run_phase0_demo()`。它依次执行：

```text
ConfigGeneratorAgent
-> SchemaValidatorTool
-> ReferenceCheckerTool
-> RuleEngineTool
-> ConfigReviewerAgent
-> ConfigRepairAgent
-> Final Validation
-> TestScenarioAgent
```

Mock 的 Generator、Reviewer 和 Repairer 是确定性代码，结果稳定，适合自动测试。它不代表真实语言理解能力。

### 真实 Provider 模式

真实模式通过 `gameconfig_agent/providers/openai_compatible.py` 调用 `.env` 配置的 Chat Completions 接口。

`gameconfig_agent/real_run.py` 中的 `RealRunPipeline.run()` 依次执行四次模型任务：

1. `generator.md`：生成结构化需求和草案配置。
2. `reviewer.md`：阅读校验错误并解释风险。
3. `repairer.md`：返回完整修复后配置。
4. `test_scenario.md`：生成配置测试场景。

每次模型输出先经过 `json.loads()`。能解析后还要经过 Schema、Reference 和 Rule 校验。

Web 的单次按钮只处理当前需求，`sample_count=1`。CLI 的 `run_real_demo` 才会追加三个固定样本做小规模评测。

## 6. 为什么真实模型可能“JSON 成功但 Schema 失败”

下面两份数据都是合法 JSON：

```json
{"upgrade_config": {"level": 1}}
```

```json
{"upgrade_config": [{"level": 1}]}
```

但项目要求 `upgrade_config` 是数组，因此第一份会被拒绝。

这就是为什么系统需要多层质量门禁：

```text
JSON Parse：是不是合法 JSON
Schema：结构和字段是否符合约定
Reference：跨表 ID 是否存在
Rule：是否违反明确业务规则
Final Validation：修复后是否全部通过
```

模型失败不会 traceback 崩溃，而会写入 badcase，记录 provider、model、阶段、错误路径和原始输出。

## 7. 真实模型生成的文件在哪里

真实 Provider 的最近一次生成结果保存在：

```text
outputs/phase2/real_run_result.json
outputs/phase2/real_run_trace.json
outputs/phase2/real_run_report.md
outputs/phase2/badcases.md
```

`outputs/phase2` 是“最近一次真实生成/评测”的共享输出位置，下一次运行会更新这些文件。

其中真正准备交给 Unity 的候选配置位于：

```text
real_run_result.json
-> results[0]
-> repaired_configs
```

它通过最终校验后，还没有自动成为 Unity 本次运行文件。必须再点击“准备本次 Unity 测试”，把它保存成不可混淆的 run 快照。

## 8. 点击“准备本次 Unity 测试”后发生什么

前端发送：

```text
POST /api/runtime-runs
```

Mock 请求只需要 requirement 和 provider。真实 Provider 请求还会携带本次：

```text
structured_requirement
repaired_configs
model
```

后端 `gameconfig_agent/runtime_runs.py` 的 `RuntimeRunService.prepare()` 会：

1. 确认案例允许 Unity 运行。
2. 对真实配置重新执行 Schema、Reference、Rule 校验。
3. 生成唯一 `run_id`。
4. 保存需求快照 `requirement.txt`。
5. 保存最终配置快照 `final_configs.json`。
6. 计算 `config_hash`，证明后续测试使用的是哪份配置。
7. 调用 `build_runtime_contract()` 生成 Unity 能读取的 `unity_contract.json`。
8. 写入状态机文件 `run_manifest.json`。

一次准备完成后目录类似：

```text
outputs/runtime_runs/run_20260714_151911_c1c750b0/
  requirement.txt
  final_configs.json
  unity_contract.json
  run_manifest.json
```

此时状态是 `prepared`，只表示文件准备好了，Unity 尚未启动。

## 9. 为什么同一分钟可能有两个 run 目录

每点击一次“准备本次 Unity 测试”，系统都会创建新 `run_id`。这是为了保留历史证据，而不是覆盖上一轮。

当前两个目录的含义是：

```text
run_20260714_151905_90139d42
provider = mock
status = prepared
```

它只完成了准备，没有启动 Unity。

```text
run_20260714_151911_c1c750b0
provider = mock
status = evaluated
mode = auto
```

它完成了自动 Unity 运行、telemetry 和评测。

目录名时间使用 UTC，因此 `151911` 对应中国时间约 `23:19:11`。Windows 文件时间显示本地时区，所以相差 8 小时是正常的。

两个 run 的 config hash 相同，表示配置内容相同；但它们仍是两次不同运行。第一个未完成目录可以保留作为状态机证据，也可以以后增加显式清理功能。

## 10. 点击“打开 Unity 手动试玩”后发生什么

前端发送：

```text
POST /api/runtime-runs/{run_id}/launch
{"mode": "manual"}
```

`RuntimeRunService.launch()` 只允许启动项目内固定的：

```text
unity/GameConfigRuntimeDemo/Builds/Windows/GameConfigRuntimeDemo.exe
```

后端实际构造的命令类似：

```text
GameConfigRuntimeDemo.exe
--config-input outputs/runtime_runs/{run_id}/unity_contract.json
--telemetry-output outputs/runtime_runs/{run_id}/telemetry.json
```

这两个参数把“输入配置”和“输出数据”都绑定到同一个 run。

Unity 中 `GameConfigLoader.cs` 读取 `--config-input`，将 JSON 反序列化为 C# 数据对象。

`RuntimeDemoBootstrap.cs` 负责：

- 创建测试场地、玩家、敌人和摄像机。
- 从配置读取武器攻击力和升级成本。
- 从 runtime scenario 读取玩家、技能、敌人和波次。
- 接收 WASD、Space、Q、U 输入。
- 统计攻击、技能、伤害、击杀、金币、升级和通关时间。

手动模式必须完成三波战斗。正常完成后 `Finish("completed")` 自动把 telemetry 写到后端指定路径。

如果直接关闭 Unity 且尚未写出 telemetry，后端会记录 `UnityProcessExited`，不会伪造成功结果。

## 11. “运行 Unity 自动回归”有什么不同

自动模式会多传一个参数：

```text
--auto-run
```

Unity 使用 `UpdateAutoPlayer()` 自动靠近最近敌人、攻击和使用技能。完成后自动退出。

自动模式适合：

- 回归测试。
- 检查配置和运行契约是否能跑通。
- 稳定采集一组可重复 telemetry。

手动模式适合：

- 感受操作、节奏和可读性。
- 观察玩家真实行为。
- 发现自动脚本无法代表的体验问题。

两者不是互相替代，而是解决不同问题。

## 12. Unity 完成后数据会自动回来吗

会，但“回来”不是 Unity 主动调用网页，而是通过共享文件和轮询完成。

前端每 1.5 秒请求：

```text
GET /api/runtime-runs/{run_id}
```

后端检查本次目录：

1. 如果 Unity 还在运行，返回 `launched`。
2. 如果发现 `telemetry.json`，自动调用 `evaluate()`。
3. `runtime_evaluation.py` 比较 telemetry 和 Unity Contract 中的 targets。
4. 生成评测和建议。
5. 更新 manifest 为 `evaluated`。
6. 前端下一次轮询拿到结果，停止转圈并显示表格。

完成后的目录会增加：

```text
telemetry.json
runtime_evaluation.json
runtime_evaluation_report.md
improvement_suggestions.json
```

因此完整闭环是：

```text
HTTP 请求创建 run
-> 后端启动 Unity 进程
-> Unity 读 JSON
-> Unity 写 telemetry JSON
-> 后端轮询文件并评测
-> 前端轮询后端并更新页面
```

## 13. 策划目标与 Unity 实测如何比较

`unity_contract.json` 包含两类数据：

```text
configs：武器、升级、奖励等策划配置
runtime_scenario：玩家、技能、敌人、波次和验收目标
```

`telemetry.json` 保存实际发生的数据，例如：

```text
completion_time_seconds
enemies_defeated
basic_attacks
skill_uses
gold_earned
gold_spent
```

Runtime Evaluator 做的是普通确定性比较：

```text
60 <= completion_time_seconds <= 90 ?
enemies_defeated == 5 ?
skill_uses >= 1 ?
第一次升级能否支付 ?
第二次升级是否仍可支付 ?
```

这部分不应该交给 LLM 猜，因为代码可以得到唯一答案。

## 14. Agent 在这条链路中到底做了什么

不要把整个系统都理解成“大模型自己运行游戏”。

当前 Agent 主要负责：

- Generator：把文字需求转换成候选结构。
- Reviewer：根据工具错误解释风险。
- Repairer：根据约束修改候选配置。
- Test Scenario Agent：生成需要验证的测试场景。

Agent 不负责：

- 判断 JSON 数组是否合法：Schema Validator 负责。
- 计算引用是否存在：Reference Checker 负责。
- 判断升级等级是否连续：Rule Engine 负责。
- 操作 Unity 角色：玩家或自动脚本负责。
- 判断 16 秒是否满足 60–90 秒：Runtime Evaluator 负责。

工程化 Agent 的关键不是“自主程度越高越好”，而是让不确定能力被确定性工具、状态和证据约束。

## 15. 如果你自己从零写，应该按什么顺序

不要一开始就写多智能体。建议按以下顺序：

1. 先定义 JSON Schema：系统究竟接受什么数据。
2. 写 Validator：给脏数据也不能崩溃。
3. 写一份手工合法配置，证明 Unity 可以读取。
4. 写 telemetry，证明 Unity 能导出运行结果。
5. 写 Runtime Evaluator，把目标和实测比较。
6. 写文件状态机，用 run_id 隔离每次运行。
7. 写 FastAPI，把这些 Python 函数包装成 HTTP 接口。
8. 写 React 页面，把接口组织成操作流程。
9. 最后接 LLM，让它只负责生成和解释不确定部分。
10. 建立 badcase 和 benchmark，持续改进 prompt、规则和数据集。

这个顺序体现一个工程原则：先建立可验证的地基，再引入不稳定的模型能力。

## 16. 你现在应该怎样操作完整真实流程

修改后必须先重启后端和前端，因为旧进程不会自动加载全部 Python 改动。

1. 在后端窗口按 `Ctrl+C`，重新运行 `scripts/start_backend.ps1`。
2. 在前端窗口按 `Ctrl+C`，重新运行 `scripts/start_frontend.ps1`。
3. 打开 `http://127.0.0.1:5173`。
4. 选择“标准新手试炼关卡”。
5. Provider 选择真实模型。
6. 点击“生成并校验当前需求”。
7. 确认 JSON、Schema、Final Validation 全部通过。
8. 点击“准备本次 Unity 测试”。
9. 检查页面显示的新 `run_id`，其 manifest 应为 `provider=openai_compatible`。
10. 选择“打开 Unity 手动试玩”或“运行 Unity 自动回归”。
11. 手动模式下完成三波，不要中途关闭窗口。
12. 回到 Web Console，页面会自动轮询并显示评测与建议。

这时 `outputs/runtime_runs/{new_run_id}` 中的 `final_configs.json` 才是本次真实模型配置的 Unity 测试快照。

## 17. 当前系统仍然有哪些边界

- Unity Demo 目前只消费武器、升级、奖励和固定试炼场景，不代表完整商业游戏配置系统。
- 真实模型通过 Schema 不代表配置一定好玩，必须继续看 Unity telemetry 和人工试玩。
- 当前自动玩家是确定性脚本，不代表真实玩家分布。
- 当前 runtime scenario 仍包含固定敌人与技能基线，后续才能逐步配置化。
- `outputs/phase2` 保存最近一次真实生成，而 `outputs/runtime_runs` 才保存每次不可混淆的运行证据。
- 当前没有数据库和用户系统，适合本地原型和面试演示，不是多人生产环境。

理解这些边界不是项目的缺点，而是正确说明“当前已经证明什么、还没有证明什么”。

## 18. 如果用户输入和 Schema 完全无关

符合 Schema 只证明数据结构合法，不证明模型理解了原始需求。当前 Mock 会继续生成固定 Training Sword；真实模型可能拒绝，也可能把“讲一个笑话”等无关请求强行套入武器配置。

正确方向是在 Generator 前增加 Requirement Intake / Scope Gate，把输入分成：

- `accepted`：属于当前支持的配置需求。
- `needs_clarification`：与配置有关，但缺少信息或存在冲突。
- `rejected`：属于美术、叙事或完全无关任务。

正常拒绝和澄清不是 badcase。系统错误接受无关需求、丢失明确约束或输出脏结构才是 badcase。

详细讨论、示例和 Milestone 8 优先级见：

```text
docs/REQUIREMENT_BOUNDARIES_AND_NEXT_STEPS.md
```
