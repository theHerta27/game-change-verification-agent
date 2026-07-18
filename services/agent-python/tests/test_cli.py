import subprocess
import sys
from pathlib import Path


def test_cli_runs_one_example(tmp_path):
    project = Path(__file__).resolve().parents[1]
    report_path = tmp_path / "report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_service.cli",
            "review",
            "--diff",
            "examples/go_http_no_timeout.patch",
            "--language",
            "go",
            "--mode",
            "mock",
            "--output",
            str(report_path),
        ],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "\"findings\"" in result.stdout
    assert "validator_passed=True" in result.stderr
    assert report_path.exists()
    assert "DevQuality Agent 代码审查报告" in report_path.read_text(encoding="utf-8")


def test_cli_help_documents_workflow_argument():
    project = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "agent_service.cli", "review", "-h"],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--workflow" in result.stdout
    assert "{single_agent,dual_agent}" in result.stdout


def test_cli_runs_dual_agent_workflow(tmp_path):
    project = Path(__file__).resolve().parents[1]
    report_path = tmp_path / "dual_report.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_service.cli",
            "review",
            "--diff",
            "examples/go_http_no_timeout.patch",
            "--language",
            "go",
            "--mode",
            "mock",
            "--workflow",
            "dual_agent",
            "--output",
            str(report_path),
        ],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "validator_passed=True" in result.stderr
    assert '"agent_name":"review_agent"' in result.stdout.replace(" ", "")
    assert '"agent_name":"test_agent"' in result.stdout.replace(" ", "")
    assert report_path.exists()
