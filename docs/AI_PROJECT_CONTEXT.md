# Agentic Game R&D Lab 项目简介

这份文档用于让网页端或其他 AI 快速了解项目大方向。需要深入讨论时，再根据具体问题提供相关源码。

## 项目定位

这是一个 AI Agent 驱动的游戏研发工具原型，主要探索：

- 策划配置生成；
- 配置校验与修复；
- 自动化测试和 Unity 运行验证；
- 代码审查与受控代码生成；
- Agent 调试、评测和 Badcase 分析。

技术栈：

- Python + FastAPI：Agent、校验器、工作流和 API；
- React + TypeScript：Web Console；
- Unity 6：可运行的游戏测试场景；
- MockLLM 与 OpenAI Compatible Provider：确定性回归和真实模型实验。

## 核心思路

项目不允许大模型直接修改最终游戏内容。模型只负责提出候选，后续必须经过确定性检查、人工审批和 Unity 验证：

```text
自然语言需求
-> Agent 生成候选配置或代码 Diff
-> Schema / Reference / Rule / Patch Safety 校验
-> Quality Review
-> 人工批准
-> Unity 隔离运行
-> telemetry 评测
-> 接受 / 修订 / 回滚
```

这样可以避免模型输出结构错误、引用缺失、数值不合理或代码补丁无法安全应用。

## 当前演示

当前游戏演示是 Training Sword 新手试炼关卡：

- 三波敌人，共 5 个敌人；
- 支持移动、普通攻击、技能和武器升级；
- 可以手动试玩，也可以固定随机种子自动试玩；
- Unity 输出通关时间、攻击次数、技能次数、击败数等 telemetry；
- Web Console 展示配置变化、Agent Trace、风险、Badcase 和运行评测。

本地可以使用博丽灵梦模型作为角色表现；没有模型时自动使用占位角色，不影响测试逻辑。

## 主要能力

### GameConfig

把策划需求转换成配置草案，再由 Generator、Reviewer、Repairer、Test Scenario Agent 和确定性校验工具处理。

### Quality Review

检查配置或代码变更中的风险，生成 Finding 和 Test Suggestion。

### Code Change Agent

开发者显式选择最多 3 个 Unity C# 文件后，真实模型可以生成候选 Diff。模型不能浏览整个仓库、修改主仓库、绕过审批或自动合并代码。

### Web Console

- 策划 / QA 视图：关注需求、配置变化、风险、Unity 试玩和最终结论；
- 开发者调试视图：查看 Agent Trace、Blackboard、JSON、Diff、Badcase 和评测指标。

## Mock 与真实模型

- GameConfig Mock 是固定 Training Sword 演示，用于保证流程可重复；
- Code Change Mock 只支持固定示例，不代表通用代码生成；
- Scripted benchmark 用于验证工程护栏，不代表真实模型质量；
- OpenAI Compatible Provider 才是真实模型调用，但输出仍必须经过相同校验。

## 当前结果

- Python：137 tests passed；
- 前端 production build：通过；
- Unity 固定种子双跑可重复率：100%；
- Code Change 护栏 benchmark：12 个固定样本，预期匹配率 100%；
- 真实代码生成评测：5 个样本；
- 真实模型语义意图命中率：100%；
- 补丁严格应用率和候选就绪率：60%；
- 两个失败案例都是代码意图基本正确，但 unified diff 上下文不准确。

## 当前不足

- Unity 场景仍然比较简单，不能代表完整商业游戏；
- 配置类型和玩法覆盖有限；
- 固定种子测试只能证明回归稳定，不能代表真实玩家体验；
- Unity Test Framework 尚未正式接入；
- 真实模型直接生成 unified diff 的稳定性不足；
- 后续更合理的方向是让模型输出结构化修改意图，再由确定性工具生成 Diff。

## 目录

```text
services/agent-python/   Agent、校验器、工作流和 FastAPI
web-console/             React Web Console
game-unity/              Unity 测试场景
evals/                   固定评测数据集
docs/                    项目文档
runtime-artifacts/       本地运行证据，不提交 Git
local-assets/            本地第三方资产，不提交 Git
```

讨论本项目时，请区分“当前已经实现”“合理推断”和“未来建议”，也不要把 Mock、脚本化 benchmark、真实模型输出和 Unity 实测结果混为一谈。
