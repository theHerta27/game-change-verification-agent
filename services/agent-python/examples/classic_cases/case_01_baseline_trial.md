# 标准新手试炼关卡

- case_id: `case_01_baseline_trial`
- title: 标准新手试炼关卡
- category: `baseline_trial`

## requirement_text

设计一个 Training Sword 新手试炼关卡：武器基础攻击力 50，可升级 3 次，每级攻击力 +5；升级消耗 Gold 和 Refine Stone；首通奖励只能领取一次。关卡包含 3 波共 5 个敌人，期望 60–90 秒通关，并至少使用 1 次技能。

## expected_observations

- 展示配置生成、静态校验、修复、Unity 运行、telemetry 和评测证据链。
- 基线案例允许部分 runtime target 失败，失败项用于暴露真实调优空间。
- 明确 Mock 输出与 Unity telemetry 的确定性边界。

## recommended_demo_usage

面试主演示第一步，用于建立完整流程全貌，再切换经济和节奏评估视角。
