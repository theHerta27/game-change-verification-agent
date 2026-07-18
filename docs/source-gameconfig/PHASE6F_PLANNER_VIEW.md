# Phase 6F：策划优先的信息架构

## 目标

默认页面服务策划和 QA，只回答：

1. 这次验证什么配置目标。
2. 当前是否通过。
3. 哪些目标没有达成。
4. 未达成会造成什么影响。
5. 下一步建议怎样调整。

Agent、Tool、Blackboard、JSON、benchmark 和 artifact 仍然保留，但只在“开发者调试”视图出现。

## 两级视图

### 策划 / QA 视图

默认打开，包含：

- 经典案例与需求输入。
- 本次验证结论。
- 关键风险数量。
- 一句话业务摘要。
- 下一步建议。
- 静态校验与 Unity 试玩五步引导。
- 本次试玩概览。
- 目标、实测、结果、影响和建议表格。

这里不显示英文内部字段、trace、Blackboard 或原始 JSON。

### 开发者调试视图

通过顶部模式切换进入，包含：

- Workflow Summary。
- Guided Run 的 `run_id` 和证据文件。
- Agent / Tool Timeline。
- Blackboard Trace。
- Draft / Final Config JSON。
- Validation Errors、Review Findings、Repair Actions。
- Test Scenarios。
- 离线回归评测、badcases、Markdown reports 和 artifacts。

## 结论状态

- `等待验证`：还没有完成当前需求的 Unity 运行。
- `就绪`：静态校验通过，或本次 Unity contract 已准备。
- `进行中`：Unity 已启动，等待本次 telemetry。
- `通过`：本次运行达到当前全部策划目标。
- `未通过`：Unity 正常完成，但存在业务目标偏差。
- `运行任务失败`：启动异常或 Unity 未写 telemetry 就退出。

业务未通过和程序执行失败使用不同语义，避免把策划目标偏差误解为系统崩溃。

## 策划结果表

列定义：

```text
检查项 | 策划目标 | 实测结果 | 结果 | 影响 | 建议
```

策划视图将内部字段转换为业务语言，例如：

- `completion_time_seconds` -> 通关时间
- `enemies_defeated` -> 击败敌人数
- `skill_uses` -> 技能使用次数
- `first_upgrade_affordable` -> 第一次升级可支付
- `second_upgrade_affordable` -> 第二次升级不可连续支付

证据路径和英文 key 只在开发者调试视图保留。

## 数据边界

- 策划视图只把当前 `runtimeRun` 的 telemetry 当作本次实测。
- 没有当前 run 时，不使用历史 latest telemetry 生成本次结论。
- `case_04` 是静态引用校验，可以不启动 Unity 直接显示静态结论。
- `case_01/02` 在运行结果基础上补充 Gold 与 Refine Stone 的多资源经济检查。
- Mock 边界保留在开发者调试视图，不占用策划主流程。
- API、artifact 字段和 Unity runtime contract 没有修改。
