# Milestone 4：受控 Code Change Agent

状态：已完成。最终验收为 Python 126 passed、Web production build 通过、浏览器 Mock 闭环通过；隔离 Unity 编译与双跑通过，固定种子重复率 100%，主仓库未被候选补丁修改。

## 1. 为什么现在才加入代码生成 Agent

Milestone 3B 已经先证明：一个人工编写的 C# Diff 可以经过安全门、质量审查、人工批准、隔离 Unity 构建和自动试玩。

只有验证闭环稳定后，才允许模型替代“人工编写候选 Diff”这一步：

```text
开发者描述代码需求并选择目标文件
-> Code Change Feasibility Gate
-> Code Change Agent 生成候选 Diff
-> Patch Safety Gate
-> Quality Review Agent
-> 人工批准
-> 隔离 Unity 验证
-> 人工接受 / 修订 / 回滚
```

Agent 增加的是候选方案生成能力，不增加写入主仓库的权限。

## 2. Agent 能看到什么

开发者必须在 Web Console 中显式选择最多 3 个目标文件。允许范围仅为：

```text
game-unity/Assets/Scripts/**/*.cs
```

系统读取这些文件并连同需求放入 Prompt。Agent 看不到：

- 其他 Python、前端或 Unity Editor 代码；
- `.env` 和密钥；
- 本地灵梦模型与贴图；
- Git 历史；
- 构建缓存和运行产物；
- 未被开发者选择的 C# 文件。

这不是为了降低模型能力，而是建立最小权限和可解释上下文。模型输出错误时，可以明确回答“它基于哪些文件做了判断”。

## 3. Prompt Contract

模板位于 `gameconfig_agent/prompts/code_change_generator.md`。真实 Provider 必须返回且只能返回：

```json
{
  "summary": "候选变更摘要",
  "assumptions": ["明确假设"],
  "target_files": ["显式选择的文件"],
  "diff": "完整 unified diff"
}
```

系统随后确定性检查：

1. JSON 是否可解析；
2. 顶层字段是否精确匹配；
3. 字段类型是否正确；
4. 模型声明的文件是否属于用户选择范围；
5. Diff 实际修改的文件是否越界；
6. Diff 是否通过 Milestone 3B Patch Safety Gate。

任何一步失败都会生成 badcase，记录阶段、错误类型、错误消息、模型原始输出、Provider、Model 和目标文件。

## 4. Mock 与真实 Provider

### deterministic Mock

Mock 只支持一个固定 recipe：

```text
为 RuntimeRunSettings.FromArgs 增加 args 空值保护，不改变现有玩法。
```

目标文件必须是：

```text
game-unity/Assets/Scripts/RuntimeRunSettings.cs
```

Mock 根据当前文件内容生成精确 Diff。其他需求返回 `needs_clarification`，不会伪装成通用代码模型。

### OpenAI Compatible

真实 Provider 使用项目已有环境变量：

```text
GAMECONFIG_LLM_BASE_URL
GAMECONFIG_LLM_API_KEY
GAMECONFIG_LLM_MODEL
```

Provider 负责生成候选 Diff。生成后仍使用确定性静态规则和 Mock Quality Review 做稳定回归，因此“生成模型”和“审查模型”是两个独立角色：

```text
真实模型：提出候选代码方案
确定性 Tool：检查权限、路径和危险 API
Mock Review：把静态提示稳定转换为 Finding/Test Suggestion
人工：决定是否允许进入 Unity
```

这样不会因为真实模型偶发波动而绕过质量门禁。

## 5. Web Console 操作

1. 打开“开发者调试”。
2. 在“受控 Code Change Agent”填写代码需求。
3. 勾选允许 Agent 读取的 C# 文件。
4. 选择 Mock 或真实 Provider。
5. 点击“生成候选 Diff”。
6. 查看可行性结论、摘要、假设和 Diff。
7. 生成成功后，下方 C# Diff 质量闭环自动载入候选。
8. 查看安全门、Finding 和 Test Suggestion。
9. 人工批准后创建隔离 Unity 工作区。
10. 运行 Unity 编译、编辑器 smoke 和固定种子双跑。
11. 最终选择接受、要求修订或回滚。

手工粘贴 Diff 的 Milestone 3B 入口仍然保留，便于比较“人写补丁”和“Agent 候选补丁”。

## 6. API

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/code-change-agent/capabilities` | 获取目标文件白名单和 Mock recipe |
| POST | `/api/code-change-agent/proposals` | 根据需求和目标文件生成候选 Diff |
| GET | `/api/code-change-agent/proposals/{proposal_id}` | 查询生成结果及下游工作流状态 |

候选生成成功后返回 `code_workflow.workflow_id`，后续复用 `/api/code-workflows/*`，不建立第二套审批与 Unity API。

## 7. 如何理解 Agent 的边界

本项目中的 Agent 不是“可以做任何事的机器人”。它由三部分组成：

- **模型推理**：根据需求和有限代码上下文提出 Diff；
- **状态管理**：记录生成、审查、审批和验证阶段；
- **工具调用**：调用 Parser、Safety Gate、Validator 和 Unity 测试。

真正决定系统能不能落地的不是模型单次回答有多聪明，而是：

- 输入上下文是否准确；
- 输出契约是否可校验；
- 权限是否足够小；
- 失败是否留下证据；
- 是否能在真实 Unity 环境复现；
- 人是否保留最终决策权。

## 8. 当前不足

- Mock 只有一个固定 recipe，不代表代码生成质量。
- 真实 Provider 尚无多样化 C# benchmark，不能给出可信的真实生成成功率。
- 目标文件由开发者选择，尚未实现基于符号索引的自动上下文检索。
- 当前只修改既有文件，不支持新增测试文件，所以 Unity Test Framework 仍未接入。
- 没有 Git worktree 和自动合并；接受结果仍需开发者人工查看和合并。
- Unity 自动试玩证明回归可运行，不证明真实玩家体验和长期平衡。

下一步应该优先扩展小型、真实的 C# 需求 benchmark 和失败分类，而不是马上扩大写权限或堆叠更多 Agent。
