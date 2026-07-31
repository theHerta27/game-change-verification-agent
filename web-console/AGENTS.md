# Web Console 约束

- 这是唯一前端控制台，不迁移 DevQuality 旧前端。
- 默认面向策划/QA，开发者证据使用已有分级视图。
- 后端 JSON、API、artifact 和环境变量字段保持英文稳定。
- 策划视图使用 Milestone 3A 的变更提案、人工审批、Unity 证据和最终决策主线；旧阶段调试能力保留在开发者视图。
- 人工 C# Diff 闭环只放在开发者调试视图，并明确“接受不等于自动合并”。
- Code Change Agent 只放在开发者调试视图；必须显示目标文件权限、Mock recipe 边界和候选 Diff。
- 代码变更 benchmark 只放在开发者视图，并明确标注“脚本化护栏评测不代表真实模型能力”。
- 真实代码评测只放在开发者视图，必须显示配置状态、调用数量、静态证据边界，并与脚本化护栏指标分栏。
- 页面应优先读取最近一次真实评测产物；不得为了刷新页面自动触发外部模型调用。
- Milestone 7 新增“弹幕变更验证”策划主页面，优先展示目标、Config Diff、授权预算、Before/After 证据、修复历史和最终决策；原始 JSON 与日志留在开发者视图。
- 引擎选择支持 Unity 6 与 Unreal Engine 5；运行按钮和手动试玩入口必须跟随后端 `capabilities` 的真实状态，不得在 `unavailable/build_required` 时可用。
- 变更后运行 `npm run build`。
