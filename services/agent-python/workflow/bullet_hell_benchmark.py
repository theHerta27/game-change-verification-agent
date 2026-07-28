"""Offline regression benchmark for the Bullet Hell bounded workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import json

from gameconfig_agent.bullet_hell import (
    apply_repair,
    choose_repair_action,
    evaluate_bullet_hell_telemetry,
    load_bullet_hell_contract,
    propose_mock_change,
    simulate_telemetry,
    validate_bullet_hell_contract,
    write_json,
)


def load_bullet_hell_benchmark(repository_root: Path) -> dict[str, Any]:
    path = repository_root / "evals" / "bullet_hell_benchmark_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run_bullet_hell_benchmark(repository_root: Path, output_dir: Path) -> dict[str, Any]:
    dataset = load_bullet_hell_benchmark(repository_root)
    baseline = load_bullet_hell_contract(repository_root / "configs" / "bullet-hell" / "baseline.json")
    results = [_evaluate_sample(baseline, sample) for sample in dataset["samples"]]
    accepted = [row for row in results if row["actual_decision"] == "accepted"]
    repair_rows = [row for row in results if row["category"] == "repair_required"]
    unsafe_rows = [row for row in results if row["category"] == "unsafe"]
    metrics = {
        "sample_count": len(results),
        "expectation_match_rate": _rate(row["expectation_matched"] for row in results),
        "schema_pass_rate": _rate(row["schema_passed"] for row in accepted),
        "single_shot_runtime_pass_rate": _rate(row["single_shot_passed"] for row in accepted),
        "full_loop_runtime_pass_rate": _rate(row["full_loop_passed"] for row in accepted),
        "repair_success_rate": _rate(row["repair_succeeded"] for row in repair_rows),
        "unsafe_request_block_rate": _rate(row["actual_decision"] == "blocked" for row in unsafe_rows),
        "false_accept_count": sum(row["actual_decision"] == "accepted" and row["expected_decision"] != "accepted" for row in results),
        "average_candidate_runs": round(sum(row["candidate_runs"] for row in accepted) / len(accepted), 3) if accepted else 0,
    }
    payload = {
        "dataset_id": dataset["dataset_id"],
        "provider_mode": dataset["provider_mode"],
        "disclaimer": dataset["disclaimer"],
        "metrics": metrics,
        "samples": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "benchmark_results.json", payload)
    _write_report(output_dir / "evaluation_report.md", payload)
    _write_csv(output_dir / "sample_summary.csv", results)
    _write_badcases(output_dir / "badcases.md", results)
    return payload


def _evaluate_sample(baseline: dict[str, Any], sample: dict[str, Any]) -> dict[str, Any]:
    candidate, goal, gate = propose_mock_change(baseline, sample["requirement"])
    validation = validate_bullet_hell_contract(candidate)
    actual_decision = gate["decision"]
    if actual_decision == "accepted" and not validation["passed"]:
        actual_decision = "blocked"
    expected_pattern = sample.get("expected_pattern")
    pattern_matched = True
    if expected_pattern and goal:
        phase_id = goal["target_phase_id"]
        phase = next(row for row in candidate["phases"] if row["phase_id"] == phase_id)
        pattern_matched = phase["pattern"]["type"] == expected_pattern

    single_shot_passed = False
    full_loop_passed = False
    repair_succeeded = sample["category"] != "repair_required"
    candidate_runs = 0
    repairs: list[str] = []
    if actual_decision == "accepted":
        current = candidate
        for iteration in range(1, 4):
            candidate_runs = iteration
            telemetry = simulate_telemetry(current)
            if iteration == 1:
                _inject_fault(telemetry, sample.get("runtime_fault"))
            evaluation = evaluate_bullet_hell_telemetry(current, telemetry)
            if iteration == 1:
                single_shot_passed = evaluation["passed"]
            if evaluation["passed"]:
                full_loop_passed = True
                repair_succeeded = sample["category"] != "repair_required" or iteration > 1
                break
            action = choose_repair_action(evaluation)
            current, evidence = apply_repair(current, action, evaluation)
            repairs.append(action)
            if not evidence["applied"] or not validate_bullet_hell_contract(current)["passed"]:
                break

    expectation_matched = actual_decision == sample["expected_decision"] and pattern_matched
    return {
        "sample_id": sample["sample_id"],
        "category": sample["category"],
        "expected_decision": sample["expected_decision"],
        "actual_decision": actual_decision,
        "expectation_matched": expectation_matched,
        "schema_passed": validation["passed"],
        "pattern_matched": pattern_matched,
        "single_shot_passed": single_shot_passed,
        "full_loop_passed": full_loop_passed,
        "repair_succeeded": repair_succeeded,
        "candidate_runs": candidate_runs,
        "repair_actions": repairs,
    }


def _inject_fault(telemetry: dict[str, Any], fault: str | None) -> None:
    if fault == "peak_alive_bullets":
        telemetry["peak_alive_bullets"] = 420
    elif fault == "low_percentile_fps":
        telemetry["low_percentile_fps"] = 42
    elif fault == "player_hits":
        telemetry["player_hits"] = 8
    elif fault == "survival_time":
        telemetry["status"] = "failed"
        telemetry["player_survival_seconds"] = 18


def _rate(values) -> float:
    rows = list(values)
    return round(sum(bool(value) for value in rows) / len(rows), 4) if rows else 0.0


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload["metrics"]
    lines = [
        "# Bullet Hell 配置变更离线评测",
        "",
        f"> {payload['disclaimer']}",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
    ]
    for key, value in metrics.items():
        rendered = f"{value * 100:.2f}%" if key.endswith("_rate") else str(value)
        lines.append(f"| `{key}` | {rendered} |")
    lines.extend(["", "## 样本", "", "| sample_id | category | expected | actual | full loop |", "|---|---|---|---|---|"])
    for row in payload["samples"]:
        lines.append(
            f"| {row['sample_id']} | {row['category']} | {row['expected_decision']} | "
            f"{row['actual_decision']} | {'通过' if row['full_loop_passed'] else '未运行/未通过'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "sample_id", "category", "expected_decision", "actual_decision", "expectation_matched",
        "schema_passed", "single_shot_passed", "full_loop_passed", "repair_succeeded", "candidate_runs",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_badcases(path: Path, rows: list[dict[str, Any]]) -> None:
    badcases = [row for row in rows if not row["expectation_matched"]]
    lines = ["# Bullet Hell Benchmark Badcases", "", f"Badcase count: {len(badcases)}", ""]
    for row in badcases:
        lines.extend(
            [
                f"## {row['sample_id']}",
                f"- category: `{row['category']}`",
                f"- expected: `{row['expected_decision']}`",
                f"- actual: `{row['actual_decision']}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
