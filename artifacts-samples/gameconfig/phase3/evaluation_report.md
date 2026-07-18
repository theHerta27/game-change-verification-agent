# Phase 3 Benchmark Evaluation Report

- Dataset: `phase3_benchmark_v1`
- Sample count: 10
- Schema pass rate: 80.00%
- Reference pass rate: 60.00%
- Rule pass rate: 30.00%
- Repair success rate: 50.00%
- Test scenario coverage rate: 60.00%
- Badcase count: 6
- Unresolved count: 4
- Avg repair actions: 1.7

## Samples
### beginner_weapon_flawed
- Tags: beginner weapon, missing reference, reward once_only
- Final passed: True
- Repair actions: 6
- Coverage: 100.0%
- Badcases: 0

### rare_weapon_flawed
- Tags: rare weapon, upgrade cost
- Final passed: True
- Repair actions: 4
- Coverage: 100.0%
- Badcases: 0

### upgrade_cost_negative
- Tags: upgrade cost
- Final passed: True
- Repair actions: 3
- Coverage: 100.0%
- Badcases: 0

### reward_once_only_false
- Tags: reward once_only
- Final passed: True
- Repair actions: 1
- Coverage: 100.0%
- Badcases: 0

### duplicate_reward_hardcase
- Tags: duplicate reward, hardcase
- Final passed: False
- Repair actions: 3
- Coverage: 0.0%
- Badcases: 1

### skill_damage_optional_config
- Tags: skill damage config, optional skill_config
- Final passed: False
- Repair actions: 0
- Coverage: 0.0%
- Badcases: 2

### level_reward_curve
- Tags: level reward curve
- Final passed: True
- Repair actions: 0
- Coverage: 100.0%
- Badcases: 0

### missing_reward_reference
- Tags: missing reference
- Final passed: False
- Repair actions: 0
- Coverage: 0.0%
- Badcases: 1

### safe_balanced_config
- Tags: safe balanced config
- Final passed: True
- Repair actions: 0
- Coverage: 100.0%
- Badcases: 0

### dirty_schema_hardcase
- Tags: hardcase, schema drift
- Final passed: False
- Repair actions: 0
- Coverage: 0.0%
- Badcases: 2
