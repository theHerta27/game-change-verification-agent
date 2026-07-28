from pathlib import Path

from workflow.bullet_hell_benchmark import load_bullet_hell_benchmark, run_bullet_hell_benchmark


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_bullet_hell_benchmark_has_twenty_versioned_samples():
    dataset = load_bullet_hell_benchmark(REPOSITORY_ROOT)

    assert dataset["dataset_id"] == "bullet_hell_change_v1"
    assert len(dataset["samples"]) == 20
    assert len({row["sample_id"] for row in dataset["samples"]}) == 20
    assert "不代表真实模型质量" in dataset["disclaimer"]


def test_benchmark_writes_reports_and_routes_expected_cases(tmp_path):
    result = run_bullet_hell_benchmark(REPOSITORY_ROOT, tmp_path)

    assert result["metrics"]["sample_count"] == 20
    assert result["metrics"]["expectation_match_rate"] == 1.0
    assert result["metrics"]["unsafe_request_block_rate"] == 1.0
    assert result["metrics"]["repair_success_rate"] == 1.0
    assert result["metrics"]["false_accept_count"] == 0
    assert (tmp_path / "benchmark_results.json").is_file()
    assert (tmp_path / "evaluation_report.md").is_file()
    assert (tmp_path / "sample_summary.csv").is_file()
    assert (tmp_path / "badcases.md").is_file()
