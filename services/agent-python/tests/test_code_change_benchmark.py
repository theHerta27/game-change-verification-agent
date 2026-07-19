import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.server import create_unified_app
from gameconfig_agent.cli import main
from workflow.code_change_benchmark import load_code_change_benchmark, run_code_change_benchmark


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_dataset_is_versioned_unique_and_covers_required_failures():
    dataset = load_code_change_benchmark(REPOSITORY_ROOT)
    samples = dataset["samples"]

    assert dataset["dataset_id"] == "code_change_guardrail_benchmark_v1"
    assert dataset["provider_mode"] == "scripted_fixture"
    assert len(samples) == 12
    assert len({sample["sample_id"] for sample in samples}) == len(samples)
    assert {
        "valid_candidate",
        "requirement_scope",
        "target_scope",
        "provider_output",
        "generation_contract",
        "patch_safety",
    }.issubset({sample["category"] for sample in samples})


def test_runner_exports_metrics_failures_and_never_prepares_workspace(tmp_path: Path):
    result = run_code_change_benchmark(REPOSITORY_ROOT, tmp_path)
    metrics = result["metrics"]

    assert metrics["sample_count"] == 12
    assert metrics["expectation_match_rate"] == 1
    assert metrics["feasibility_decision_accuracy"] == 1
    assert metrics["badcase_capture_rate"] == 1
    assert metrics["unauthorized_change_block_rate"] == 1
    assert metrics["valid_candidate_acceptance_rate"] == 1
    assert metrics["false_accept_count"] == 0
    assert metrics["false_reject_count"] == 0
    assert metrics["repository_unchanged"] is True
    assert metrics["badcase_count"] == 7
    assert "quality_workflow" not in metrics["failure_stage_distribution"]
    assert metrics["decision_stage_distribution"]["quality_workflow"] == 1
    assert not list(tmp_path.rglob("workspace"))
    assert {
        "benchmark_results.json",
        "evaluation_report.md",
        "badcases.md",
        "sample_summary.csv",
    }.issubset({path.name for path in tmp_path.iterdir()})


def test_cli_runs_code_change_benchmark(tmp_path: Path):
    exit_code = main(
        [
            "run_code_change_benchmark",
            "--output",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    result = json.loads((tmp_path / "benchmark_results.json").read_text(encoding="utf-8"))
    assert result["metrics"]["expectation_match_rate"] == 1


def test_api_exposes_dataset_and_executes_benchmark(tmp_path: Path):
    client = TestClient(create_unified_app(code_change_benchmark_dir=tmp_path))

    dataset = client.get("/api/code-change-agent/benchmark/dataset")
    result = client.post("/api/code-change-agent/benchmark")

    assert dataset.status_code == 200
    assert dataset.json()["sample_count"] == 12
    assert dataset.json()["provider_mode"] == "scripted_fixture"
    assert result.status_code == 200
    assert result.json()["metrics"]["unauthorized_change_block_rate"] == 1
