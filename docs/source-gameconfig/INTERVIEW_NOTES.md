# 面试讲解笔记

## 一句话介绍

GameConfig Agent 是一个面向游戏研发管线中“策划配置生成”的多 Agent 原型：它把自然语言策划需求转成结构化游戏配置，并通过校验、审查、修复、测试场景生成和基准评测，让配置产物可追踪、可验证、可迭代。

## 岗位需求如何对应到项目

这个岗位关注的是 AI Agent 在游戏研发管线中的落地，而不是单纯做聊天机器人。我的切入点是策划配置生成，因为它真实存在于游戏生产流程里：策划提出数值和奖励需求，配置需要符合 schema、引用合法、数值合理、奖励规则安全，还要能被测试和回归验证。

项目对应岗位职责的方式：

- 研发工具链：把“需求输入 -> 配置草案 -> 自动校验 -> 审查 -> 修复 -> 测试场景 -> 评测报告”做成一条本地工具链。
- 游戏生产管线：围绕武器、升级、奖励、道具等常见配置类型设计流程，而不是泛泛生成文本。
- Agent 方向：用不同 Agent 承担生成、审查、修复、测试场景生成等职责，用确定性工具承担 schema、引用、规则和指标计算。
- 工程落地：保留 CLI、FastAPI、本地 Web Console、pytest、benchmark dataset、badcase 记录和真实 LLM provider 边界。

## 真实业务痛点

策划配置生成的难点不是“模型能不能写 JSON”，而是生成结果能不能进入研发流程。

几个典型痛点：

- 配置结构必须稳定，否则程序侧读取失败。
- 引用必须存在，例如奖励引用的 item id 不能缺失。
- 数值和规则要符合设计约束，例如升级等级连续、消耗不能为 0、一次性奖励不能重复领取。
- 修复不能乱改全表，只能在明确范围内做局部修复。
- 真实 LLM 会出现 schema drift，系统不能因为脏输出直接崩溃。
- 面试或协作时需要能解释每一步为什么发生，而不是只展示最终 JSON。

## 架构亮点

- Python 核心 pipeline，默认 deterministic MockLLM，保证演示和测试可复现。
- Blackboard 作为多 Agent 共享工作区，记录需求、草案、错误、审查发现、修复动作、最终配置和 trace。
- Generator / Reviewer / Repairer / Test Scenario Agent 分工清晰。
- Schema Validator / Reference Checker / Rule Engine / Evaluation / Exporter 保持确定性工具边界。
- Provider 抽象支持 MockLLM 和 OpenAI-compatible provider，真实模型输出必须经过现有校验。
- badcase 机制记录 JSON 解析失败、schema drift、校验失败和未解决样本。
- Web Console 只做本地可视化，不改变核心 pipeline。

## 为什么是 Multi-Agent

游戏配置生成包含多个职责：需求理解、配置生成、风险审查、局部修复、测试场景设计。把它们拆成 Agent 的价值不是“为了多 Agent 而多 Agent”，而是让每个角色的输入、输出和责任可追踪。

讲法可以是：

“如果只用一个大 prompt 生成最终配置，失败时很难知道是需求理解错了、引用缺失、规则不满足，还是修复策略不合理。拆成 Generator、Reviewer、Repairer 和 Test Scenario Agent 后，每一步都能被工具校验和 trace 记录，这更接近研发工具链，而不是一次性内容生成。”

## Agent / Tool / Design Reference 边界

- Agent：处理语义判断、审查和修复决策，例如生成草案、判断风险、选择修复动作。
- Tool：处理确定性逻辑，例如 schema 校验、引用检查、规则检查、指标计算、导出报告。
- Design Reference：提供游戏数值设计参考，例如合法区间或推荐边界，但它不做 Agent 决策。

这个边界很重要。不是所有模块都应该叫 Agent。能确定性执行的部分应该作为 Tool，这样系统更稳定，也更容易测试。

## Blackboard + Repair Loop 怎么工作

1. Generator 读取策划需求，生成结构化配置草案。
2. Schema Validator 检查结构是否合法。
3. Reference Checker 检查配置引用是否存在。
4. Rule Engine 检查硬规则和设计约束。
5. Reviewer 汇总平衡性、一致性和上线风险。
6. Repairer 根据错误和审查发现做有边界的局部修复。
7. Final Validation 再跑一次校验，判断最终配置是否可交付。
8. Test Scenario Agent 基于最终配置生成测试场景。
9. Benchmark runner 用多样本评测整体稳定性和 hardcase 表现。

默认 Mock 演示里，前两个工具之后可能看到“发现配置问题”。这是正常的：它表示草案没通过校验，随后 Repairer 会修复，关键看最终校验是否成功。

## Phase 3 指标怎么解释

- `sample_count`：benchmark 样本数。
- `schema_pass_rate`：初始草案结构合法率。
- `reference_pass_rate`：初始草案引用完整率。
- `rule_pass_rate`：初始草案硬规则通过率。
- `repair_success_rate`：修复后最终通过率。
- `test_scenario_coverage_rate`：生成测试场景覆盖预期标签的比例。
- `badcase_count`：系统显式记录的问题样本数。
- `unresolved_count`：当前修复策略仍无法解决的样本数。
- `avg_repair_actions`：平均每个样本产生多少修复动作。

这些指标不要包装成“越高越炫”的功能点。它们的价值是暴露系统边界：哪些配置类型稳定，哪些 hardcase 需要补规则、补参考数据或调整修复策略。

## 真实 LLM Provider 和 MockLLM 边界

MockLLM 是默认路径，用来保证演示、测试和 benchmark 稳定复现。真实 provider 是可选路径，用环境变量或 `.env` 配置，不在代码里写密钥。

真实 LLM 输出不可信，所以必须经过：

- JSON parse
- schema validation
- reference validation
- rule validation
- badcase logging

如果真实模型把 `upgrade_config` 的对象输出成字符串，validator 不应该崩溃，而应该返回结构化 schema error，并把原始输出写入 badcase。这一点能体现对 LLM 能力边界的理解。

## Web Console 的价值

Web Console 不是为了“再做一个前端”，而是让工具链可演示、可排查、可协作。它把 blackboard trace、timeline、草案配置、最终配置、校验错误、修复动作、测试场景、指标和 badcases 放在同一屏，面试时可以直接讲清楚系统为什么这样设计。

## 推荐讲解顺序

1. 先讲业务问题：策划配置生成不只是让模型输出一段语法正确的 JSON，而是让这份配置满足业务约束，并能被安全地接入研发管线。
2. 再讲系统边界：Agent 做语义和决策，Tool 做确定性校验，Mock 保证可复现，真实 provider 作为可选路径。
3. 打开 Web Console，运行默认 Mock demo。
4. 指着 timeline 说明草案发现问题是正常流程，Repairer 会做局部修复。
5. 展示 Final Config、Repair Actions、Test Scenarios。
6. 运行 Phase 3 benchmark，说明指标和 badcases 暴露系统边界。
7. 最后讲不足和改进方向，表现出你不是只堆功能，而是在理解生产管线。

