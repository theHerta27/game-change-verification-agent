# Phase 1 测试场景生成

## 目标

Phase 1 在 Phase 0 final configs 之上新增 Test Scenario Agent。它不生成或修复配置，而是把已经通过最终校验的配置转换为可执行的配置测试场景，并用 small evaluation dataset 计算覆盖率。

## 输入

- `outputs/phase0/final_configs.json`
- deterministic Phase 0 blackboard 中的 `repaired_configs`

CLI 为了保持 demo 自洽，会先运行 Phase 0 deterministic workflow，再把 final configs 交给 Test Scenario Agent。

## Test Scenario Agent 输出

Test Scenario Agent 生成 7 个场景：

- Training Sword 基础攻击力符合新手需求
- Weapon item reference 能解析到 item_config
- 升级等级连续且每级 +5 攻击
- 金币消耗符合新手曲线
- 强化石消耗符合新手曲线
- 新手任务奖励只能领取一次
- 奖励 item 和 weapon 引用可解析

每个场景包含：

- `scenario_id`
- `title`
- `config_refs`
- `steps`
- `expected_result`
- `coverage_tags`
- `priority`
- `source_agent`

## Evaluation Dataset

Small evaluation dataset 定义 8 个 expected coverage tags：

- `base_attack_exact`
- `weapon_item_reference`
- `upgrade_levels_continuous`
- `upgrade_bonus_per_level`
- `gold_cost_curve`
- `material_cost_curve`
- `reward_once_only`
- `reward_item_reference`

Coverage 计算方式：

```text
已覆盖 expected tags / 全部 expected tags
```

当前 demo 结果为 `8/8 = 100%`。

## 输出

- `outputs/phase1/test_scenarios.json`
- `outputs/phase1/test_scenario_report.md`
- `outputs/phase1/evaluation_report.md`
