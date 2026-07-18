import json

from gameconfig_agent.milestone1_testbed import evaluate_testbed_files, evaluate_testbed_runs


def _profile() -> dict:
    return {
        "profile_version": "1.0",
        "profile_id": "test_profile",
        "scenario_id": "scenario_beginner_trial_arena",
        "run_mode": "auto",
        "seed": 42,
        "completion_time_tolerance_seconds": 1.0,
        "expected": {
            "status": "completed",
            "waves_completed": 3,
            "enemies_defeated": 5,
            "skill_uses_min": 1,
        },
        "stable_fields": [
            "status",
            "scenario_id",
            "run_mode",
            "random_seed",
            "simulation_ticks",
            "waves_completed",
            "enemies_defeated",
            "basic_attacks",
            "skill_uses",
            "damage_dealt",
        ],
    }


def _telemetry(completion_time: float = 15.2) -> dict:
    return {
        "status": "completed",
        "scenario_id": "scenario_beginner_trial_arena",
        "run_mode": "auto",
        "random_seed": 42,
        "simulation_ticks": 820,
        "waves_completed": 3,
        "enemies_defeated": 5,
        "basic_attacks": 27,
        "skill_uses": 2,
        "damage_dealt": 1750,
        "completion_time_seconds": completion_time,
        "wave_results": [
            {"wave": 1, "enemies_spawned": 2, "enemies_defeated": 2, "duration_seconds": 3.0},
            {"wave": 2, "enemies_spawned": 2, "enemies_defeated": 2, "duration_seconds": 4.0},
            {"wave": 3, "enemies_spawned": 1, "enemies_defeated": 1, "duration_seconds": 8.0},
        ],
    }


def test_repeatable_fixed_seed_runs_pass() -> None:
    result = evaluate_testbed_runs(_profile(), _telemetry(15.2), _telemetry(15.7))

    assert result["passed"] is True
    assert result["repeatability_rate"] == 1.0
    assert result["failed_checks"] == []


def test_counter_drift_is_reported() -> None:
    repeat = _telemetry()
    repeat["basic_attacks"] = 28

    result = evaluate_testbed_runs(_profile(), _telemetry(), repeat)

    assert result["passed"] is False
    stable = next(check for check in result["checks"] if check["check_id"] == "stable_counters_repeatable")
    assert stable["actual"]["basic_attacks"] == [27, 28]


def test_file_evaluation_writes_json_and_chinese_report(tmp_path) -> None:
    profile_path = tmp_path / "profile.json"
    primary_path = tmp_path / "telemetry.json"
    repeat_path = tmp_path / "telemetry_repeat.json"
    profile_path.write_text(json.dumps(_profile()), encoding="utf-8")
    primary_path.write_text(json.dumps(_telemetry()), encoding="utf-8")
    repeat_path.write_text(json.dumps(_telemetry()), encoding="utf-8")

    result = evaluate_testbed_files(profile_path, primary_path, repeat_path, tmp_path / "result")

    assert result["passed"] is True
    assert (tmp_path / "result" / "testbed_evaluation.json").is_file()
    report = (tmp_path / "result" / "testbed_evaluation_report.md").read_text(encoding="utf-8")
    assert "灰盒自动战斗测试床报告" in report
    assert "真实玩家体验" in report
