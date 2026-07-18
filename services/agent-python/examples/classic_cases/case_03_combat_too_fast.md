# 关卡节奏过快风险

- case_id: `case_03_combat_too_fast`
- title: 关卡节奏过快风险
- category: `combat_pacing`

## requirement_text

评估 Training Sword 新手试炼的战斗节奏：3 波共 5 个敌人，目标通关时间为 60–90 秒。Unity 实测明显低于下限时，应提示敌人耐久、波次规模或玩家输出需要调整。

## expected_observations

- 使用最近一次 Training Sword Unity telemetry，而不是伪装成独立关卡运行。
- 约 16.45 秒的通关时间应判定为失败。
- 风险提示必须附带 telemetry 字段证据和可执行修复方向。

## recommended_demo_usage

面试主演示第三步，说明静态合法不等于实际游戏节奏符合策划目标。
