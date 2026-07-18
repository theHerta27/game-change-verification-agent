import csv
import subprocess
import sys
from pathlib import Path

from gameconfig_agent.data.benchmark_dataset import BENCHMARK_SAMPLES
from gameconfig_agent.phase3_benchmark import run_phase3_benchmark


def test_phase3_benchmark_dataset_has_required_coverage():
    assert 8 <= len(BENCHMARK_SAMPLES) <= 12
    tags = {tag for sample in BENCHMARK_SAMPLES for tag in sample["tags"]}
    required = {
        "beginner weapon",
        "rare weapon",
        "upgrade cost",
        "reward once_only",
        "duplicate reward",
        "skill damage config",
        "level reward curve",
        "missing reference",
        "safe balanced config",
    }
    assert required <= tags


def test_phase3_benchmark_runner_generates_artifacts(tmp_path):
    result = run_phase3_benchmark(tmp_path)

    assert result["metrics"]["sample_count"] == len(BENCHMARK_SAMPLES)
    assert result["metrics"]["badcase_count"] >= 1
    assert result["metrics"]["unresolved_count"] >= 1
    assert result["metrics"]["avg_repair_actions"] >= 0

    expected = {
        "benchmark_results.json",
        "evaluation_report.md",
        "badcases.md",
        "sample_summary.csv",
    }
    assert expected == {path.name for path in tmp_path.iterdir()}

    with (tmp_path / "sample_summary.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(BENCHMARK_SAMPLES)


def test_phase3_cli_command(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "gameconfig_agent.cli",
            "run_phase3_benchmark",
            "--output",
            str(tmp_path),
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "GameConfig Agent Phase 3 Benchmark" in result.stdout
    assert (tmp_path / "benchmark_results.json").exists()
