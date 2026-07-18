# Phase 3 Benchmark Dataset 与 Hardcase Evaluation

## 范围

Phase 3 聚焦核心评测质量。不新增前端，不新增 Agent，不重构 Phase 0 / Phase 1 / Phase 2 主流程。

## Dataset

Benchmark dataset 包含 10 个 requirement samples，覆盖：

- beginner weapon
- rare weapon
- upgrade cost
- reward once_only
- duplicate reward
- skill damage config
- level reward curve
- missing reference
- safe balanced config
- schema drift hardcase

## CLI

```powershell
python -m gameconfig_agent.cli run_phase3_benchmark --output outputs\phase3
```

## 指标

Runner 记录：

- `sample_count`
- `schema_pass_rate`
- `reference_pass_rate`
- `rule_pass_rate`
- `repair_success_rate`
- `test_scenario_coverage_rate`
- `badcase_count`
- `unresolved_count`
- `avg_repair_actions`

## 输出

- `outputs/phase3/benchmark_results.json`
- `outputs/phase3/evaluation_report.md`
- `outputs/phase3/badcases.md`
- `outputs/phase3/sample_summary.csv`
