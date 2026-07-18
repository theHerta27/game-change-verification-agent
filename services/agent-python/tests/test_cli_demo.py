import subprocess
import sys
from pathlib import Path


def test_cli_demo_generates_all_outputs(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "phase0"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "gameconfig_agent.cli",
            "run_demo",
            "--input",
            str(project_root / "examples" / "training_sword_requirement.txt"),
            "--output",
            str(output_dir),
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Final Validation: passed" in result.stdout
    expected_files = {
        "draft_configs.json",
        "final_configs.json",
        "blackboard_trace.json",
        "validation_report.md",
        "risk_report.md",
        "repair_trace.md",
    }
    assert expected_files == {path.name for path in output_dir.iterdir()}
