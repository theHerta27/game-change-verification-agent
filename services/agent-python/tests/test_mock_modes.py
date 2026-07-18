import subprocess
import sys
from pathlib import Path


def test_cli_supports_invalid_json_mock_case(tmp_path):
    project = Path(__file__).resolve().parents[1]
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
            "--mock-case",
            "invalid_json",
            "--output",
            str(tmp_path / "invalid.md"),
        ],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "invalid mock llm output" in result.stdout


def test_cli_supports_timeout_mock_case(tmp_path):
    project = Path(__file__).resolve().parents[1]
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
            "--mock-case",
            "timeout",
            "--output",
            str(tmp_path / "timeout.md"),
        ],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "mock llm timeout" in result.stdout

