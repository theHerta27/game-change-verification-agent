# Milestone 6：真实 Provider 代码生成评测

## 1. 目标

Milestone 5 的 100% 是脚本化护栏测试，不是模型成绩。Milestone 6 单独调用 OpenAI Compatible Provider，评估真实模型能否针对指定 Unity C# 源文件生成满足需求的候选 Diff。

当前数据集只有 5 个小型防御式改动：

1. `RuntimeRunSettings.FromArgs` 的 args 空值保护。
2. `CombatRangePolicy.IsInRange` 的负数 range 防护。
3. `GameConfigLoader.Load` 的空白配置文本防护。
4. `RuntimeVisualPulse.Configure` 的 NaN/Infinity 防护。
5. `--seed` 的 `InvariantCulture` 解析。

这些需求不新增玩法，不要求模型浏览仓库，也不修改 Unity contract。

## 2. 完整评测链

```text
固定需求与目标文件
-> OpenAI Compatible Provider
-> JSON Parse
-> Generation Contract
-> Target Scope Validation
-> Patch Safety Gate
-> Quality Review Agent
-> 基线源码 + Diff 的语义意图断言
-> 临时目录精确应用补丁
-> 应用后源码的固定语义断言
-> candidate_ready / badcase
```

`candidate_ready=true` 只表示静态链路通过，候选仍停在人工审批前。它不等于：

- C# 已编译；
- Unity 已启动；
- 固定种子自动试玩已通过；
- 玩家体验或数值效果已验证；
- 补丁可以自动合并。

## 3. 数据与 Prompt 固定

- Dataset：`evals/real_code_generation_v1.json`
- Dataset ID：`real_code_generation_v1`
- Prompt：`gameconfig_agent/prompts/code_change_generator.md`
- 报告记录 dataset SHA256 和 prompt SHA256。

每个样本包含 `requirement_text`、显式 `target_files` 和语义检查。例如负数攻击范围要求同时保留 `PlanarDistance`、出现负值判断并返回 `false`。

语义断言是固定正则证据，只能验证关键实现意图，不是完整程序证明。

系统区分两个语义指标：

- `semantic_intent_pass_rate`：在“基线源码 + 模型 Diff”中能否找到需求关键证据，用于判断模型是否理解了修改意图。
- `semantic_requirement_pass_rate`：补丁被严格应用后，候选源码是否满足同一组语义断言。

前者通过不代表补丁可用。模型可能写对代码内容，却给出错误的 unified diff hunk 行号或上下文；此时严格应用器仍必须拒绝。

## 4. 环境变量

在仓库根目录创建 `.env`：

```text
GAMECONFIG_LLM_BASE_URL=https://your-provider.example/v1
GAMECONFIG_LLM_API_KEY=replace_me
GAMECONFIG_LLM_MODEL=your-model
```

可以从 `.env.example` 开始。`.env` 已被 Git 忽略，不能提交，也不会写入报告。系统只报告变量是否存在，不返回变量值。

## 5. CLI

```powershell
cd <repository-root>\services\agent-python
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli run_real_code_evaluation `
  --output ..\..\runtime-artifacts\real-code-evaluation `
  --timeout-seconds 60
```

已有真实输出可以离线重放，不再次调用外部模型：

```powershell
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli replay_real_code_evaluation `
  --output ..\..\runtime-artifacts\real-code-evaluation
```

未配置 Provider 时：

- 返回非零 exit code；
- `run_status=blocked`；
- 不发生模型调用；
- 仍生成配置失败 badcase 和报告；
- 所有比率为 `null`，不能解释为模型 0 分。

## 6. API 与 Web

```text
GET  /api/code-change-agent/real-evaluation/config
GET  /api/code-change-agent/real-evaluation/dataset
GET  /api/code-change-agent/real-evaluation/latest
POST /api/code-change-agent/real-evaluation
POST /api/code-change-agent/real-evaluation/replay
```

Web Console 的“真实模型代码生成评测”只位于开发者视图，与“代码变更护栏评测”分开。按钮在配置缺失时生成阻塞报告，配置齐全时会执行 5 次真实调用。

## 7. 指标

- `provider_call_success_rate`
- `json_parse_success_rate`
- `generation_contract_pass_rate`
- `patch_safety_pass_rate`
- `target_scope_pass_rate`
- `quality_review_pass_rate`
- `patch_apply_success_rate`
- `semantic_intent_pass_rate`
- `semantic_requirement_pass_rate`
- `candidate_ready_rate`
- `badcase_count`
- `failure_stage_distribution`
- `latency_ms`
- `usage` 或 `token_estimate`
- `repository_unchanged`

## 8. 产物

```text
runtime-artifacts/real-code-evaluation/
├── real_code_evaluation.json
├── evaluation_report.md
├── badcases.md
├── sample_summary.csv
└── sample_runs/
```

运行产物不提交 Git。真实模型原始脏输出只进入本地 badcase 证据。

## 9. 首次真实运行结果

- Provider：`openai_compatible`
- Model：`deepseek-v4-flash`
- 样本：5
- Provider / JSON / Contract / Safety / Quality Review：均为 100%
- 语义意图命中率：100%
- 严格补丁应用率：60%
- 应用后语义通过率：60%
- 候选就绪率：60%
- Badcases：2，均为 `patch_apply`
- 总延迟：141,578 ms
- Provider usage：19,842 total tokens
- 主仓库未修改：`true`

两个失败样本分别是负数攻击范围防护和固定文化 seed 解析。模型生成的关键 C# 语义正确，但 unified diff hunk 行号与真实源文件不一致。系统保留坏例并拒绝候选，没有放宽补丁安全规则。后续优化方向应是结构化编辑或由工具根据结构化修改生成 diff，而不是让模型输出不受校验的文本补丁。
