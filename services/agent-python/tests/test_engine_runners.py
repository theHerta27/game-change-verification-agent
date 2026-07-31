from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from gameconfig_agent.bullet_hell import load_bullet_hell_contract
from workflow.engines.telemetry import config_sha256
from workflow.engines.unity import UnityEngineRunner
from workflow.engines.unreal import UnrealEngineRunner


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = REPOSITORY_ROOT / "configs" / "bullet-hell" / "baseline.json"


def test_unity_environment_distinguishes_build_required_from_available(tmp_path):
    repository = tmp_path / "repo"
    (repository / "game-unity").mkdir(parents=True)
    editor = tmp_path / "Unity.exe"
    editor.write_bytes(b"editor")
    player = repository / "game-unity" / "Builds" / "BulletHellDemo.exe"
    runner = UnityEngineRunner(
        repository_root=repository,
        executable=player,
        editor_executable=editor,
    )

    assert runner.validate_environment()["status"] == "build_required"
    player.parent.mkdir(parents=True)
    player.write_bytes(b"player")
    assert runner.validate_environment()["status"] == "available"


def test_unreal_environment_never_reports_available_without_real_project_and_player(tmp_path):
    runner = UnrealEngineRunner(repository_root=tmp_path)

    assert runner.validate_environment()["status"] == "unavailable"
    assert runner.capabilities()["automated_run"] is False
    with pytest.raises(FileNotFoundError, match="Registered UE5 Player"):
        runner.automated_run(
            contract={},
            run_dir=tmp_path / "runtime-artifacts" / "run",
            seed=20260727,
            run_id="test",
            variant="baseline",
        )


def test_unreal_runner_uses_fixed_player_validates_evidence_and_marks_verified(
    tmp_path,
    monkeypatch,
):
    repository = tmp_path / "repo"
    project = repository / "game-unreal" / "BulletHellUE"
    project.mkdir(parents=True)
    (project / "BulletHellUE.uproject").write_text("{}", encoding="utf-8")
    executable = project / "Builds" / "Windows" / "BulletHellUE.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"player")
    runner = UnrealEngineRunner(repository_root=repository)
    contract = load_bullet_hell_contract(BASELINE_PATH)
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        value = lambda prefix: next(row.removeprefix(prefix) for row in command if row.startswith(prefix))
        telemetry_path = Path(value("-TelemetryOutput="))
        screenshot_dir = Path(value("-ScreenshotDir="))
        config_hash = value("-ConfigHash=")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        telemetry_path.write_text(
            json.dumps(
                {
                    "status": "completed",
                    "completed": True,
                    "engine_version": "5.8.1",
                    "build_id": "test-build",
                    "config_hash": config_hash,
                    "duration_seconds": 36,
                    "total_bullets_spawned": 600,
                    "peak_alive_bullets": 100,
                    "player_hits": 0,
                    "player_survival_seconds": 36,
                    "phase_results": [{"phase_id": "phase_1"}],
                    "average_fps": 60,
                    "low_percentile_fps": 59,
                    "minimum_fps": 50,
                    "runtime_error_count": 0,
                }
            ),
            encoding="utf-8",
        )
        for second in (10, 20, 30):
            (screenshot_dir / f"capture_{second:02d}s.png").write_bytes(b"png")
        (screenshot_dir / "capture_manifest.json").write_text(
            json.dumps({"config_hash": config_hash}),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("workflow.engines.unreal.subprocess.run", fake_run)
    for variant in ("baseline", "candidate_1"):
        result = runner.automated_run(
            contract=contract,
            run_dir=repository / "runtime-artifacts" / "workflow" / variant,
            seed=20260727,
            run_id="workflow_ue_candidate_iteration",
            variant=variant,
            capture_times=(10, 20, 30),
        )
        assert result.normalized_evidence["engine_name"] == "unreal"
        assert result.normalized_evidence["completed"] is True

    assert commands[0][0] == str(executable)
    assert "-Automated" in commands[0]
    assert any(row.startswith("-ConfigInput=") for row in commands[0])
    assert any(row.startswith("-ConfigFileHash=") for row in commands[0])
    assert runner.validate_environment()["status"] == "verified"


def test_unreal_runner_rejects_paths_outside_runtime_artifacts(tmp_path):
    repository = tmp_path / "repo"
    project = repository / "game-unreal" / "BulletHellUE"
    project.mkdir(parents=True)
    (project / "BulletHellUE.uproject").write_text("{}", encoding="utf-8")
    executable = project / "Builds" / "Windows" / "BulletHellUE.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"player")
    runner = UnrealEngineRunner(repository_root=repository)
    contract = load_bullet_hell_contract(BASELINE_PATH)

    with pytest.raises(ValueError, match="must remain under"):
        runner.automated_run(
            contract=contract,
            run_dir=repository / "outside",
            seed=20260727,
            run_id="workflow_ue",
            variant="baseline",
        )


def test_unity_automated_run_uses_registered_player_and_normalizes_without_mutating_raw(
    tmp_path,
    monkeypatch,
):
    repository = tmp_path / "repo"
    project = repository / "game-unity"
    project.mkdir(parents=True)
    executable = project / "Builds" / "BulletHellDemo.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"player")
    runner = UnityEngineRunner(repository_root=repository, executable=executable)
    contract = load_bullet_hell_contract(BASELINE_PATH)
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        telemetry_path = Path(command[command.index("--telemetry-output") + 1])
        telemetry_path.write_text(
            json.dumps(
                {
                    "status": "completed",
                    "duration_seconds": 36,
                    "total_bullets_spawned": 592,
                    "peak_alive_bullets": 66,
                    "player_hits": 2,
                    "player_survival_seconds": 36,
                    "phase_results": [{"phase_id": "phase_1"}],
                    "average_fps": 60,
                    "low_percentile_fps": 58.7,
                    "minimum_fps": 50,
                    "exception_log_count": 0,
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("workflow.engines.unity.subprocess.run", fake_run)
    result = runner.automated_run(
        contract=contract,
        run_dir=tmp_path / "run",
        seed=20260727,
        run_id="workflow_1",
        variant="baseline",
    )

    assert commands[0][0] == str(executable)
    assert "--config-input" in commands[0]
    assert result.telemetry["exception_log_count"] == 0
    assert "engine_name" not in result.telemetry
    assert result.normalized_evidence["engine_name"] == "unity"
    assert result.normalized_evidence["config_hash"] == config_sha256(contract)
    assert result.normalized_evidence["completed"] is True


def test_normalized_completion_is_distinct_from_gameplay_validation_failure(tmp_path, monkeypatch):
    repository = tmp_path / "repo"
    project = repository / "game-unity"
    project.mkdir(parents=True)
    executable = project / "Builds" / "BulletHellDemo.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"player")
    runner = UnityEngineRunner(repository_root=repository, executable=executable)
    contract = load_bullet_hell_contract(BASELINE_PATH)

    def fake_run(command, **_kwargs):
        telemetry_path = Path(command[command.index("--telemetry-output") + 1])
        telemetry_path.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "duration_seconds": 18,
                    "player_survival_seconds": 18,
                    "phase_results": [],
                    "exception_log_count": 0,
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr("workflow.engines.unity.subprocess.run", fake_run)
    result = runner.automated_run(
        contract=contract,
        run_dir=tmp_path / "run",
        seed=20260727,
        run_id="workflow_2",
        variant="candidate",
    )

    assert result.exit_code == 1
    assert result.normalized_evidence["completed"] is True
    assert result.normalized_evidence["validation_outcome"] == "failed"
