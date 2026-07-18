from __future__ import annotations

import json
from pathlib import Path

from agent_service.evaluation.dataset import load_evaluation_dataset
from agent_service.evaluation.runner import run_phase4_evaluation


def test_evaluation_dataset_has_phase4_sample_size() -> None:
    samples = load_evaluation_dataset()

    assert 30 <= len(samples) <= 50
    assert {sample.language for sample in samples} == {"go", "python"}
    assert any(not sample.expected_findings for sample in samples)
    assert any(sample.expected_findings for sample in samples)


def test_phase4_evaluation_writes_reports(tmp_path: Path) -> None:
    result = run_phase4_evaluation(project_root=tmp_path, output_dir=tmp_path / "phase4")

    assert result["dataset_size"] >= 30
    assert (tmp_path / "phase4" / "evaluation_result.json").exists()
    assert (tmp_path / "phase4" / "evaluation_report.md").exists()
    assert (tmp_path / "phase4" / "badcases.md").exists()
    assert (tmp_path / "phase4" / "comparison_report.md").exists()
    assert (tmp_path / "phase4" / "phase4_summary.md").exists()
    assert (tmp_path / "phase4" / "single_vs_dual_metrics.csv").exists()
    assert (tmp_path / "phase4" / "single_vs_dual_comparison.png").stat().st_size > 0

    payload = json.loads((tmp_path / "phase4" / "evaluation_result.json").read_text(encoding="utf-8"))
    assert payload["workflows"]["single_agent"]["metrics"]["json_valid_rate"] == 1.0
    assert payload["workflows"]["dual_agent"]["metrics"]["validator_pass_rate"] == 1.0
    assert payload["workflows"]["single_agent"]["metrics"]["avg_latency_ms"] > 0
    assert payload["comparison"]["summary"]["samples_compared"] == payload["dataset_size"]
