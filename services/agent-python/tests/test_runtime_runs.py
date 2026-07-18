import json
from pathlib import Path

import pytest

from gameconfig_agent.runtime_runs import RuntimeRunService


STRUCTURED_REQUIREMENT = {
    "request_id": "req_training_sword_beginner_weapon",
    "item_name": "Training Sword",
    "category": "beginner_weapon",
    "base_attack": 50,
    "upgrade_times": 3,
    "upgrade_attack_bonus": 5,
    "cost_item_tags": ["gold", "refine_stone"],
    "reward_channel": "beginner_quest",
    "once_only": True,
}


def _service(tmp_path: Path, launches: list[tuple[list[str], Path]]) -> RuntimeRunService:
    executable = tmp_path / "GameConfigRuntimeDemo.exe"
    executable.write_bytes(b"fixture")
    (tmp_path / "guided_runtime_version.txt").write_text("guided-runtime-v1", encoding="utf-8")

    def launcher(command: list[str], cwd: Path) -> int:
        launches.append((command, cwd))
        return 4321

    return RuntimeRunService(
        runs_dir=tmp_path / "runtime_runs",
        unity_executable=executable,
        launcher=launcher,
        process_checker=lambda _process_id: True,
    )


def test_prepare_creates_isolated_run_artifacts_and_case_targets(tmp_path):
    service = _service(tmp_path, [])

    run = service.prepare(
        case_id="case_03_combat_too_fast",
        requirement_text="创建标准 Training Sword 试炼。",
    )

    run_dir = service.runs_dir / run["run_id"]
    assert run["status"] == "prepared"
    assert len(run["config_hash"]) == 64
    assert run["steps"]["unity_play"] == "ready"
    assert (run_dir / "requirement.txt").is_file()
    assert (run_dir / "final_configs.json").is_file()
    contract = json.loads((run_dir / "unity_contract.json").read_text(encoding="utf-8"))
    assert contract["runtime_scenario"]["targets"]["completion_time_seconds_min"] == 60.0
    assert contract["runtime_scenario"]["targets"]["completion_time_seconds_max"] == 90.0


def test_static_only_case_cannot_prepare_unity_run(tmp_path):
    service = _service(tmp_path, [])

    with pytest.raises(ValueError, match="static validation"):
        service.prepare(
            case_id="case_04_missing_reference",
            requirement_text="检查 Trial Medal 引用。",
        )


def test_real_provider_prepare_revalidates_and_snapshots_exact_configs(tmp_path):
    service = _service(tmp_path, [])
    mock = service.prepare(
        case_id="case_01_baseline_trial",
        requirement_text="创建标准 Training Sword 试炼。",
    )
    mock_configs = json.loads(
        (service.runs_dir / mock["run_id"] / "final_configs.json").read_text(encoding="utf-8")
    )

    real = service.prepare(
        case_id="case_01_baseline_trial",
        requirement_text="创建标准 Training Sword 试炼。",
        provider="openai_compatible",
        structured_requirement=STRUCTURED_REQUIREMENT,
        final_configs=mock_configs,
        model="test-model",
    )

    real_dir = service.runs_dir / real["run_id"]
    assert real["provider"] == "openai_compatible"
    assert real["model"] == "test-model"
    assert real["static_validation"]["passed"] is True
    assert json.loads((real_dir / "final_configs.json").read_text(encoding="utf-8")) == mock_configs


def test_real_provider_prepare_rejects_dirty_configs(tmp_path):
    service = _service(tmp_path, [])

    with pytest.raises(ValueError, match="Final static validation failed"):
        service.prepare(
            case_id="case_01_baseline_trial",
            requirement_text="创建标准 Training Sword 试炼。",
            provider="openai_compatible",
            structured_requirement=STRUCTURED_REQUIREMENT,
            final_configs={"item_config": {}},
            model="test-model",
        )


def test_launch_uses_only_isolated_contract_and_telemetry_paths(tmp_path):
    launches: list[tuple[list[str], Path]] = []
    service = _service(tmp_path, launches)
    prepared = service.prepare(
        case_id="case_01_baseline_trial",
        requirement_text="创建标准 Training Sword 试炼。",
    )

    launched = service.launch(prepared["run_id"], mode="manual")

    command, cwd = launches[0]
    run_dir = service.runs_dir / prepared["run_id"]
    assert launched["status"] == "launched"
    assert launched["process_id"] == 4321
    assert command[command.index("--config-input") + 1] == str(run_dir / "unity_contract.json")
    assert command[command.index("--telemetry-output") + 1] == str(run_dir / "telemetry.json")
    assert "--auto-run" not in command
    assert cwd == service.unity_executable.parent


def test_launch_rejects_player_without_guided_runtime_marker(tmp_path):
    service = _service(tmp_path, [])
    (tmp_path / "guided_runtime_version.txt").unlink()
    prepared = service.prepare(
        case_id="case_01_baseline_trial",
        requirement_text="创建标准 Training Sword 试炼。",
    )

    with pytest.raises(FileNotFoundError, match="must be rebuilt"):
        service.launch(prepared["run_id"], mode="manual")


def test_status_evaluates_new_telemetry_and_records_suggestions(tmp_path):
    service = _service(tmp_path, [])
    prepared = service.prepare(
        case_id="case_03_combat_too_fast",
        requirement_text="创建节奏目标为 60 到 90 秒的 Training Sword 试炼。",
    )
    run_dir = service.runs_dir / prepared["run_id"]
    (run_dir / "telemetry.json").write_text(
        json.dumps({"status": "completed", "completion_time_seconds": 16.45, "gold_earned": 300}),
        encoding="utf-8",
    )

    completed = service.get(prepared["run_id"])

    assert completed["status"] == "evaluated"
    assert completed["evaluation"]["passed"] is False
    assert completed["steps"]["improvement_suggestions"] == "completed"
    assert any(item["check_id"] == "completion_time_in_target" for item in completed["improvement_suggestions"])
    assert (run_dir / "runtime_evaluation_report.md").is_file()


def test_status_records_process_exit_without_telemetry(tmp_path):
    executable = tmp_path / "GameConfigRuntimeDemo.exe"
    executable.write_bytes(b"fixture")
    (tmp_path / "guided_runtime_version.txt").write_text("guided-runtime-v1", encoding="utf-8")
    service = RuntimeRunService(
        runs_dir=tmp_path / "runtime_runs",
        unity_executable=executable,
        launcher=lambda _command, _cwd: 9999,
        process_checker=lambda _process_id: False,
    )
    prepared = service.prepare(
        case_id="case_01_baseline_trial",
        requirement_text="创建标准 Training Sword 试炼。",
    )
    service.launch(prepared["run_id"], mode="manual")

    failed = service.get(prepared["run_id"])

    assert failed["status"] == "failed"
    assert failed["error"]["type"] == "UnityProcessExited"
