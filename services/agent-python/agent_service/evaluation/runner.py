from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from agent_service.agents.dual_agent import run_dual_agent
from agent_service.agents.single_agent import run_single_agent
from agent_service.evaluation.dataset import EvaluationSample, load_evaluation_dataset
from agent_service.schemas import ReviewRequest, ReviewResponse


WORKFLOWS = ("single_agent", "dual_agent")


def run_phase4_evaluation(project_root: Path, output_dir: Path | None = None) -> dict[str, Any]:
    output_dir = output_dir or project_root / "outputs" / "phase4"
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = load_evaluation_dataset()
    result: dict[str, Any] = {
        "dataset_size": len(samples),
        "workflows": {},
    }

    comparison_rows: list[dict[str, Any]] = []
    all_badcases: list[dict[str, Any]] = []

    for workflow in WORKFLOWS:
        workflow_result = _run_workflow(samples, workflow)
        result["workflows"][workflow] = workflow_result
        all_badcases.extend(workflow_result["badcases"])

    for sample in samples:
        single = _sample_result(result, "single_agent", sample.name)
        dual = _sample_result(result, "dual_agent", sample.name)
        comparison_rows.append(
            {
                "sample": sample.name,
                "language": sample.language,
                "expected_findings": len(sample.expected_findings),
                "single_findings": single["findings_count"],
                "dual_findings": dual["findings_count"],
                "single_tests": single["test_suggestions_count"],
                "dual_tests": dual["test_suggestions_count"],
                "single_validator_pass": single["validator_passed"],
                "dual_validator_pass": dual["validator_passed"],
                "single_token_estimate": single["token_estimate"],
                "dual_token_estimate": dual["token_estimate"],
                "badcase_attribution": _badcase_attribution(single, dual),
            }
        )

    result["comparison"] = {
        "rows": comparison_rows,
        "summary": _comparison_summary(comparison_rows),
    }

    _write_json(output_dir / "evaluation_result.json", result)
    (output_dir / "evaluation_report.md").write_text(_evaluation_report(result), encoding="utf-8")
    (output_dir / "badcases.md").write_text(_badcases_report(all_badcases), encoding="utf-8")
    (output_dir / "comparison_report.md").write_text(_comparison_report(result), encoding="utf-8")
    _write_comparison_csv(output_dir / "single_vs_dual_metrics.csv", result)
    _write_comparison_chart(output_dir / "single_vs_dual_comparison.png", result)
    (output_dir / "phase4_summary.md").write_text(
        _phase4_summary(result, _load_backend_load_result(project_root)),
        encoding="utf-8",
    )
    return result


def _run_workflow(samples: tuple[EvaluationSample, ...], workflow: str) -> dict[str, Any]:
    sample_results = []
    badcases = []

    for sample in samples:
        started = perf_counter()
        response = _run_sample(sample, workflow)
        elapsed_ms = (perf_counter() - started) * 1000
        sample_result = _evaluate_sample(sample, workflow, response, elapsed_ms)
        sample_results.append(sample_result)
        badcases.extend(sample_result["badcases"])

    metrics = _aggregate_metrics(sample_results)
    return {
        "metrics": metrics,
        "samples": sample_results,
        "badcases": badcases,
    }


def _run_sample(sample: EvaluationSample, workflow: str) -> ReviewResponse:
    request = ReviewRequest(
        diff=sample.diff,
        language=sample.language,
        mode="mock",
        workflow=workflow,
    )
    if workflow == "dual_agent":
        return run_dual_agent(request)
    return run_single_agent(request)


def _evaluate_sample(
    sample: EvaluationSample,
    workflow: str,
    response: ReviewResponse,
    elapsed_ms: float,
) -> dict[str, Any]:
    expected_categories = Counter(finding.category for finding in sample.expected_findings)
    actual_categories = Counter(finding.category for finding in response.findings)
    expected_severities = Counter(finding.severity for finding in sample.expected_findings)
    actual_severities = Counter(finding.severity for finding in response.findings)

    matched_categories = _counter_intersection_total(expected_categories, actual_categories)
    false_positive_categories = list((actual_categories - expected_categories).elements())
    false_negative_categories = list((expected_categories - actual_categories).elements())
    severity_missing = list((expected_severities - actual_severities).elements())

    test_links_ok = all(
        0 <= suggestion.finding_index < len(response.findings)
        for suggestion in response.test_suggestions
    )
    expected_tests_ok = len(response.test_suggestions) >= sample.expected_test_suggestions
    validator_passed = not response.validation_errors
    json_valid = all(run.status == "succeeded" for run in response.agent_runs)

    sample_badcases = []
    if not json_valid:
        sample_badcases.append(_badcase(sample, workflow, "schema_invalid", response.validation_errors))
    if false_negative_categories:
        sample_badcases.append(_badcase(sample, workflow, "false_negative", false_negative_categories))
    if false_positive_categories:
        sample_badcases.append(_badcase(sample, workflow, "false_positive", false_positive_categories))
    if not test_links_ok or not expected_tests_ok:
        sample_badcases.append(
            _badcase(
                sample,
                workflow,
                "test_suggestion_missing",
                {
                    "links_ok": test_links_ok,
                    "expected": sample.expected_test_suggestions,
                    "actual": len(response.test_suggestions),
                },
            )
        )

    return {
        "sample": sample.name,
        "language": sample.language,
        "source_type": sample.source_type,
        "workflow": workflow,
        "expected_categories": list(expected_categories.elements()),
        "actual_categories": list(actual_categories.elements()),
        "expected_severities": list(expected_severities.elements()),
        "actual_severities": list(actual_severities.elements()),
        "matched_findings": matched_categories,
        "expected_findings_count": len(sample.expected_findings),
        "findings_count": len(response.findings),
        "test_suggestions_count": len(response.test_suggestions),
        "json_valid": json_valid,
        "validator_passed": validator_passed,
        "test_link_rate": 1.0 if test_links_ok else 0.0,
        "false_positive_categories": false_positive_categories,
        "false_negative_categories": false_negative_categories,
        "severity_missing": severity_missing,
        "validation_errors": response.validation_errors,
        "latency_ms": round(elapsed_ms, 3),
        "agent_run_names": [run.agent_name for run in response.agent_runs],
        "token_estimate": _token_estimate(response),
        "badcases": sample_badcases,
    }


def _aggregate_metrics(sample_results: list[dict[str, Any]]) -> dict[str, Any]:
    total_samples = len(sample_results)
    expected_total = sum(item["expected_findings_count"] for item in sample_results)
    matched_total = sum(item["matched_findings"] for item in sample_results)
    false_positive_total = sum(len(item["false_positive_categories"]) for item in sample_results)
    false_negative_total = sum(len(item["false_negative_categories"]) for item in sample_results)
    test_link_total = sum(item["test_link_rate"] for item in sample_results)

    return {
        "sample_count": total_samples,
        "json_valid_rate": _ratio(sum(1 for item in sample_results if item["json_valid"]), total_samples),
        "validator_pass_rate": _ratio(sum(1 for item in sample_results if item["validator_passed"]), total_samples),
        "finding_recall": _ratio(matched_total, expected_total),
        "false_positives": false_positive_total,
        "false_negatives": false_negative_total,
        "test_suggestion_link_rate": _ratio(test_link_total, total_samples),
        "avg_latency_ms": round(sum(item["latency_ms"] for item in sample_results) / max(total_samples, 1), 3),
        "avg_token_estimate": round(sum(item["token_estimate"] for item in sample_results) / max(total_samples, 1), 2),
    }


def _evaluation_report(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 4 Evaluation Report",
        "",
        f"- Dataset size: {result['dataset_size']}",
        "- Mode: mock",
        "- Workflows: single_agent, dual_agent",
        "- Latency: in-process workflow timing measured with `perf_counter`; backend/API latency is measured separately by the mock backend load test.",
        "",
        "| workflow | json valid rate | validator pass rate | finding recall | false positives | false negatives | test link rate | avg latency ms | avg token estimate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for workflow, workflow_result in result["workflows"].items():
        metrics = workflow_result["metrics"]
        lines.append(
            "| "
            + " | ".join(
                [
                    workflow,
                    _fmt_rate(metrics["json_valid_rate"]),
                    _fmt_rate(metrics["validator_pass_rate"]),
                    _fmt_rate(metrics["finding_recall"]),
                    str(metrics["false_positives"]),
                    str(metrics["false_negatives"]),
                    _fmt_rate(metrics["test_suggestion_link_rate"]),
                    str(metrics["avg_latency_ms"]),
                    str(metrics["avg_token_estimate"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _badcases_report(badcases: list[dict[str, Any]]) -> str:
    lines = ["# Phase 4 Badcases", ""]
    if not badcases:
        lines.append("No badcases found in the current mock evaluation run.")
        return "\n".join(lines) + "\n"

    lines.extend(["| workflow | sample | type | details |", "| --- | --- | --- | --- |"])
    for item in badcases:
        details = json.dumps(item["details"], ensure_ascii=False)
        lines.append(f"| {item['workflow']} | {item['sample']} | {item['type']} | `{details}` |")
    return "\n".join(lines) + "\n"


def _comparison_report(result: dict[str, Any]) -> str:
    rows = result["comparison"]["rows"]
    lines = [
        "# Phase 4 Single vs Dual Comparison",
        "",
        "| sample | language | expected | single findings | dual findings | single tests | dual tests | single validator | dual validator | single tokens | dual tokens | badcase attribution |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["sample"],
                    row["language"],
                    str(row["expected_findings"]),
                    str(row["single_findings"]),
                    str(row["dual_findings"]),
                    str(row["single_tests"]),
                    str(row["dual_tests"]),
                    str(row["single_validator_pass"]),
                    str(row["dual_validator_pass"]),
                    str(row["single_token_estimate"]),
                    str(row["dual_token_estimate"]),
                    row["badcase_attribution"],
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _write_comparison_csv(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "workflow",
        "json_valid_rate",
        "validator_pass_rate",
        "finding_recall",
        "test_suggestion_link_rate",
        "avg_token_estimate",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for workflow in WORKFLOWS:
            metrics = result["workflows"][workflow]["metrics"]
            writer.writerow({field: workflow if field == "workflow" else metrics[field] for field in fields})


def _write_comparison_chart(path: Path, result: dict[str, Any]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    rate_keys = [
        ("json_valid_rate", "JSON 有效率"),
        ("validator_pass_rate", "校验通过率"),
        ("finding_recall", "Finding 召回率"),
        ("test_suggestion_link_rate", "测试关联率"),
    ]
    x_positions = list(range(len(rate_keys)))
    width = 0.34
    colors = {"single_agent": "#2F6B9A", "dual_agent": "#D97706"}

    fig, (rate_ax, token_ax) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [3, 1]})
    for offset, workflow in zip((-width / 2, width / 2), WORKFLOWS, strict=True):
        metrics = result["workflows"][workflow]["metrics"]
        rate_ax.bar(
            [position + offset for position in x_positions],
            [metrics[key] * 100 for key, _ in rate_keys],
            width,
            label=workflow,
            color=colors[workflow],
        )
    rate_ax.set_title("工作流质量指标")
    rate_ax.set_ylabel("比例（%）")
    rate_ax.set_ylim(0, 110)
    rate_ax.set_xticks(x_positions, [label for _, label in rate_keys], rotation=15, ha="right")
    rate_ax.grid(axis="y", alpha=0.25)
    rate_ax.legend(frameon=False)

    token_values = [result["workflows"][workflow]["metrics"]["avg_token_estimate"] for workflow in WORKFLOWS]
    token_ax.bar(WORKFLOWS, token_values, color=[colors[workflow] for workflow in WORKFLOWS])
    token_ax.set_title("平均 Token 估算")
    token_ax.set_ylabel("估算 Token / 样本")
    token_ax.tick_params(axis="x", rotation=20)
    token_ax.grid(axis="y", alpha=0.25)
    for index, value in enumerate(token_values):
        token_ax.text(index, value, f"{value:.2f}", ha="center", va="bottom")

    fig.suptitle("DevQuality Phase 4A：单 Agent 与双 Agent 对比")
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def _load_backend_load_result(project_root: Path) -> dict[str, Any] | None:
    path = project_root.parent / "backend" / "outputs" / "phase4_load" / "mock_backend_load_result.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _phase4_summary(result: dict[str, Any], load_result: dict[str, Any] | None) -> str:
    single = result["workflows"]["single_agent"]["metrics"]
    dual = result["workflows"]["dual_agent"]["metrics"]
    badcase_count = sum(len(workflow["badcases"]) for workflow in result["workflows"].values())
    lines = [
        "# DevQuality Phase 4A Final Summary",
        "",
        "## Scope",
        "",
        "- Positioning: Development Quality Agent Platform with single-agent baseline and Review/Test dual-agent workflow.",
        f"- Dataset size: {result['dataset_size']} Go/Python Git Diff samples.",
        "- Evaluation mode: deterministic static rules + MockLLM; no real LLM is used.",
        "",
        "## Single-Agent vs Dual-Agent",
        "",
        "| workflow | JSON valid | validator pass | finding recall | false positives | false negatives | test link | avg tokens |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        _summary_metric_row("single_agent", single),
        _summary_metric_row("dual_agent", dual),
        "",
        "在当前 mock dataset 中，single_agent 与 dual_agent 的 finding/test 结果一致；dual_agent token estimate 更高，但 Review/Test 分离带来更好的职责边界、结构化校验、失败归因和后续真实 LLM 独立重试能力。",
        "",
        "## Badcases",
        "",
        f"- Automated badcases in this run: {badcase_count}.",
        "- The result means the current deterministic rules and labels are internally consistent; it does not establish generalization to unseen repositories.",
        "",
        "## Mock Backend Load Test",
        "",
    ]
    if load_result is None:
        lines.append("- Existing load-test result was not available when this summary was generated.")
    else:
        lines.extend(
            [
                "| concurrency | requests | success rate | avg ms | P95 ms | P99 ms | final status |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for level in load_result["levels"]:
            lines.append(
                f"| {level['concurrency']} | {level['total_requests']} | "
                f"{_fmt_rate(level['success_rate'])} | {level['avg_latency_ms']} | "
                f"{level['p95_latency_ms']} | {level['p99_latency_ms']} | "
                f"`{json.dumps(level['final_status_distribution'], sort_keys=True)}` |"
            )
    lines.extend(
        [
            "",
            "## Current Conclusion",
            "",
            "- The mock evaluation demonstrates schema, validator, deterministic-rule, and workflow reproducibility on the labeled dataset.",
            "- The backend load result demonstrates successful queued task completion under the recorded local mock configuration; higher concurrency includes queueing delay and is not a production throughput claim.",
            "- DevQuality v1 stops at this evaluation boundary. It will not add a multi-agent board; multi-agent collaboration will be explored in the separate GameConfig Agent project.",
            "",
            "## Limitations",
            "",
            "- Mock metrics must not be interpreted as real-LLM accuracy.",
            "- Dataset labels are aligned with the current deterministic rules and require broader independently reviewed open-source patches for external validity.",
            "- Token values are MockLLM estimates, not provider billing measurements.",
            "- Load-test results are from one local machine and one worker configuration.",
            "",
            "## Real LLM Provider TODO",
            "",
            "- Add an OpenAI-compatible provider behind the existing LLM abstraction.",
            "- Version prompts and record provider/model parameters for replay.",
            "- Add schema-repair, timeout, retry, and per-stage retry policies.",
            "- Re-run blind evaluation on independently labeled patches and report precision/recall with confidence intervals.",
        ]
    )
    return "\n".join(lines) + "\n"


def _summary_metric_row(workflow: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {workflow} | {_fmt_rate(metrics['json_valid_rate'])} | "
        f"{_fmt_rate(metrics['validator_pass_rate'])} | {_fmt_rate(metrics['finding_recall'])} | "
        f"{metrics['false_positives']} | {metrics['false_negatives']} | "
        f"{_fmt_rate(metrics['test_suggestion_link_rate'])} | {metrics['avg_token_estimate']} |"
    )


def _comparison_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "samples_compared": len(rows),
        "same_findings_count": sum(1 for row in rows if row["single_findings"] == row["dual_findings"]),
        "same_test_suggestions_count": sum(1 for row in rows if row["single_tests"] == row["dual_tests"]),
        "dual_runs_are_stage_attributable": True,
    }


def _badcase_attribution(single: dict[str, Any], dual: dict[str, Any]) -> str:
    if not single["badcases"] and not dual["badcases"]:
        return "none"
    if dual["badcases"] and "review_agent" in dual["agent_run_names"]:
        return "dual_agent_stage_visible"
    return "single_agent_combined"


def _sample_result(result: dict[str, Any], workflow: str, sample_name: str) -> dict[str, Any]:
    for item in result["workflows"][workflow]["samples"]:
        if item["sample"] == sample_name:
            return item
    raise KeyError(sample_name)


def _badcase(sample: EvaluationSample, workflow: str, case_type: str, details: Any) -> dict[str, Any]:
    return {
        "sample": sample.name,
        "workflow": workflow,
        "type": case_type,
        "details": details,
    }


def _counter_intersection_total(left: Counter[str], right: Counter[str]) -> int:
    return sum((left & right).values())


def _token_estimate(response: ReviewResponse) -> int:
    return sum((run.input_tokens or 0) + (run.output_tokens or 0) for run in response.agent_runs)


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 4)


def _fmt_rate(value: float) -> str:
    return f"{value * 100:.2f}%"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
