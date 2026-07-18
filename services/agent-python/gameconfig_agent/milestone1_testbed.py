"""Evaluate repeatability evidence from the Milestone 1 Unity greybox testbed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def evaluate_testbed_runs(profile: dict, primary: dict, repeat: dict) -> dict:
    expected = profile["expected"]
    seed = profile["seed"]
    scenario_id = profile["scenario_id"]
    run_mode = profile.get("run_mode", "auto")
    stable_fields = profile["stable_fields"]
    tolerance = float(profile.get("completion_time_tolerance_seconds", 1.0))

    checks = [
        _check(
            "profile_identity",
            primary.get("scenario_id") == scenario_id and repeat.get("scenario_id") == scenario_id,
            [primary.get("scenario_id"), repeat.get("scenario_id")],
            scenario_id,
        ),
        _check(
            "fixed_seed",
            primary.get("random_seed") == seed and repeat.get("random_seed") == seed,
            [primary.get("random_seed"), repeat.get("random_seed")],
            seed,
        ),
        _check(
            "auto_run_mode",
            primary.get("run_mode") == run_mode and repeat.get("run_mode") == run_mode,
            [primary.get("run_mode"), repeat.get("run_mode")],
            run_mode,
        ),
        _check(
            "runs_completed",
            primary.get("status") == expected["status"] and repeat.get("status") == expected["status"],
            [primary.get("status"), repeat.get("status")],
            expected["status"],
        ),
        _check(
            "waves_completed",
            _both_equal(primary, repeat, "waves_completed", expected["waves_completed"]),
            [primary.get("waves_completed"), repeat.get("waves_completed")],
            expected["waves_completed"],
        ),
        _check(
            "enemies_defeated",
            _both_equal(primary, repeat, "enemies_defeated", expected["enemies_defeated"]),
            [primary.get("enemies_defeated"), repeat.get("enemies_defeated")],
            expected["enemies_defeated"],
        ),
        _check(
            "skill_usage",
            _both_at_least(primary, repeat, "skill_uses", expected["skill_uses_min"]),
            [primary.get("skill_uses"), repeat.get("skill_uses")],
            f">= {expected['skill_uses_min']}",
        ),
        _check(
            "wave_evidence_complete",
            _wave_evidence_complete(primary, expected["waves_completed"])
            and _wave_evidence_complete(repeat, expected["waves_completed"]),
            [_wave_summary(primary), _wave_summary(repeat)],
            f"{expected['waves_completed']} completed wave records",
        ),
    ]

    mismatches = {
        field: [primary.get(field), repeat.get(field)]
        for field in stable_fields
        if field not in primary or field not in repeat or primary.get(field) != repeat.get(field)
    }
    checks.append(_check("stable_counters_repeatable", not mismatches, mismatches, "all stable fields equal"))

    primary_time = _number(primary.get("completion_time_seconds"))
    repeat_time = _number(repeat.get("completion_time_seconds"))
    time_delta = abs(primary_time - repeat_time) if primary_time is not None and repeat_time is not None else None
    checks.append(
        _check(
            "completion_time_repeatable",
            time_delta is not None and time_delta <= tolerance,
            {"primary": primary_time, "repeat": repeat_time, "delta": time_delta},
            f"delta <= {tolerance}s",
        )
    )

    failed_checks = [check for check in checks if not check["passed"]]
    return {
        "profile_version": profile["profile_version"],
        "profile_id": profile["profile_id"],
        "scenario_id": scenario_id,
        "seed": seed,
        "passed": not failed_checks,
        "check_count": len(checks),
        "passed_count": len(checks) - len(failed_checks),
        "repeatability_rate": (len(checks) - len(failed_checks)) / len(checks),
        "checks": checks,
        "failed_checks": failed_checks,
    }


def evaluate_testbed_files(
    profile_path: str | Path,
    primary_telemetry_path: str | Path,
    repeat_telemetry_path: str | Path,
    output_dir: str | Path,
) -> dict:
    profile = _load_json(profile_path)
    primary = _load_json(primary_telemetry_path)
    repeat = _load_json(repeat_telemetry_path)
    result = evaluate_testbed_runs(profile, primary, repeat)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "testbed_evaluation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (destination / "testbed_evaluation_report.md").write_text(_report(result), encoding="utf-8")
    return result


def _load_json(path: str | Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _both_equal(primary: dict, repeat: dict, field: str, expected: Any) -> bool:
    return primary.get(field) == expected and repeat.get(field) == expected


def _both_at_least(primary: dict, repeat: dict, field: str, minimum: int) -> bool:
    values = (primary.get(field), repeat.get(field))
    return all(isinstance(value, int) and value >= minimum for value in values)


def _wave_evidence_complete(telemetry: dict, expected_count: int) -> bool:
    waves = telemetry.get("wave_results")
    if not isinstance(waves, list) or len(waves) != expected_count:
        return False
    for expected_wave, wave in enumerate(waves, start=1):
        if not isinstance(wave, dict):
            return False
        if wave.get("wave") != expected_wave:
            return False
        if wave.get("enemies_spawned") != wave.get("enemies_defeated"):
            return False
        if not isinstance(wave.get("duration_seconds"), (int, float)) or wave["duration_seconds"] <= 0:
            return False
    return True


def _wave_summary(telemetry: dict) -> list[dict]:
    waves = telemetry.get("wave_results")
    if not isinstance(waves, list):
        return []
    return [
        {
            "wave": wave.get("wave"),
            "spawned": wave.get("enemies_spawned"),
            "defeated": wave.get("enemies_defeated"),
        }
        for wave in waves
        if isinstance(wave, dict)
    ]


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _check(check_id: str, passed: bool, actual: Any, expected: Any) -> dict:
    return {"check_id": check_id, "passed": passed, "actual": actual, "expected": expected}


def _report(result: dict) -> str:
    lines = [
        "# Milestone 1 灰盒自动战斗测试床报告",
        "",
        f"- 测试画像：`{result['profile_id']}`",
        f"- 场景：`{result['scenario_id']}`",
        f"- 固定种子：`{result['seed']}`",
        f"- 总结论：`{'通过' if result['passed'] else '失败'}`",
        f"- 可重复性检查：`{result['passed_count']}/{result['check_count']}`",
        "",
        "## 检查明细",
        "",
    ]
    for check in result["checks"]:
        status = "通过" if check["passed"] else "失败"
        lines.append(
            f"- **{status}** `{check['check_id']}`：实际 `{check['actual']}`；预期 `{check['expected']}`"
        )
    lines.extend(
        [
            "",
            "## 证据边界",
            "",
            "该报告证明同一配置和固定种子的灰盒自动试玩可重复，不代表真实玩家体验或统计学平衡结论。",
        ]
    )
    return "\n".join(lines) + "\n"
