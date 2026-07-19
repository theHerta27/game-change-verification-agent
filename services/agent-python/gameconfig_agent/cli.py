"""Command line entry point for GameConfig Agent demos."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gameconfig_agent.agents.generator import ConfigGeneratorAgent
from gameconfig_agent.agents.repairer import ConfigRepairAgent
from gameconfig_agent.agents.reviewer import ConfigReviewerAgent
from gameconfig_agent.agents.test_scenario import TestScenarioAgent
from gameconfig_agent.blackboard import create_blackboard, record_trace
from gameconfig_agent.data.design_reference import BALANCE_POLICY_LOOKUP
from gameconfig_agent.data.evaluation_dataset import EVALUATION_DATASET
from gameconfig_agent.env_loader import load_dotenv
from gameconfig_agent.milestone1_testbed import evaluate_testbed_files
from gameconfig_agent.phase3_benchmark import run_phase3_benchmark
from gameconfig_agent.real_run import export_real_run, failed_evaluation_result, make_provider, run_real_evaluation
from gameconfig_agent.runtime_contract import export_runtime_contract
from gameconfig_agent.runtime_evaluation import evaluate_runtime_files
from gameconfig_agent.tools.evaluator import EvaluationTool
from gameconfig_agent.tools.exporter import ExporterReportBuilderTool
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool
from gameconfig_agent.tools.rule_engine import RuleEngineTool
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


def run_phase0_demo(input_path: str | Path, output_dir: str | Path) -> dict:
    requirement_text = Path(input_path).read_text(encoding="utf-8").strip()
    blackboard = create_blackboard(requirement_text)
    blackboard["design_reference"] = BALANCE_POLICY_LOOKUP

    generator = ConfigGeneratorAgent()
    generator.generate(blackboard)
    record_trace(
        blackboard,
        actor=generator.name,
        actor_type="agent",
        action="generate_draft_configs",
        input_refs=["requirement_text", "design_reference"],
        output_refs=["structured_requirement", "draft_configs", "assumptions"],
        status="succeeded",
    )

    schema_tool = SchemaValidatorTool()
    schema_errors = schema_tool.validate(blackboard["structured_requirement"], blackboard["draft_configs"])
    blackboard["validation_runs"]["draft_schema"] = {"errors": schema_errors, "passed": not schema_errors}
    record_trace(
        blackboard,
        actor=schema_tool.name,
        actor_type="tool",
        action="validate_schema",
        input_refs=["structured_requirement", "draft_configs"],
        output_refs=["validation_runs.draft_schema"],
        status="failed" if schema_errors else "succeeded",
        error_count=len(schema_errors),
    )

    reference_tool = ReferenceCheckerTool()
    reference_errors = reference_tool.check(blackboard["draft_configs"])
    blackboard["validation_runs"]["draft_reference"] = {
        "errors": reference_errors,
        "passed": not reference_errors,
    }
    record_trace(
        blackboard,
        actor=reference_tool.name,
        actor_type="tool",
        action="check_references",
        input_refs=["draft_configs"],
        output_refs=["validation_runs.draft_reference"],
        status="failed" if reference_errors else "succeeded",
        error_count=len(reference_errors),
    )

    rule_tool = RuleEngineTool()
    rule_result = rule_tool.evaluate(blackboard["structured_requirement"], blackboard["draft_configs"])
    rule_errors = rule_result["violations"]
    blackboard["validation_runs"]["draft_rule"] = {
        "errors": rule_errors,
        "passed": not rule_errors,
        "coupled_fields": rule_result["coupled_fields"],
    }
    blackboard["validation_errors"] = schema_errors + reference_errors + rule_errors
    record_trace(
        blackboard,
        actor=rule_tool.name,
        actor_type="tool",
        action="evaluate_rules",
        input_refs=["structured_requirement", "draft_configs"],
        output_refs=["validation_runs.draft_rule", "validation_errors"],
        status="failed" if rule_errors else "succeeded",
        error_count=len(rule_errors),
    )

    reviewer = ConfigReviewerAgent()
    findings = reviewer.review(blackboard)
    record_trace(
        blackboard,
        actor=reviewer.name,
        actor_type="agent",
        action="review_balance_consistency_and_risk",
        input_refs=["draft_configs", "validation_errors", "design_reference"],
        output_refs=["review_findings"],
        status="succeeded",
        error_count=len(findings),
    )

    repairer = ConfigRepairAgent()
    actions = repairer.repair(blackboard)
    record_trace(
        blackboard,
        actor=repairer.name,
        actor_type="agent",
        action="repair_bounded_local_issues",
        input_refs=["validation_errors", "review_findings", "design_reference"],
        output_refs=["repaired_configs", "repair_actions"],
        status="succeeded",
        error_count=0,
    )

    final_schema_errors = schema_tool.validate(blackboard["structured_requirement"], blackboard["repaired_configs"])
    final_reference_errors = reference_tool.check(blackboard["repaired_configs"])
    final_rule_result = rule_tool.evaluate(blackboard["structured_requirement"], blackboard["repaired_configs"])
    final_errors = final_schema_errors + final_reference_errors + final_rule_result["violations"]
    blackboard["final_validation"] = {
        "passed": not final_errors,
        "errors": final_errors,
        "schema_errors": final_schema_errors,
        "reference_errors": final_reference_errors,
        "rule_errors": final_rule_result["violations"],
    }
    record_trace(
        blackboard,
        actor="Final Validation",
        actor_type="tool",
        action="validate_repaired_configs",
        input_refs=["structured_requirement", "repaired_configs"],
        output_refs=["final_validation"],
        status="failed" if final_errors else "succeeded",
        error_count=len(final_errors),
    )

    exporter = ExporterReportBuilderTool()
    exported_files = exporter.export(blackboard, output_dir)
    record_trace(
        blackboard,
        actor=exporter.name,
        actor_type="tool",
        action="export_phase0_artifacts",
        input_refs=["draft_configs", "repaired_configs", "trace", "review_findings", "repair_actions"],
        output_refs=["outputs/phase0"],
        status="succeeded",
    )
    exporter.export(blackboard, output_dir)
    blackboard["exported_files"] = [str(path) for path in exported_files]
    return blackboard


def build_summary(blackboard: dict) -> str:
    files = "\n".join(f"  {path}" for path in blackboard.get("exported_files", []))
    return f"""GameConfig Agent Phase 0 Demo

Input: Training Sword beginner weapon requirement

Workflow:
  Config Generator Agent: draft generated with 4 config groups and 5 intentional issues
  Schema Validator Tool: {'passed' if blackboard['validation_runs']['draft_schema']['passed'] else 'failed'}
  Reference Checker Tool: {'passed' if blackboard['validation_runs']['draft_reference']['passed'] else 'failed'}, {len(blackboard['validation_runs']['draft_reference']['errors'])} missing reference
  Rule Engine Tool: {'passed' if blackboard['validation_runs']['draft_rule']['passed'] else 'failed'}, {len(blackboard['validation_runs']['draft_rule']['errors'])} rule violations
  Config Reviewer Agent: {len(blackboard['review_findings'])} review findings
  Config Repair Agent: {len(blackboard['repair_actions'])} repair actions
  Final Validation: {'passed' if blackboard['final_validation']['passed'] else 'failed'}

Outputs:
{files}
"""


def run_phase1_demo(input_path: str | Path, phase0_output_dir: str | Path, output_dir: str | Path) -> dict:
    phase0_blackboard = run_phase0_demo(input_path, phase0_output_dir)
    agent = TestScenarioAgent()
    scenarios = agent.generate(phase0_blackboard["repaired_configs"])
    evaluation = EvaluationTool().evaluate(scenarios, EVALUATION_DATASET)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    files = [
        _write_json(output_path / "test_scenarios.json", scenarios),
        _write_text(output_path / "test_scenario_report.md", _test_scenario_report(scenarios)),
        _write_text(output_path / "evaluation_report.md", _evaluation_report(evaluation)),
    ]

    return {
        "phase0": phase0_blackboard,
        "test_scenarios": scenarios,
        "evaluation": evaluation,
        "exported_files": [str(path) for path in files],
    }


def build_phase1_summary(result: dict) -> str:
    files = "\n".join(f"  {path}" for path in result["exported_files"])
    evaluation = result["evaluation"]
    return f"""GameConfig Agent Phase 1 Demo

Input: Training Sword final configs from deterministic Phase 0

Workflow:
  Phase 0 final configs: {'passed' if result['phase0']['final_validation']['passed'] else 'failed'}
  Test Scenario Agent: {len(result['test_scenarios'])} scenarios generated
  Evaluation Tool: {evaluation['coverage_percent']}% coverage ({evaluation['covered_tag_count']}/{evaluation['expected_tag_count']} tags)
  Evaluation Result: {'passed' if evaluation['passed'] else 'failed'}

Outputs:
{files}
"""


def run_real_demo(input_path: str | Path, output_dir: str | Path, provider_name: str) -> dict:
    load_dotenv(Path.cwd() / ".env")
    requirement_text = Path(input_path).read_text(encoding="utf-8").strip()
    try:
        provider = make_provider(provider_name)
        result = run_real_evaluation(provider, requirement_text)
    except Exception as exc:
        result = failed_evaluation_result(provider_name, exc, requirement_text)
    exported_files = export_real_run(result, output_dir)
    result["exported_files"] = [str(path) for path in exported_files]
    return result


def build_real_summary(result: dict) -> str:
    files = "\n".join(f"  {path}" for path in result["exported_files"])
    metrics = result["metrics"]
    return f"""GameConfig Agent Phase 2 Real-Run Demo

Provider: {result['provider']}

Evaluation:
  Samples: {metrics['sample_count']}
  JSON Parse Success Rate: {metrics['json_parse_success_rate']:.2%}
  Schema Pass Rate: {metrics['schema_pass_rate']:.2%}
  Final Validation Pass Rate: {metrics['final_validation_pass_rate']:.2%}
  Repair Success Rate: {metrics['repair_success_rate']:.2%}
  Test Scenario Coverage Rate: {metrics['test_scenario_coverage_rate']:.2%}
  Latency Total: {metrics['latency_ms']['total']} ms
  Token Estimate: {metrics['token_estimate']}
  Badcases: {metrics['badcase_count']}

Outputs:
{files}
"""


def build_phase3_summary(result: dict) -> str:
    files = "\n".join(f"  {path}" for path in result["exported_files"])
    metrics = result["metrics"]
    return f"""GameConfig Agent Phase 3 Benchmark

Evaluation:
  Samples: {metrics['sample_count']}
  Schema Pass Rate: {metrics['schema_pass_rate']:.2%}
  Reference Pass Rate: {metrics['reference_pass_rate']:.2%}
  Rule Pass Rate: {metrics['rule_pass_rate']:.2%}
  Repair Success Rate: {metrics['repair_success_rate']:.2%}
  Test Scenario Coverage Rate: {metrics['test_scenario_coverage_rate']:.2%}
  Badcases: {metrics['badcase_count']}
  Unresolved: {metrics['unresolved_count']}
  Avg Repair Actions: {metrics['avg_repair_actions']}

Outputs:
{files}
"""


def build_code_change_benchmark_summary(result: dict) -> str:
    metrics = result["metrics"]
    files = "\n".join(f"  {path}" for path in result["exported_files"])
    return f"""Code Change Agent Guardrail Benchmark

Dataset: {result['dataset_id']}
Provider Mode: {result['provider_mode']} (not a real-model quality score)

Evaluation:
  Samples: {metrics['sample_count']}
  Expectation Match Rate: {metrics['expectation_match_rate']:.2%}
  Feasibility Decision Accuracy: {metrics['feasibility_decision_accuracy']:.2%}
  Badcase Capture Rate: {metrics['badcase_capture_rate']:.2%}
  Unauthorized Change Block Rate: {metrics['unauthorized_change_block_rate']:.2%}
  Valid Candidate Acceptance Rate: {metrics['valid_candidate_acceptance_rate']:.2%}
  False Accepts: {metrics['false_accept_count']}
  False Rejects: {metrics['false_reject_count']}
  Repository Unchanged: {metrics['repository_unchanged']}

Outputs:
{files}
"""


def build_real_code_evaluation_summary(result: dict) -> str:
    files = "\n".join(f"  {path}" for path in result["exported_files"])
    if result["run_status"] == "blocked":
        return f"""Real Provider Code Generation Evaluation

Status: blocked
Provider: {result['provider']}
Reason: {result['configuration_error']['error_message']}

No model call was made. Empty rates are not model scores.

Outputs:
{files}
"""
    metrics = result["metrics"]
    return f"""Real Provider Code Generation Evaluation

Status: completed
Dataset: {result['dataset_id']}
Provider: {result['provider']}
Model: {result['model']}

Evaluation:
  Samples: {metrics['sample_count']}
  JSON Parse Success Rate: {metrics['json_parse_success_rate']:.2%}
  Generation Contract Pass Rate: {metrics['generation_contract_pass_rate']:.2%}
  Patch Safety Pass Rate: {metrics['patch_safety_pass_rate']:.2%}
  Quality Review Pass Rate: {metrics['quality_review_pass_rate']:.2%}
  Patch Apply Success Rate: {metrics['patch_apply_success_rate']:.2%}
  Semantic Intent Pass Rate: {metrics['semantic_intent_pass_rate']:.2%}
  Semantic Requirement Pass Rate: {metrics['semantic_requirement_pass_rate']:.2%}
  Candidate Ready Rate: {metrics['candidate_ready_rate']:.2%}
  Badcases: {metrics['badcase_count']}
  Latency Total: {metrics['latency_ms']['total']} ms

Outputs:
{files}
"""


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_text(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    return path


def _test_scenario_report(scenarios: list[dict]) -> str:
    lines = [
        "# Test Scenario Report",
        "",
        f"- Scenario count: {len(scenarios)}",
        "- Source agent: Test Scenario Agent",
        "",
    ]
    for scenario in scenarios:
        lines.extend(
            [
                f"## {scenario['scenario_id']}",
                f"- Title: {scenario['title']}",
                f"- Priority: {scenario['priority']}",
                f"- Coverage tags: `{', '.join(scenario['coverage_tags'])}`",
                f"- Expected result: {scenario['expected_result']}",
                "",
            ]
        )
    return "\n".join(lines)


def _evaluation_report(evaluation: dict) -> str:
    lines = [
        "# Evaluation Report",
        "",
        f"- Dataset: `{evaluation['dataset_id']}`",
        f"- Scenario count: {evaluation['scenario_count']}",
        f"- Coverage: {evaluation['coverage_percent']}%",
        f"- Covered tags: {evaluation['covered_tag_count']}/{evaluation['expected_tag_count']}",
        f"- Passed: {evaluation['passed']}",
        "",
        "## Covered Tags",
    ]
    lines.extend(f"- `{tag}`" for tag in evaluation["covered_tags"])
    lines.extend(["", "## Missing Tags"])
    if evaluation["missing_tags"]:
        lines.extend(f"- `{tag}`" for tag in evaluation["missing_tags"])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gameconfig-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser("run_demo", help="Run the deterministic Phase 0 demo.")
    demo_parser.add_argument("--input", required=True, help="Requirement text file.")
    demo_parser.add_argument("--output", required=True, help="Output directory.")

    phase1_parser = subparsers.add_parser("run_phase1_demo", help="Run deterministic Phase 1 scenario generation.")
    phase1_parser.add_argument("--input", required=True, help="Requirement text file used to regenerate Phase 0 configs.")
    phase1_parser.add_argument("--phase0-output", default="outputs/phase0", help="Phase 0 output directory.")
    phase1_parser.add_argument("--output", required=True, help="Phase 1 output directory.")

    real_parser = subparsers.add_parser("run_real_demo", help="Run Phase 2 provider-backed evaluation.")
    real_parser.add_argument("--input", required=True, help="Requirement text file.")
    real_parser.add_argument("--output", required=True, help="Phase 2 output directory.")
    real_parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai_compatible"],
        help="LLM provider. Defaults to deterministic mock.",
    )

    phase3_parser = subparsers.add_parser("run_phase3_benchmark", help="Run Phase 3 benchmark evaluation.")
    phase3_parser.add_argument("--output", required=True, help="Phase 3 output directory.")

    code_benchmark_parser = subparsers.add_parser(
        "run_code_change_benchmark",
        help="Run the deterministic Code Change Agent guardrail benchmark.",
    )
    code_benchmark_parser.add_argument("--output", required=True, help="Benchmark output directory.")
    code_benchmark_parser.add_argument(
        "--dataset",
        default="evals/code_change_benchmark_v1.json",
        help="Versioned benchmark dataset path, relative to repository root by default.",
    )

    real_code_parser = subparsers.add_parser(
        "run_real_code_evaluation",
        help="Run the small OpenAI-compatible Unity C# generation evaluation.",
    )
    real_code_parser.add_argument("--output", required=True, help="Real code evaluation output directory.")
    real_code_parser.add_argument(
        "--dataset",
        default="evals/real_code_generation_v1.json",
        help="Versioned real-code dataset path.",
    )
    real_code_parser.add_argument("--timeout-seconds", type=int, default=60, help="Per-sample provider timeout.")

    replay_real_code_parser = subparsers.add_parser(
        "replay_real_code_evaluation",
        help="Replay local evaluators against saved real-provider outputs without API calls.",
    )
    replay_real_code_parser.add_argument("--output", required=True, help="Existing real code evaluation directory.")
    replay_real_code_parser.add_argument(
        "--dataset",
        default="evals/real_code_generation_v1.json",
        help="Versioned real-code dataset path.",
    )

    unity_parser = subparsers.add_parser(
        "export_unity_runtime_config",
        help="Export validated final configs as a Unity runtime contract.",
    )
    unity_parser.add_argument("--config", required=True, help="Path to final_configs.json.")
    unity_parser.add_argument("--output", required=True, help="Unity StreamingAssets JSON path.")

    unity_evaluation_parser = subparsers.add_parser(
        "evaluate_unity_runtime",
        help="Evaluate Unity telemetry against runtime design targets.",
    )
    unity_evaluation_parser.add_argument("--contract", required=True, help="Unity runtime contract JSON path.")
    unity_evaluation_parser.add_argument("--telemetry", required=True, help="Unity telemetry JSON path.")
    unity_evaluation_parser.add_argument("--output", required=True, help="Runtime evaluation output directory.")

    testbed_parser = subparsers.add_parser(
        "evaluate_milestone1_testbed",
        help="Evaluate two fixed-seed Unity greybox runs for repeatability.",
    )
    testbed_parser.add_argument("--profile", required=True, help="Milestone 1 test profile JSON path.")
    testbed_parser.add_argument("--telemetry", required=True, help="Primary Unity telemetry JSON path.")
    testbed_parser.add_argument("--repeat-telemetry", required=True, help="Repeated Unity telemetry JSON path.")
    testbed_parser.add_argument("--output", required=True, help="Testbed evaluation output directory.")

    args = parser.parse_args(argv)
    if args.command == "run_demo":
        blackboard = run_phase0_demo(args.input, args.output)
        print(build_summary(blackboard))
        return 0 if blackboard["final_validation"]["passed"] else 1
    if args.command == "run_phase1_demo":
        result = run_phase1_demo(args.input, args.phase0_output, args.output)
        print(build_phase1_summary(result))
        return 0 if result["evaluation"]["passed"] else 1
    if args.command == "run_real_demo":
        result = run_real_demo(args.input, args.output, args.provider)
        print(build_real_summary(result))
        return 0 if result["metrics"]["final_validation_pass_rate"] > 0 else 1
    if args.command == "run_phase3_benchmark":
        result = run_phase3_benchmark(args.output)
        print(build_phase3_summary(result))
        return 0
    if args.command == "run_code_change_benchmark":
        from workflow.code_change_benchmark import run_code_change_benchmark

        repository_root = Path(__file__).resolve().parents[3]
        result = run_code_change_benchmark(repository_root, args.output, args.dataset)
        print(build_code_change_benchmark_summary(result))
        return 0 if result["metrics"]["expectation_match_rate"] == 1 else 1
    if args.command == "run_real_code_evaluation":
        from workflow.real_code_evaluation import run_real_code_evaluation

        repository_root = Path(__file__).resolve().parents[3]
        result = run_real_code_evaluation(
            repository_root,
            args.output,
            dataset_path=args.dataset,
            timeout_seconds=args.timeout_seconds,
        )
        print(build_real_code_evaluation_summary(result))
        if result["run_status"] == "blocked":
            return 2
        return 0 if result["metrics"]["candidate_ready_rate"] == 1 else 1
    if args.command == "replay_real_code_evaluation":
        from workflow.real_code_evaluation import replay_real_code_evaluation

        repository_root = Path(__file__).resolve().parents[3]
        try:
            result = replay_real_code_evaluation(
                repository_root,
                args.output,
                dataset_path=args.dataset,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"Real code evaluation replay failed: {exc}")
            return 2
        print(build_real_code_evaluation_summary(result))
        return 0 if result["metrics"]["candidate_ready_rate"] == 1 else 1
    if args.command == "export_unity_runtime_config":
        destination = export_runtime_contract(args.config, args.output)
        print(f"Unity runtime contract exported: {destination}")
        return 0
    if args.command == "evaluate_unity_runtime":
        result = evaluate_runtime_files(args.contract, args.telemetry, args.output)
        print(f"Unity runtime target pass rate: {result['runtime_target_pass_rate']:.1%}")
        return 0 if result["passed"] else 1
    if args.command == "evaluate_milestone1_testbed":
        result = evaluate_testbed_files(
            args.profile,
            args.telemetry,
            args.repeat_telemetry,
            args.output,
        )
        print(f"Milestone 1 testbed repeatability rate: {result['repeatability_rate']:.1%}")
        return 0 if result["passed"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
