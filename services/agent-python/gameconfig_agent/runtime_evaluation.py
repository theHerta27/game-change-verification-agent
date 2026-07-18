"""Evaluate Unity telemetry against the runtime scenario's design targets."""

from __future__ import annotations

import json
import math
from pathlib import Path


def evaluate_runtime(contract: dict, telemetry: dict) -> dict:
    scenario = contract["runtime_scenario"]
    targets = scenario["targets"]
    configs = contract["configs"]
    base_attack = configs["weapon_config"][0]["base_attack"]
    normal_enemies = scenario["enemies"][:-1]
    hits_to_kill = {
        enemy["enemy_id"]: math.ceil(enemy["max_health"] / base_attack)
        for enemy in normal_enemies
    }

    upgrades = sorted(configs["upgrade_config"], key=lambda row: row["level"])
    costs = [_cost_vector(row) for row in upgrades]
    inventory = _reward_inventory(configs, telemetry)
    first_affordable = bool(costs) and _can_afford(inventory, costs[0])
    after_first = _subtract_cost(inventory, costs[0]) if first_affordable else inventory
    second_affordable = len(costs) > 1 and _can_afford(after_first, costs[1])

    checks = [
        _check("run_completed", telemetry.get("status") == "completed", telemetry.get("status"), "completed"),
        _check(
            "completion_time_in_target",
            targets["completion_time_seconds_min"] <= telemetry.get("completion_time_seconds", 0) <= targets["completion_time_seconds_max"],
            telemetry.get("completion_time_seconds", 0),
            [targets["completion_time_seconds_min"], targets["completion_time_seconds_max"]],
        ),
        _check(
            "normal_enemy_hits_to_kill_in_target",
            all(targets["normal_enemy_hits_to_kill_min"] <= value <= targets["normal_enemy_hits_to_kill_max"] for value in hits_to_kill.values()),
            hits_to_kill,
            [targets["normal_enemy_hits_to_kill_min"], targets["normal_enemy_hits_to_kill_max"]],
        ),
        _check("first_upgrade_affordable", first_affordable == targets["first_upgrade_affordable"], first_affordable, targets["first_upgrade_affordable"]),
        _check("second_upgrade_affordable", second_affordable == targets["second_upgrade_affordable"], second_affordable, targets["second_upgrade_affordable"]),
    ]
    if "enemies_defeated" in targets:
        checks.append(
            _check(
                "enemies_defeated_in_target",
                telemetry.get("enemies_defeated", 0) == targets["enemies_defeated"],
                telemetry.get("enemies_defeated", 0),
                targets["enemies_defeated"],
            )
        )
    if "skill_uses_min" in targets:
        checks.append(
            _check(
                "skill_uses_in_target",
                telemetry.get("skill_uses", 0) >= targets["skill_uses_min"],
                telemetry.get("skill_uses", 0),
                f">= {targets['skill_uses_min']}",
            )
        )
    failed_checks = [check for check in checks if not check["passed"]]
    return {
        "scenario_id": scenario["scenario_id"],
        "passed": not failed_checks,
        "check_count": len(checks),
        "passed_count": len(checks) - len(failed_checks),
        "runtime_target_pass_rate": (len(checks) - len(failed_checks)) / len(checks),
        "checks": checks,
        "failed_checks": failed_checks,
    }


def evaluate_runtime_files(contract_path: str | Path, telemetry_path: str | Path, output_dir: str | Path) -> dict:
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    telemetry = json.loads(Path(telemetry_path).read_text(encoding="utf-8"))
    result = evaluate_runtime(contract, telemetry)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "runtime_evaluation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "runtime_evaluation_report.md").write_text(_report(result), encoding="utf-8")
    return result


def _reward_inventory(configs: dict, telemetry: dict) -> dict[str, int]:
    rewards = configs.get("reward_config", [])
    reward_items = [
        reward_item
        for reward in rewards
        if isinstance(reward, dict)
        for reward_item in reward.get("reward_items", [])
        if isinstance(reward_item, dict)
    ]
    if not reward_items:
        return {"item_gold": int(telemetry.get("gold_earned", 0))}
    inventory: dict[str, int] = {}
    for reward_item in reward_items:
        item_id = reward_item.get("item_id")
        amount = reward_item.get("amount")
        if isinstance(item_id, str) and isinstance(amount, int):
            inventory[item_id] = inventory.get(item_id, 0) + amount
    return inventory


def _cost_vector(upgrade: dict) -> dict[str, int]:
    cost: dict[str, int] = {}
    for item in upgrade.get("cost_items", []):
        if not isinstance(item, dict):
            continue
        item_id = item.get("item_id")
        amount = item.get("amount")
        if isinstance(item_id, str) and isinstance(amount, int):
            cost[item_id] = cost.get(item_id, 0) + amount
    return cost


def _can_afford(inventory: dict[str, int], cost: dict[str, int]) -> bool:
    return all(inventory.get(item_id, 0) >= amount for item_id, amount in cost.items())


def _subtract_cost(inventory: dict[str, int], cost: dict[str, int]) -> dict[str, int]:
    remaining = dict(inventory)
    for item_id, amount in cost.items():
        remaining[item_id] = remaining.get(item_id, 0) - amount
    return remaining


def _check(check_id: str, passed: bool, actual: object, expected: object) -> dict:
    return {"check_id": check_id, "passed": passed, "actual": actual, "expected": expected}


def _report(result: dict) -> str:
    lines = [
        "# Unity Runtime Evaluation Report",
        "",
        f"- Scenario: `{result['scenario_id']}`",
        f"- Passed: `{result['passed']}`",
        f"- Target pass rate: `{result['runtime_target_pass_rate']:.1%}`",
        f"- Checks: `{result['passed_count']}/{result['check_count']}`",
        "",
        "## Checks",
        "",
    ]
    for check in result["checks"]:
        mark = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- **{mark}** `{check['check_id']}`: actual `{check['actual']}`, expected `{check['expected']}`")
    return "\n".join(lines) + "\n"
