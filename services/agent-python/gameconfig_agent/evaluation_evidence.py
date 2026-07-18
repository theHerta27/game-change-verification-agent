"""Case-aware evidence views over existing configs, validation, and Unity telemetry."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from gameconfig_agent.agents.repairer import ConfigRepairAgent
from gameconfig_agent.data.classic_cases import load_classic_case
from gameconfig_agent.data.design_reference import BALANCE_POLICY_LOOKUP
from gameconfig_agent.mock_llm import MockLLM
from gameconfig_agent.runtime_telemetry import RuntimeTelemetryNormalizer
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

EVALUATION_VIEWS = {
    "case_01_baseline_trial": "baseline evidence chain",
    "case_02_reward_overgrant": "first-clear reward economy risk",
    "case_03_combat_too_fast": "combat pacing risk",
    "case_04_missing_reference": "static missing-reference validation",
    "case_05_skill_guidance_balance": "weak skill-usage validation",
}


def build_evaluation_evidence(case_id: str, *, outputs_dir: Path = OUTPUTS_DIR) -> dict[str, Any]:
    case = load_classic_case(case_id)
    configs = _load_json(outputs_dir / "phase0" / "final_configs.json")
    telemetry_path = _latest_telemetry_path(outputs_dir / "unity")
    raw_telemetry = _load_json(telemetry_path) if telemetry_path else None
    normalized = RuntimeTelemetryNormalizer().normalize(raw_telemetry) if raw_telemetry is not None else None

    if case_id == "case_04_missing_reference":
        checks = _missing_reference_checks(configs)
        evidence_type = "static_validation"
        telemetry_source = None
    else:
        checks = _runtime_checks(case, configs, normalized)
        evidence_type = "runtime_evaluation"
        telemetry_source = {
            "label": "latest Training Sword Unity runtime run",
            "path": _relative_path(telemetry_path) if telemetry_path else None,
        }

    risks = [
        {"check_id": check["check_id"], "reason": check["risk_reason"]}
        for check in checks
        if check["status"] == "failed"
    ]
    recommendations = [
        {"check_id": check["check_id"], "suggestion": check["repair_suggestion"]}
        for check in checks
        if check["status"] == "failed"
    ]
    return {
        "case": case,
        "generation_mode": "deterministic_mock_training_sword",
        "evaluation_view": EVALUATION_VIEWS[case_id],
        "evidence_type": evidence_type,
        "telemetry_source": telemetry_source,
        "design_targets": case["expected_runtime_targets"],
        "normalized_telemetry": normalized,
        "checks": checks,
        "risks": risks,
        "recommendations": recommendations,
        "artifacts": _runtime_artifacts(outputs_dir / "unity"),
    }


def _runtime_checks(case: dict, configs: dict | None, normalized: dict | None) -> list[dict]:
    case_id = case["case_id"]
    targets = case["expected_runtime_targets"]
    if normalized is None:
        check_ids = {
            "case_01_baseline_trial": ["completion_time", "enemies_defeated", "skill_usage"],
            "case_03_combat_too_fast": ["completion_time"],
            "case_05_skill_guidance_balance": ["skill_usage", "completion_time"],
        }.get(case_id, [])
        checks = [
            _check(
                check_id,
                "unavailable",
                "unavailable",
                "unavailable",
                "telemetry artifact unavailable",
                "Telemetry is not available.",
                "Run the Unity auto-run smoke to generate telemetry.",
            )
            for check_id in check_ids
        ]
        if case_id in {"case_01_baseline_trial", "case_02_reward_overgrant"}:
            checks.extend(_economy_checks(configs, targets.get("reward_grants", {})))
        return checks

    values = normalized["values"]
    field_sources = normalized["field_sources"]
    checks: list[dict] = []
    if case_id in {"case_01_baseline_trial", "case_03_combat_too_fast", "case_05_skill_guidance_balance"}:
        time_target = targets["completion_time_seconds"]
        actual = values["completion_time_seconds"]
        source = field_sources["completion_time_seconds"]
        passed = actual != "unavailable" and time_target["min"] <= actual <= time_target["max"]
        checks.append(
            _check(
                "completion_time",
                f"{time_target['min']:.0f}-{time_target['max']:.0f}s",
                actual,
                "passed" if passed else "failed" if actual != "unavailable" else "unavailable",
                f"telemetry.{source}" if source else "telemetry field unavailable",
                "The measured clear time is outside the case acceptance range.",
                "Tune enemy durability, wave pressure, or player output, then rerun Unity.",
            )
        )
    if case_id == "case_01_baseline_trial":
        checks.append(_numeric_minimum_check("enemies_defeated", targets["enemies_defeated"], values, field_sources, exact=True))
    if case_id in {"case_01_baseline_trial", "case_05_skill_guidance_balance"}:
        checks.append(_numeric_minimum_check("skill_usage", targets["skill_uses_min"], values, field_sources))
    if case_id in {"case_01_baseline_trial", "case_02_reward_overgrant"}:
        checks.extend(_economy_checks(configs, targets.get("reward_grants", {})))
    return checks


def _numeric_minimum_check(check_id: str, target: int, values: dict, sources: dict, *, exact: bool = False) -> dict:
    field = "enemies_defeated" if check_id == "enemies_defeated" else "skill_uses"
    actual = values[field]
    passed = actual != "unavailable" and (actual == target if exact else actual >= target)
    expected = str(target) if exact else f">= {target}"
    return _check(
        check_id,
        expected,
        actual,
        "passed" if passed else "failed" if actual != "unavailable" else "unavailable",
        f"telemetry.{sources[field]}" if sources[field] else "telemetry field unavailable",
        "The runtime observation does not satisfy the case target.",
        "Review encounter configuration and rerun the same telemetry scenario.",
    )


def _economy_checks(configs: dict | None, reward_grants: dict[str, int]) -> list[dict]:
    upgrades_value = configs.get("upgrade_config") if isinstance(configs, dict) else None
    if (
        not isinstance(upgrades_value, list)
        or len(upgrades_value) < 2
        or not all(isinstance(row, dict) for row in upgrades_value[:2])
        or not reward_grants
    ):
        return [
            _check("first_upgrade", "affordable", "unavailable", "unavailable", "classic case profile + upgrade_config", "Economy inputs are incomplete.", "Regenerate final_configs and keep the case reward profile available."),
            _check("second_upgrade_after_first", "not affordable", "unavailable", "unavailable", "classic case profile + upgrade_config", "Economy inputs are incomplete.", "Regenerate final_configs and keep the case reward profile available."),
        ]
    upgrades = sorted(upgrades_value, key=lambda row: row.get("level", 0))
    first_cost = _cost_vector(upgrades[0])
    second_cost = _cost_vector(upgrades[1])
    first_affordable = _can_afford(reward_grants, first_cost)
    remaining = {item_id: amount - first_cost.get(item_id, 0) for item_id, amount in reward_grants.items()}
    second_affordable = first_affordable and _can_afford(remaining, second_cost)
    evidence = "classic_cases.reward_grants + upgrade_config.cost_items"
    return [
        _check("first_upgrade", "affordable", first_affordable, "passed" if first_affordable else "failed", evidence, "The first upgrade cannot be purchased from the first-clear inventory.", "Adjust reward grants or first-level costs."),
        _check("second_upgrade_after_first", "not affordable", second_affordable, "failed" if second_affordable else "passed", evidence, "The first-clear inventory can fund two consecutive upgrades.", "Reduce one or more reward resources or raise the second-level multi-resource cost."),
    ]


def _missing_reference_checks(configs: dict | None) -> list[dict]:
    if configs is None:
        return [_check("trial_medal_reference", "reference resolves", "unavailable", "unavailable", "phase0/final_configs.json", "Static config is unavailable.", "Run the deterministic demo first.")]
    draft = deepcopy(configs)
    draft["upgrade_config"][0]["cost_items"].append({"item_id": "item_trial_medal", "amount": 1})
    draft["item_config"] = [item for item in draft["item_config"] if item.get("item_id") != "item_trial_medal"]
    errors = ReferenceCheckerTool().check(draft)
    trial_errors = [error for error in errors if error.get("value") == "item_trial_medal"]

    requirement, _ = MockLLM().infer_training_sword_requirement("classic case 04")
    blackboard = {
        "structured_requirement": requirement,
        "design_reference": BALANCE_POLICY_LOOKUP,
        "draft_configs": draft,
    }
    ConfigRepairAgent().repair(blackboard)
    repair_actions = [
        action for action in blackboard["repair_actions"]
        if isinstance(action.get("after"), dict)
        and action["after"].get("item_id") == "item_trial_medal"
    ]
    return [
        _check("trial_medal_reference", "reference resolves", "missing item_trial_medal", "failed" if trial_errors else "passed", "Reference Checker: upgrade_config[0].cost_items -> item_config.item_id", "upgrade_config references Trial Medal without an item definition.", "Add the catalog-backed Trial Medal item definition before export."),
        _check("trial_medal_repair", "bounded repair recorded", bool(repair_actions), "passed" if repair_actions else "failed", "Config Repair Agent repair_actions", "The known missing resource was not repaired.", "Allow bounded repair only for IDs in RESOURCE_ITEM_CATALOG."),
    ]


def _cost_vector(upgrade: dict) -> dict[str, int]:
    cost_items = upgrade.get("cost_items")
    if not isinstance(cost_items, list):
        return {}
    return {
        item["item_id"]: item["amount"]
        for item in cost_items
        if isinstance(item, dict) and isinstance(item.get("item_id"), str) and isinstance(item.get("amount"), int)
    }


def _can_afford(inventory: dict[str, int], cost: dict[str, int]) -> bool:
    return all(inventory.get(item_id, 0) >= amount for item_id, amount in cost.items())


def _check(check_id: str, target: object, actual: object, status: str, evidence: str, risk_reason: str, repair_suggestion: str) -> dict:
    return {
        "check_id": check_id,
        "target": target,
        "actual": actual,
        "status": status,
        "evidence": evidence,
        "risk_reason": risk_reason,
        "repair_suggestion": repair_suggestion,
    }


def _latest_telemetry_path(directory: Path) -> Path | None:
    candidates = [path for path in directory.glob("telemetry*.json") if path.is_file()] if directory.exists() else []
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _runtime_artifacts(directory: Path) -> list[dict]:
    names = ("telemetry.json", "telemetry_hotfix.json", "runtime_evaluation_report.md")
    return [
        {"name": name, "path": f"unity/{name}", "size": (directory / name).stat().st_size}
        for name in names
        if (directory / name).is_file()
    ]


def _load_json(path: Path | None) -> dict | None:
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)
