"""Phase 3 benchmark dataset and hardcase evaluation runner."""

from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path

from gameconfig_agent.agents.repairer import ConfigRepairAgent
from gameconfig_agent.agents.reviewer import ConfigReviewerAgent
from gameconfig_agent.agents.test_scenario import TestScenarioAgent
from gameconfig_agent.blackboard import create_blackboard
from gameconfig_agent.data.benchmark_dataset import BENCHMARK_SAMPLES
from gameconfig_agent.data.design_reference import BALANCE_POLICY_LOOKUP
from gameconfig_agent.data.evaluation_dataset import EVALUATION_DATASET
from gameconfig_agent.tools.evaluator import EvaluationTool
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool
from gameconfig_agent.tools.rule_engine import RuleEngineTool
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


def run_phase3_benchmark(output_dir: str | Path) -> dict:
    runner = Phase3BenchmarkRunner()
    result = runner.run()
    result["exported_files"] = [str(path) for path in export_phase3(result, output_dir)]
    return result


class Phase3BenchmarkRunner:
    def __init__(self) -> None:
        self.schema_tool = SchemaValidatorTool()
        self.reference_tool = ReferenceCheckerTool()
        self.rule_tool = RuleEngineTool()
        self.reviewer = ConfigReviewerAgent()
        self.repairer = ConfigRepairAgent()
        self.scenario_agent = TestScenarioAgent()
        self.evaluator = EvaluationTool()

    def run(self) -> dict:
        sample_results = [self._run_sample(sample) for sample in BENCHMARK_SAMPLES]
        metrics = self._metrics(sample_results)
        return {
            "dataset_id": "phase3_benchmark_v1",
            "sample_count": len(sample_results),
            "samples": sample_results,
            "metrics": metrics,
        }

    def _run_sample(self, sample: dict) -> dict:
        structured_requirement = deepcopy(sample["structured_requirement"])
        draft_configs = deepcopy(sample["draft_configs"])
        initial_schema_errors = self.schema_tool.validate(structured_requirement, draft_configs)
        initial_reference_errors = []
        initial_rule_errors = []
        review_findings = []
        repair_actions = []
        final_configs = deepcopy(draft_configs)
        badcases = []

        if initial_schema_errors:
            badcases.append(
                {
                    "sample_id": sample["sample_id"],
                    "stage": "schema_validation",
                    "reason": "initial schema validation failed",
                    "errors": initial_schema_errors,
                }
            )
        else:
            initial_reference_errors = self.reference_tool.check(draft_configs)
            initial_rule_errors = self.rule_tool.evaluate(structured_requirement, draft_configs)["violations"]
            initial_errors = initial_reference_errors + initial_rule_errors
            if initial_errors:
                blackboard = self._blackboard(sample, structured_requirement, draft_configs, initial_errors)
                try:
                    review_findings = self.reviewer.review(blackboard)
                    repair_actions = self.repairer.repair(blackboard)
                    final_configs = blackboard["repaired_configs"]
                except Exception as exc:
                    badcases.append(
                        {
                            "sample_id": sample["sample_id"],
                            "stage": "repair_loop",
                            "reason": "existing repair loop could not handle sample",
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    )

        final_schema_errors = self.schema_tool.validate(structured_requirement, final_configs)
        final_reference_errors = []
        final_rule_errors = []
        if not final_schema_errors:
            final_reference_errors = self.reference_tool.check(final_configs)
            final_rule_errors = self.rule_tool.evaluate(structured_requirement, final_configs)["violations"]

        final_passed = not (final_schema_errors or final_reference_errors or final_rule_errors)
        if not final_passed:
            badcases.append(
                {
                    "sample_id": sample["sample_id"],
                    "stage": "final_validation",
                    "reason": "sample remains unresolved after benchmark flow",
                    "schema_errors": final_schema_errors,
                    "reference_errors": final_reference_errors,
                    "rule_errors": final_rule_errors,
                }
            )

        test_scenarios = []
        evaluation = self.evaluator.evaluate([], EVALUATION_DATASET)
        if final_passed and final_configs.get("weapon_config") and final_configs.get("reward_config"):
            try:
                test_scenarios = self.scenario_agent.generate(final_configs)
                evaluation = self.evaluator.evaluate(test_scenarios, EVALUATION_DATASET)
            except Exception as exc:
                badcases.append(
                    {
                        "sample_id": sample["sample_id"],
                        "stage": "test_scenario_generation",
                        "reason": "existing Test Scenario Agent could not handle sample",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )

        return {
            "sample_id": sample["sample_id"],
            "requirement_text": sample["requirement_text"],
            "tags": sample["tags"],
            "initial_validation": {
                "schema_passed": not initial_schema_errors,
                "reference_passed": not initial_reference_errors and not initial_schema_errors,
                "rule_passed": not initial_rule_errors and not initial_schema_errors,
                "schema_errors": initial_schema_errors,
                "reference_errors": initial_reference_errors,
                "rule_errors": initial_rule_errors,
            },
            "review_findings": review_findings,
            "repair_actions": repair_actions,
            "final_validation": {
                "passed": final_passed,
                "schema_errors": final_schema_errors,
                "reference_errors": final_reference_errors,
                "rule_errors": final_rule_errors,
            },
            "test_scenario_count": len(test_scenarios),
            "test_scenario_coverage": evaluation["coverage"],
            "test_scenario_coverage_percent": evaluation["coverage_percent"],
            "badcases": badcases,
            "unresolved": not final_passed,
        }

    def _blackboard(self, sample: dict, structured_requirement: dict, draft_configs: dict, validation_errors: list[dict]) -> dict:
        blackboard = create_blackboard(sample["requirement_text"])
        blackboard["structured_requirement"] = structured_requirement
        blackboard["draft_configs"] = draft_configs
        blackboard["validation_errors"] = validation_errors
        blackboard["design_reference"] = BALANCE_POLICY_LOOKUP
        return blackboard

    def _metrics(self, sample_results: list[dict]) -> dict:
        sample_count = len(sample_results) or 1
        repair_attempts = [sample for sample in sample_results if sample["repair_actions"] or not sample["initial_validation"]["rule_passed"] or not sample["initial_validation"]["reference_passed"]]
        repair_successes = [sample for sample in repair_attempts if sample["repair_actions"] and sample["final_validation"]["passed"]]
        return {
            "sample_count": len(sample_results),
            "schema_pass_rate": _rate(sample["initial_validation"]["schema_passed"] for sample in sample_results),
            "reference_pass_rate": _rate(sample["initial_validation"]["reference_passed"] for sample in sample_results),
            "rule_pass_rate": _rate(sample["initial_validation"]["rule_passed"] for sample in sample_results),
            "repair_success_rate": len(repair_successes) / len(repair_attempts) if repair_attempts else 1.0,
            "test_scenario_coverage_rate": sum(sample["test_scenario_coverage"] for sample in sample_results) / sample_count,
            "badcase_count": sum(len(sample["badcases"]) for sample in sample_results),
            "unresolved_count": sum(1 for sample in sample_results if sample["unresolved"]),
            "avg_repair_actions": round(sum(len(sample["repair_actions"]) for sample in sample_results) / sample_count, 2),
        }


def export_phase3(result: dict, output_dir: str | Path) -> list[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    files = [
        _write_json(output_path / "benchmark_results.json", result),
        _write_text(output_path / "evaluation_report.md", _evaluation_report(result)),
        _write_text(output_path / "badcases.md", _badcases_report(result)),
        _write_csv(output_path / "sample_summary.csv", result["samples"]),
    ]
    return files


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    return path


def _write_csv(path: Path, samples: list[dict]) -> Path:
    fieldnames = [
        "sample_id",
        "tags",
        "schema_passed",
        "reference_passed",
        "rule_passed",
        "final_passed",
        "repair_actions",
        "coverage_percent",
        "badcases",
        "unresolved",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for sample in samples:
            writer.writerow(
                {
                    "sample_id": sample["sample_id"],
                    "tags": ";".join(sample["tags"]),
                    "schema_passed": sample["initial_validation"]["schema_passed"],
                    "reference_passed": sample["initial_validation"]["reference_passed"],
                    "rule_passed": sample["initial_validation"]["rule_passed"],
                    "final_passed": sample["final_validation"]["passed"],
                    "repair_actions": len(sample["repair_actions"]),
                    "coverage_percent": sample["test_scenario_coverage_percent"],
                    "badcases": len(sample["badcases"]),
                    "unresolved": sample["unresolved"],
                }
            )
    return path


def _evaluation_report(result: dict) -> str:
    metrics = result["metrics"]
    lines = [
        "# Phase 3 Benchmark Evaluation Report",
        "",
        f"- Dataset: `{result['dataset_id']}`",
        f"- Sample count: {metrics['sample_count']}",
        f"- Schema pass rate: {metrics['schema_pass_rate']:.2%}",
        f"- Reference pass rate: {metrics['reference_pass_rate']:.2%}",
        f"- Rule pass rate: {metrics['rule_pass_rate']:.2%}",
        f"- Repair success rate: {metrics['repair_success_rate']:.2%}",
        f"- Test scenario coverage rate: {metrics['test_scenario_coverage_rate']:.2%}",
        f"- Badcase count: {metrics['badcase_count']}",
        f"- Unresolved count: {metrics['unresolved_count']}",
        f"- Avg repair actions: {metrics['avg_repair_actions']}",
        "",
        "## Samples",
    ]
    for sample in result["samples"]:
        lines.extend(
            [
                f"### {sample['sample_id']}",
                f"- Tags: {', '.join(sample['tags'])}",
                f"- Final passed: {sample['final_validation']['passed']}",
                f"- Repair actions: {len(sample['repair_actions'])}",
                f"- Coverage: {sample['test_scenario_coverage_percent']}%",
                f"- Badcases: {len(sample['badcases'])}",
                "",
            ]
        )
    return "\n".join(lines)


def _badcases_report(result: dict) -> str:
    badcases = [badcase for sample in result["samples"] for badcase in sample["badcases"]]
    lines = ["# Phase 3 Badcases", ""]
    if not badcases:
        lines.append("- None")
        return "\n".join(lines) + "\n"
    for index, badcase in enumerate(badcases, start=1):
        lines.extend(
            [
                f"## Badcase {index}",
                f"- Sample: `{badcase.get('sample_id')}`",
                f"- Stage: `{badcase.get('stage')}`",
                f"- Reason: {badcase.get('reason')}",
                f"- Detail: `{json.dumps(badcase, ensure_ascii=False)}`",
                "",
            ]
        )
    return "\n".join(lines)


def _rate(values) -> float:
    values = list(values)
    return sum(1 for value in values if value) / len(values) if values else 1.0
