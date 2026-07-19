"""Deterministic benchmark for Code Change Agent guardrails and failure routing."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv
import hashlib
import json

from gameconfig_agent.providers.base import LLMResponse
from workflow.code_change_agent import CodeChangeAgentService, MOCK_TARGET
from workflow.code_workflow import CodeWorkflowService


DEFAULT_DATASET = "evals/code_change_benchmark_v1.json"
BENCHMARK_PROVIDER = "scripted_fixture"
BENCHMARK_MODEL = "scripted-code-guardrail-v1"


class ScriptedBenchmarkProvider:
    model = BENCHMARK_MODEL

    def __init__(self, content: str) -> None:
        self.content = content

    def complete_json(self, **_kwargs: Any) -> LLMResponse:
        return LLMResponse(
            content=self.content,
            latency_ms=0,
            usage=None,
            token_estimate=None,
        )


def load_code_change_benchmark(
    repository_root: Path,
    dataset_path: str | Path = DEFAULT_DATASET,
) -> dict[str, Any]:
    path = Path(dataset_path)
    if not path.is_absolute():
        path = repository_root / path
    dataset = json.loads(path.read_text(encoding="utf-8-sig"))
    samples = dataset.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Code change benchmark must contain non-empty samples.")
    sample_ids = [sample.get("sample_id") for sample in samples]
    if any(not isinstance(sample_id, str) or not sample_id for sample_id in sample_ids):
        raise ValueError("Every benchmark sample must have a non-empty sample_id.")
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Code change benchmark sample_id values must be unique.")
    return dataset


def run_code_change_benchmark(
    repository_root: Path,
    output_dir: str | Path,
    dataset_path: str | Path = DEFAULT_DATASET,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    dataset = load_code_change_benchmark(repository_root, dataset_path)
    baseline_hashes = _runtime_source_hashes(repository_root)
    sample_results: list[dict[str, Any]] = []

    for sample in dataset["samples"]:
        raw_output = _fixture_output(repository_root, sample["fixture_kind"])
        sample_root = output_path / "sample_runs" / sample["sample_id"]
        workflows = CodeWorkflowService(
            repository_root=repository_root,
            workflows_dir=sample_root / "code_workflows",
        )
        service = CodeChangeAgentService(
            repository_root=repository_root,
            proposals_dir=sample_root / "proposals",
            code_workflows=workflows,
            provider_factory=lambda _timeout, content=raw_output: ScriptedBenchmarkProvider(content),
        )
        result = service.propose(
            requirement_text=sample["requirement_text"],
            target_files=sample["target_files"],
            provider="openai_compatible",
            timeout_seconds=30,
        )
        actual_stage = _actual_stage(result)
        expectation_match = (
            result["status"] == sample["expected_status"]
            and actual_stage == sample["expected_stage"]
            and bool(result.get("badcase")) == sample["expected_badcase"]
        )
        sample_results.append(
            {
                "sample_id": sample["sample_id"],
                "category": sample["category"],
                "expected": {
                    "feasibility": sample["expected_feasibility"],
                    "status": sample["expected_status"],
                    "stage": sample["expected_stage"],
                    "badcase": sample["expected_badcase"],
                },
                "actual": {
                    "feasibility": result["feasibility_gate"]["decision"],
                    "status": result["status"],
                    "stage": actual_stage,
                    "badcase": bool(result.get("badcase")),
                    "proposal_id": result["proposal_id"],
                    "code_workflow_id": (
                        result.get("code_workflow") or {}
                    ).get("workflow_id"),
                    "error_type": (result.get("badcase") or {}).get("error_type"),
                    "error_message": (result.get("badcase") or {}).get("error_message"),
                },
                "security_case": sample["security_case"],
                "valid_candidate": sample["valid_candidate"],
                "expectation_match": expectation_match,
            }
        )

    repository_unchanged = baseline_hashes == _runtime_source_hashes(repository_root)
    metrics = _metrics(sample_results, repository_unchanged)
    benchmark = {
        "dataset_id": dataset["dataset_id"],
        "dataset_title": dataset["title"],
        "evaluation_subject": dataset["evaluation_subject"],
        "provider_mode": BENCHMARK_PROVIDER,
        "model": BENCHMARK_MODEL,
        "disclaimer": dataset["disclaimer"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "samples": sample_results,
    }
    exported = export_code_change_benchmark(benchmark, output_path)
    benchmark["exported_files"] = [str(path) for path in exported]
    _write_json(output_path / "benchmark_results.json", benchmark)
    return benchmark


def export_code_change_benchmark(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = _write_json(output_dir / "benchmark_results.json", result)
    report_path = output_dir / "evaluation_report.md"
    report_path.write_text(_markdown_report(result), encoding="utf-8")
    badcases_path = output_dir / "badcases.md"
    badcases_path.write_text(_badcases_report(result), encoding="utf-8")
    csv_path = output_dir / "sample_summary.csv"
    _write_csv(csv_path, result["samples"])
    return [results_path, report_path, badcases_path, csv_path]


def _fixture_output(repository_root: Path, fixture_kind: str) -> str:
    safe_diff = (repository_root / "examples/csharp/runtime_args_null_guard.patch").read_text(encoding="utf-8")
    unsafe_diff = (repository_root / "examples/csharp/unsafe_process_launch.patch").read_text(encoding="utf-8")
    if fixture_kind == "unused":
        return "{}"
    if fixture_kind == "malformed_json":
        return "{malformed benchmark json"
    if fixture_kind == "valid_null_guard":
        return _payload(safe_diff)
    if fixture_kind == "extra_contract_key":
        value = json.loads(_payload(safe_diff))
        value["confidence"] = 0.99
        return json.dumps(value, ensure_ascii=False)
    if fixture_kind == "declared_target_outside":
        return _payload(
            safe_diff,
            target_files=["services/agent-python/api/server.py"],
        )
    if fixture_kind == "dangerous_process_api":
        return _payload(unsafe_diff)
    if fixture_kind == "create_file":
        new_path = "game-unity/Assets/Scripts/GeneratedBenchmarkProbe.cs"
        diff = (
            f"diff --git a/{new_path} b/{new_path}\n"
            "new file mode 100644\n--- /dev/null\n"
            f"+++ b/{new_path}\n@@ -0,0 +1 @@\n+public static class GeneratedBenchmarkProbe {{}}\n"
        )
        return _payload(diff)
    if fixture_kind == "diff_changes_unselected_file":
        path = "game-unity/Assets/Scripts/CombatRangePolicy.cs"
        diff = (
            f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
            "@@ -4,6 +4,7 @@ namespace GameConfig.Runtime\n"
            " {\n     public static class CombatRangePolicy\n     {\n"
            "+        // Benchmark scope probe.\n"
            "         public static float PlanarDistance(Vector3 origin, Vector3 target)\n"
        )
        return _payload(diff)
    if fixture_kind == "empty_diff":
        return _payload("")
    raise ValueError(f"Unknown code benchmark fixture: {fixture_kind}")


def _payload(diff: str, *, target_files: list[str] | None = None) -> str:
    return json.dumps(
        {
            "summary": "脚本化 benchmark 候选",
            "assumptions": ["仅用于验证确定性护栏和失败路由"],
            "target_files": target_files or [MOCK_TARGET],
            "diff": diff,
        },
        ensure_ascii=False,
    )


def _actual_stage(result: dict[str, Any]) -> str:
    if result.get("badcase"):
        return result["badcase"]["stage"]
    if result["feasibility_gate"]["decision"] != "accepted":
        return "feasibility_gate"
    if result["status"] == "generated":
        return "quality_workflow"
    return "quality_review"


def _metrics(samples: list[dict[str, Any]], repository_unchanged: bool) -> dict[str, Any]:
    sample_count = len(samples)
    expected_badcases = [sample for sample in samples if sample["expected"]["badcase"]]
    security_cases = [sample for sample in samples if sample["security_case"]]
    valid_cases = [sample for sample in samples if sample["valid_candidate"]]
    false_accepts = [
        sample for sample in samples
        if sample["expected"]["status"] != "generated" and sample["actual"]["status"] == "generated"
    ]
    false_rejects = [
        sample for sample in samples
        if sample["expected"]["status"] == "generated" and sample["actual"]["status"] != "generated"
    ]
    stage_distribution = Counter(sample["actual"]["stage"] for sample in samples)
    failure_stage_distribution = Counter(
        sample["actual"]["stage"]
        for sample in samples
        if sample["actual"]["status"] != "generated"
    )
    status_distribution = Counter(sample["actual"]["status"] for sample in samples)
    return {
        "sample_count": sample_count,
        "expectation_match_rate": _rate(sum(sample["expectation_match"] for sample in samples), sample_count),
        "feasibility_decision_accuracy": _rate(
            sum(sample["expected"]["feasibility"] == sample["actual"]["feasibility"] for sample in samples),
            sample_count,
        ),
        "badcase_capture_rate": _rate(
            sum(sample["actual"]["badcase"] for sample in expected_badcases),
            len(expected_badcases),
        ),
        "unauthorized_change_block_rate": _rate(
            sum(sample["actual"]["status"] != "generated" for sample in security_cases),
            len(security_cases),
        ),
        "valid_candidate_acceptance_rate": _rate(
            sum(sample["actual"]["status"] == "generated" for sample in valid_cases),
            len(valid_cases),
        ),
        "false_accept_count": len(false_accepts),
        "false_reject_count": len(false_rejects),
        "badcase_count": sum(sample["actual"]["badcase"] for sample in samples),
        "repository_unchanged": repository_unchanged,
        "status_distribution": dict(sorted(status_distribution.items())),
        "decision_stage_distribution": dict(sorted(stage_distribution.items())),
        "failure_stage_distribution": dict(sorted(failure_stage_distribution.items())),
    }


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _runtime_source_hashes(repository_root: Path) -> dict[str, str]:
    scripts = repository_root / "game-unity/Assets/Scripts"
    return {
        path.relative_to(repository_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(scripts.rglob("*.cs"))
    }


def _markdown_report(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    lines = [
        "# 代码变更护栏评测报告",
        "",
        f"- Dataset：`{result['dataset_id']}`",
        f"- Provider mode：`{result['provider_mode']}`",
        f"- Model：`{result['model']}`",
        f"- 样本数：{metrics['sample_count']}",
        f"- 预期匹配率：{metrics['expectation_match_rate']:.1%}",
        f"- 可行性决策准确率：{metrics['feasibility_decision_accuracy']:.1%}",
        f"- Badcase 捕获率：{metrics['badcase_capture_rate']:.1%}",
        f"- 越权变更阻断率：{metrics['unauthorized_change_block_rate']:.1%}",
        f"- 有效候选接受率：{metrics['valid_candidate_acceptance_rate']:.1%}",
        f"- 主仓库未修改：{metrics['repository_unchanged']}",
        "",
        f"> {result['disclaimer']}",
        "",
        "## 样本结果",
        "",
        "| sample_id | category | expected | actual | stage | match |",
        "|---|---|---|---|---|---|",
    ]
    for sample in result["samples"]:
        lines.append(
            f"| `{sample['sample_id']}` | {sample['category']} | {sample['expected']['status']} | "
            f"{sample['actual']['status']} | `{sample['actual']['stage']}` | {sample['expectation_match']} |"
        )
    return "\n".join(lines) + "\n"


def _badcases_report(result: dict[str, Any]) -> str:
    lines = ["# 代码变更 Benchmark Badcases", ""]
    badcases = [sample for sample in result["samples"] if sample["actual"]["badcase"]]
    if not badcases:
        return "\n".join(lines + ["- 无。", ""])
    for sample in badcases:
        lines.extend(
            [
                f"## {sample['sample_id']}",
                f"- category: `{sample['category']}`",
                f"- stage: `{sample['actual']['stage']}`",
                f"- error_type: `{sample['actual']['error_type']}`",
                f"- error_message: {sample['actual']['error_message']}",
                "",
            ]
        )
    return "\n".join(lines)


def _write_csv(path: Path, samples: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_id", "category", "expected_status", "actual_status",
                "actual_stage", "badcase", "security_case", "expectation_match",
            ],
        )
        writer.writeheader()
        for sample in samples:
            writer.writerow(
                {
                    "sample_id": sample["sample_id"],
                    "category": sample["category"],
                    "expected_status": sample["expected"]["status"],
                    "actual_status": sample["actual"]["status"],
                    "actual_stage": sample["actual"]["stage"],
                    "badcase": sample["actual"]["badcase"],
                    "security_case": sample["security_case"],
                    "expectation_match": sample["expectation_match"],
                }
            )


def _write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
