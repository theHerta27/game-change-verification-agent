# Trial Medal 引用缺失

- case_id: `case_04_missing_reference`
- title: Trial Medal 引用缺失
- category: `missing_reference`

## requirement_text

为 Training Sword 的试炼升级配置增加 Trial Medal 消耗。upgrade_config 引用了 item_trial_medal，但 item_config 中暂未定义该材料；系统应发现缺失引用，并由受约束 Repairer 补齐基础 item 定义或记录 unresolved 证据。

## expected_observations

- Reference Checker 返回 item_trial_medal 的 missing_reference。
- Trial Medal 虽存在于 Design Reference，缺少 item_config 时仍不能通过校验。
- Repairer 只能补充资源目录中的已知材料，未知 ID 不得猜测。

## recommended_demo_usage

专项展示案例，用于解释静态引用校验、确定性资源目录和受约束修复边界。
