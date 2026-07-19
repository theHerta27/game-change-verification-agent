# Milestone 5：代码变更 Benchmark 与失败分类

状态：已完成。最终验收为 Python 130 passed、Web production build 通过、浏览器 12 样本实跑通过、Unity 与仓库完整回归通过。

## 1. 为什么先评测护栏

Milestone 4 已经允许真实 Provider 基于最多 3 个指定 C# 文件生成候选 Diff，但“模型返回了一段代码”不等于“系统可以安全采用它”。在继续扩大能力前，需要先回答：

1. 无关需求能否在调用模型前被拒绝。
2. 模型输出不是约定 JSON 时能否留下 badcase。
3. 模型声明或实际修改未授权文件时能否被阻断。
4. 新建文件、进程启动等危险补丁能否被安全门拒绝。
5. 合法候选能否进入既有质量审查，同时仍停在人工审批前。

因此本阶段评测的是**工程护栏与失败路由**，不是自然语言理解或真实模型代码能力。

## 2. 数据集

数据集位于：

```text
evals/code_change_benchmark_v1.json
```

`dataset_id` 为 `code_change_guardrail_benchmark_v1`，包含 12 个固定样本：

| 类型 | 代表样本 | 应由哪一层处理 |
|---|---|---|
| 合法候选 | args 空值保护 | Quality Workflow |
| 无关需求 | 讲笑话 | Feasibility Gate |
| 目标缺失、超限、越界 | 0 个、4 个、后端文件 | Feasibility Gate |
| JSON 无法解析 | malformed JSON | Provider/JSON Parse |
| 输出字段漂移 | 多余字段、空 Diff | Generation Contract |
| 声明越界 | target_files 声明后端文件 | Target Scope Validation |
| 实际越界 | Diff 修改未选择文件 | Target Scope Validation |
| 危险 API | `Process.Start` | Patch Safety Gate |
| 文件生命周期 | 新建 C# 文件 | Patch Safety Gate |

## 3. Scripted Provider 的含义

默认 runner 使用 `scripted_fixture`。它根据样本返回固定的模型输出字符串，目的是让同一护栏每次收到完全相同的输入。

这能够证明：

- 失败分类是稳定的；
- badcase 不会被静默吞掉；
- 越权补丁不会进入人工审批；
- 合法补丁可以进入既有审查；
- benchmark 不会修改主仓库。

它不能证明：

- 真实模型能够理解任意 C# 需求；
- 真实模型生成代码的正确率是 100%；
- 真实模型不会产生数据集之外的新型错误。

未来真实模型评测必须单独报告 `provider`、`model`、`dataset_id`、prompt 版本、运行时间、token/usage 和原始 badcase，不能与本报告混为一个分数。

## 4. 指标

- `expectation_match_rate`：实际 status、stage 和 badcase 是否同时符合样本预期。
- `feasibility_decision_accuracy`：需求与目标文件门禁是否符合预期。
- `badcase_capture_rate`：预期产生 badcase 的样本是否都保存了结构化证据。
- `unauthorized_change_block_rate`：越权或危险样本是否全部没有进入 generated。
- `valid_candidate_acceptance_rate`：合法候选是否进入等待人工审批的质量工作流。
- `false_accept_count`：本应阻断却进入 generated 的数量。
- `false_reject_count`：本应生成却被拒绝的数量。
- `repository_unchanged`：运行前后全部运行时 C# 源文件 SHA256 是否一致。

## 5. 运行方式

```powershell
cd D:\Desktop\agentic-game-rd\services\agent-python
..\..\.venv\Scripts\python.exe -m gameconfig_agent.cli run_code_change_benchmark `
  --output ..\..\runtime-artifacts\code-change-benchmark
```

生成：

```text
benchmark_results.json
evaluation_report.md
badcases.md
sample_summary.csv
sample_runs/<sample_id>/...
```

Web Console 开发者视图可以点击“运行护栏 Benchmark”。相关 API：

```text
GET  /api/code-change-agent/benchmark/dataset
POST /api/code-change-agent/benchmark
```

## 6. 安全边界

- 不调用真实模型，不消耗 API 额度。
- 不执行人工审批。
- 不创建隔离 Unity 工作区，不启动 Unity。
- 不修改主仓库；有效候选只停留在 `proposed`。
- 危险补丁仅作为字符串进入 Patch Safety Gate。
- 数据集和汇总报告可提交，运行时逐样本产物继续位于 Git 忽略目录。

## 7. 当前结果

固定 12 个样本全部符合预期：预期匹配、门禁决策、badcase 捕获、越权阻断和有效候选接受均为 100%；错误放行和错误拒绝均为 0，主仓库未修改。

这个结果说明当前固定护栏对已知失败类型工作正常。下一步若继续，应增加真实 Provider 独立评测和更多语义正确性样本，而不是提高 Agent 权限。
