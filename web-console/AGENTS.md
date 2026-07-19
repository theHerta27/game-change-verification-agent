# Web Console 约束

- 这是唯一前端控制台，不迁移 DevQuality 旧前端。
- 默认面向策划/QA，开发者证据使用已有分级视图。
- 后端 JSON、API、artifact 和环境变量字段保持英文稳定。
- 策划视图使用 Milestone 3A 的变更提案、人工审批、Unity 证据和最终决策主线；旧阶段调试能力保留在开发者视图。
- 人工 C# Diff 闭环只放在开发者调试视图，并明确“接受不等于自动合并”。
- Code Change Agent 只放在开发者调试视图；必须显示目标文件权限、Mock recipe 边界和候选 Diff。
- 变更后运行 `npm run build`。
