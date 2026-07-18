# 首通奖励过量风险

- case_id: `case_02_reward_overgrant`
- title: 首通奖励过量风险
- category: `reward_economy`

## requirement_text

检查 Training Sword 新手试炼的首通经济：首通奖励为 300 Gold 和 3 Refine Stone；玩家应能完成第一次升级，但扣除第一次升级成本后不应立即完成第二次升级。

## expected_observations

- 使用 Classic Case Evaluation Profile 提供首通资源库存。
- 同时计算 Gold 与 Refine Stone，不能只看单一货币。
- 当前配置在第一次升级后仍可完成第二次升级，应提示首通奖励过量风险。

## recommended_demo_usage

面试主演示第二步，说明配置质量需要跨表静态经济计算，而不是肉眼查看 JSON。
