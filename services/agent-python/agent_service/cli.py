from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_service.agents.dual_agent import run_dual_agent
from agent_service.agents.single_agent import run_single_agent
from agent_service.evaluation.runner import run_phase4_evaluation
from agent_service.schemas import ReviewRequest
from agent_service.summary import (
    generate_phase1_badcases,
    generate_phase1_summary,
    generate_phase2_comparison,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="devquality-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    review_parser = subparsers.add_parser("review", help="run the Phase 1 CLI baseline")
    review_parser.add_argument("--diff", required=True, help="path to a Git diff file")
    review_parser.add_argument("--language", required=True, choices=["go", "python"])
    review_parser.add_argument(
        "--mode",
        default="mock",
        choices=["mock", "single_agent", "dual_agent"],
        help="LLM provider mode. Use mock for the Phase 1/2 CLI baseline. single_agent/dual_agent are deprecated aliases for --workflow.",
    )
    review_parser.add_argument(
        "--workflow",
        default="single_agent",
        choices=["single_agent", "dual_agent"],
        help="agent workflow to run",
    )
    review_parser.add_argument("--mock-case", default="success", choices=["success", "invalid_json", "timeout"])
    review_parser.add_argument("--mock-latency-ms", type=int, default=0)
    review_parser.add_argument("--output", required=True, help="path to write the Markdown report")

    summary_parser = subparsers.add_parser("summarize", help="generate phase summary reports")
    summary_parser.add_argument(
        "--phase",
        required=True,
        choices=["phase1", "phase2"],
        help="phase1 writes phase1_summary and phase1_badcases; phase2 writes phase2_comparison",
    )

    evaluate_parser = subparsers.add_parser("evaluate", help="run Phase 4 mock evaluation")
    evaluate_parser.add_argument(
        "--output-dir",
        default="outputs/phase4",
        help="directory to write evaluation_result.json, evaluation_report.md, badcases.md and comparison_report.md",
    )

    args = parser.parse_args(argv)
    if args.command == "review":
        return _run_review(args)
    if args.command == "summarize":
        return _run_summarize(args)
    if args.command == "evaluate":
        return _run_evaluate(args)
    return 1


def _run_review(args: argparse.Namespace) -> int:
    diff_text = Path(args.diff).read_text(encoding="utf-8")
    workflow = _resolve_workflow(args.mode, args.workflow)
    request = ReviewRequest(
        diff=diff_text,
        language=args.language,
        mode="mock",
        workflow=workflow,
        mock_case=args.mock_case,
        mock_latency_ms=args.mock_latency_ms,
    )
    if workflow == "dual_agent":
        response = run_dual_agent(request)
    else:
        response = run_single_agent(request)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(response.report_markdown, encoding="utf-8")

    print(response.model_dump_json(indent=2), flush=True)
    print(
        (
            f"findings={len(response.findings)} "
            f"test_suggestions={len(response.test_suggestions)} "
            f"latency_ms={sum(run.latency_ms for run in response.agent_runs)} "
            f"validator_passed={not response.validation_errors}"
        ),
        file=sys.stderr,
        flush=True,
    )
    return 0 if not response.validation_errors else 2


def _resolve_workflow(mode: str, workflow: str) -> str:
    # Backward compatibility for older README snippets that used --mode as workflow.
    if mode in {"single_agent", "dual_agent"}:
        return mode
    return workflow


def _run_summarize(args: argparse.Namespace) -> int:
    project_root = Path.cwd()
    if args.phase == "phase1":
        generate_phase1_summary(project_root)
        generate_phase1_badcases(project_root)
        print("wrote outputs/phase1_summary.md and outputs/phase1_badcases.md")
        return 0
    generate_phase2_comparison(project_root)
    print("wrote outputs/phase2_comparison.md")
    return 0


def _run_evaluate(args: argparse.Namespace) -> int:
    project_root = Path.cwd()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    result = run_phase4_evaluation(project_root, output_dir)
    for workflow, workflow_result in result["workflows"].items():
        metrics = workflow_result["metrics"]
        print(
            (
                f"{workflow}: samples={metrics['sample_count']} "
                f"json_valid_rate={metrics['json_valid_rate']} "
                f"validator_pass_rate={metrics['validator_pass_rate']} "
                f"finding_recall={metrics['finding_recall']} "
                f"false_positives={metrics['false_positives']} "
                f"false_negatives={metrics['false_negatives']}"
            ),
            flush=True,
        )
    print(f"wrote {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
