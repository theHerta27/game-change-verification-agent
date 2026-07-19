"""Deterministic config-change primitives for the Milestone 3A workflow."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import json

from gameconfig_agent.data.design_reference import BALANCE_POLICY_LOOKUP
from gameconfig_agent.requirement_intake import analyze_requirement
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool
from gameconfig_agent.tools.rule_engine import RuleEngineTool
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


SUPPORTED_CONSTRAINTS = {
    "weapon_config.base_attack",
    "structured_requirement.upgrade_times",
    "runtime_target_config.completion_time_seconds",
    "runtime_target_config.enemies_defeated",
    "runtime_target_config.skill_uses_min",
    "reward_config.reward_items[item_gold].amount",
}


def load_baseline_configs(contract_path: Path) -> dict[str, Any]:
    """Load the committed Unity contract and expose schema-valid config groups."""
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    configs = deepcopy(contract["configs"])
    scenario = contract["runtime_scenario"]
    configs["enemy_config"] = [
        {
            **enemy,
            "role": enemy.get("role", "elite" if "elite" in enemy["enemy_id"] else "normal"),
        }
        for enemy in scenario.get("enemies", [])
    ]
    configs["wave_config"] = deepcopy(scenario.get("waves", []))
    configs["skill_config"] = [deepcopy(scenario["skill"])] if scenario.get("skill") else []
    targets = scenario.get("targets", {})
    configs["runtime_target_config"] = [
        {
            "target_id": "target_starter_trial",
            "completion_time_seconds_min": targets.get("completion_time_seconds_min", 20.0),
            "completion_time_seconds_max": targets.get("completion_time_seconds_max", 150.0),
            "enemies_defeated": targets.get(
                "enemies_defeated",
                sum(row.get("count", 0) for row in scenario.get("waves", [])),
            ),
            "skill_uses_min": targets.get("skill_uses_min", 1),
            "first_upgrade_affordable": targets.get("first_upgrade_affordable", True),
            "second_upgrade_affordable": targets.get("second_upgrade_affordable", False),
        }
    ]
    return configs


def build_structured_requirement(configs: dict[str, Any]) -> dict[str, Any]:
    weapon = configs["weapon_config"][0]
    upgrades = configs["upgrade_config"]
    return {
        "request_id": "req_starter_trial_change",
        "item_name": configs["item_config"][0]["display_name"],
        "category": "beginner_weapon",
        "base_attack": weapon["base_attack"],
        "upgrade_times": len(upgrades),
        "upgrade_attack_bonus": upgrades[0]["attack_bonus"],
        "cost_item_tags": ["gold", "refine_stone"],
        "reward_channel": "beginner_quest",
        "once_only": True,
    }


def run_feasibility_gate(requirement_text: str) -> dict[str, Any]:
    intake = analyze_requirement(requirement_text)
    result = {
        **intake,
        "gate": "change_feasibility",
        "config_only": True,
        "requires_code_change": False,
        "supported_constraints": sorted(SUPPORTED_CONSTRAINTS),
        "out_of_range": [],
    }
    if result["decision"] != "accepted":
        return result

    conflicts = _constraint_conflicts(result["constraints"])
    out_of_range = [
        issue
        for constraint in result["constraints"]
        if (issue := _range_issue(constraint)) is not None
    ]
    unsupported = [
        constraint["target_field"]
        for constraint in result["constraints"]
        if constraint["target_field"] not in SUPPORTED_CONSTRAINTS
    ]
    if conflicts:
        result.update(
            decision="needs_clarification",
            reason="同一个配置字段出现互相冲突的目标，请保留一个明确值。",
            conflicts=conflicts,
        )
    elif out_of_range:
        result.update(
            decision="rejected",
            reason="需求中的数值超出当前 Starter Trial 安全边界。",
            out_of_range=out_of_range,
        )
    elif unsupported:
        result.update(
            decision="rejected",
            reason="需求包含当前能力清单尚未支持的配置字段。",
            unsupported_constraints=unsupported,
        )
    return result


def apply_constraints(
    baseline: dict[str, Any],
    constraints: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    candidate = deepcopy(baseline)
    structured = build_structured_requirement(candidate)
    actions: list[dict[str, Any]] = []
    for constraint in constraints:
        field = constraint["target_field"]
        value = constraint["value"]
        before: Any
        if field == "weapon_config.base_attack":
            before = candidate["weapon_config"][0]["base_attack"]
            candidate["weapon_config"][0]["base_attack"] = value
            structured["base_attack"] = value
        elif field == "structured_requirement.upgrade_times":
            before = len(candidate["upgrade_config"])
            candidate["upgrade_config"] = _resize_upgrades(candidate["upgrade_config"], value)
            structured["upgrade_times"] = value
        elif field == "runtime_target_config.completion_time_seconds":
            target = candidate["runtime_target_config"][0]
            before = [target["completion_time_seconds_min"], target["completion_time_seconds_max"]]
            target["completion_time_seconds_min"], target["completion_time_seconds_max"] = value
        elif field == "runtime_target_config.enemies_defeated":
            target = candidate["runtime_target_config"][0]
            before = target["enemies_defeated"]
            target["enemies_defeated"] = value
        elif field == "runtime_target_config.skill_uses_min":
            target = candidate["runtime_target_config"][0]
            before = target["skill_uses_min"]
            target["skill_uses_min"] = value
        elif field == "reward_config.reward_items[item_gold].amount":
            reward = candidate["reward_config"][0]
            reward_items = reward.setdefault("reward_items", [])
            gold = next((row for row in reward_items if row.get("item_id") == "item_gold"), None)
            before = gold.get("amount") if gold else None
            if gold is None:
                reward_items.append({"item_id": "item_gold", "amount": value})
            else:
                gold["amount"] = value
        else:
            continue
        actions.append(
            {
                "action": "apply_requirement_constraint",
                "target_field": field,
                "operator": constraint["operator"],
                "before": before,
                "after": value,
                "source_text": constraint["source_text"],
            }
        )
    return candidate, structured, actions


def validate_candidate(structured_requirement: dict[str, Any], configs: dict[str, Any]) -> dict[str, Any]:
    schema_errors = SchemaValidatorTool().validate(structured_requirement, configs)
    reference_errors = ReferenceCheckerTool().check(configs) if not schema_errors else []
    rule_errors = (
        RuleEngineTool().evaluate(structured_requirement, configs)["violations"]
        if not schema_errors
        else []
    )
    return {
        "passed": not (schema_errors or reference_errors or rule_errors),
        "schema_errors": schema_errors,
        "reference_errors": reference_errors,
        "rule_errors": rule_errors,
    }


def build_config_diff(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else key
            if key not in before:
                changes.append(_change("added", child, None, after[key]))
            elif key not in after:
                changes.append(_change("removed", child, before[key], None))
            else:
                changes.extend(build_config_diff(before[key], after[key], child))
        return changes
    if isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            child = f"{path}[{index}]"
            if index >= len(before):
                changes.append(_change("added", child, None, after[index]))
            elif index >= len(after):
                changes.append(_change("removed", child, before[index], None))
            else:
                changes.extend(build_config_diff(before[index], after[index], child))
        return changes
    if before != after:
        changes.append(_change("modified", path, before, after))
    return changes


def build_quality_review(
    constraints: list[dict[str, Any]],
    candidate: dict[str, Any],
    config_diff: list[dict[str, Any]],
    static_validation: dict[str, Any],
) -> dict[str, Any]:
    coverage = []
    for constraint in constraints:
        actual = _constraint_actual(candidate, constraint["target_field"])
        coverage.append(
            {
                "target_field": constraint["target_field"],
                "expected": constraint["value"],
                "actual": actual,
                "passed": actual == constraint["value"],
                "evidence": f"candidate_configs.{constraint['target_field']}",
            }
        )

    findings: list[dict[str, Any]] = []
    base_attack = candidate["weapon_config"][0]["base_attack"]
    attack_range = BALANCE_POLICY_LOOKUP["beginner_weapon"]["base_attack_range"]
    if not attack_range[0] <= base_attack <= attack_range[1]:
        findings.append(
            {
                "severity": "high",
                "category": "balance_risk",
                "title": "新手武器攻击力超出设计参考范围",
                "evidence": {"actual": base_attack, "recommended_range": attack_range},
                "suggestion": "确认是否有意提高新手战斗速度，并通过 Unity 固定种子试玩验证通关时间。",
            }
        )
    if not config_diff:
        findings.append(
            {
                "severity": "low",
                "category": "no_effective_change",
                "title": "当前需求没有改变基线字段",
                "evidence": {"change_count": 0},
                "suggestion": "如需比较效果，请在需求中明确攻击力、通关时间、击败数或技能使用目标。",
            }
        )
    if not static_validation["passed"]:
        findings.append(
            {
                "severity": "critical",
                "category": "invalid_candidate",
                "title": "候选配置未通过确定性校验",
                "evidence": static_validation,
                "suggestion": "修正结构、引用或规则错误后重新创建变更提案。",
            }
        )

    changed_paths = [item["path"] for item in config_diff]
    tests = [
        {
            "test_id": "static_contract_validation",
            "type": "deterministic",
            "reason": "所有配置变更都必须重新执行 Schema、Reference 和 Rule 校验。",
        }
    ]
    if any(path.startswith(("weapon_config", "enemy_config", "wave_config", "skill_config", "runtime_target_config")) for path in changed_paths):
        tests.append(
            {
                "test_id": "unity_fixed_seed_playtest",
                "type": "runtime",
                "reason": "战斗或运行目标变化需要固定种子自动试玩和 telemetry 对比。",
            }
        )
    if any(path.startswith(("upgrade_config", "reward_config")) for path in changed_paths):
        tests.append(
            {
                "test_id": "first_clear_economy_check",
                "type": "deterministic",
                "reason": "升级或奖励变化需要验证首通后第一次与第二次升级可支付性。",
            }
        )
    approval_recommended = (
        static_validation["passed"]
        and all(item["passed"] for item in coverage)
        and not any(item["severity"] == "critical" for item in findings)
    )
    return {
        "reviewer": "Quality Review Agent",
        "approval_recommended": approval_recommended,
        "requirement_coverage": coverage,
        "findings": findings,
        "test_suggestions": tests,
        "summary": "候选配置可以进入人工审批。" if approval_recommended else "候选配置需要修订后再审批。",
    }


def review_runtime_evidence(runtime_run: dict[str, Any]) -> dict[str, Any]:
    evaluation = runtime_run.get("evaluation") or {}
    failed_checks = [check for check in evaluation.get("checks", []) if not check.get("passed")]
    return {
        "reviewer": "Quality Review Agent",
        "evidence_complete": runtime_run.get("status") == "evaluated" and bool(evaluation),
        "runtime_passed": evaluation.get("passed", False),
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
        "recommendation": "accept" if evaluation.get("passed") else "revise",
        "summary": (
            "Unity 运行证据达到全部当前目标，可以提交人工接受。"
            if evaluation.get("passed")
            else "Unity 已完成，但存在未达到的策划目标；建议修订配置，人工仍可带说明接受。"
        ),
    }


def _resize_upgrades(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    policy = BALANCE_POLICY_LOOKUP["beginner_weapon"]
    existing = {row["level"]: deepcopy(row) for row in rows}
    result = []
    for index, level in enumerate(range(1, count + 1)):
        row = existing.get(level, deepcopy(rows[-1]))
        row["level"] = level
        row["cost_items"] = [
            {"item_id": "item_gold", "amount": policy["recommended_gold_cost"][index]},
            {"item_id": "item_refine_stone", "amount": policy["recommended_refine_stone_cost"][index]},
        ]
        result.append(row)
    return result


def _constraint_actual(configs: dict[str, Any], field: str) -> Any:
    if field == "weapon_config.base_attack":
        return configs["weapon_config"][0]["base_attack"]
    if field == "structured_requirement.upgrade_times":
        return len(configs["upgrade_config"])
    if field == "runtime_target_config.completion_time_seconds":
        target = configs["runtime_target_config"][0]
        return [target["completion_time_seconds_min"], target["completion_time_seconds_max"]]
    if field == "runtime_target_config.enemies_defeated":
        return configs["runtime_target_config"][0]["enemies_defeated"]
    if field == "runtime_target_config.skill_uses_min":
        return configs["runtime_target_config"][0]["skill_uses_min"]
    if field == "reward_config.reward_items[item_gold].amount":
        for item in configs["reward_config"][0].get("reward_items", []):
            if item.get("item_id") == "item_gold":
                return item.get("amount")
    return None


def _constraint_conflicts(constraints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values: dict[str, list[Any]] = {}
    for constraint in constraints:
        values.setdefault(constraint["target_field"], []).append(constraint["value"])
    return [
        {"target_field": field, "values": items}
        for field, items in values.items()
        if any(item != items[0] for item in items[1:])
    ]


def _range_issue(constraint: dict[str, Any]) -> dict[str, Any] | None:
    field = constraint["target_field"]
    value = constraint["value"]
    ranges = {
        "weapon_config.base_attack": (1, 200),
        "structured_requirement.upgrade_times": (1, 3),
        "runtime_target_config.enemies_defeated": (1, 20),
        "runtime_target_config.skill_uses_min": (0, 100),
        "reward_config.reward_items[item_gold].amount": (1, 1_000_000),
    }
    if field == "runtime_target_config.completion_time_seconds":
        valid = isinstance(value, list) and len(value) == 2 and 5 <= value[0] < value[1] <= 600
        return None if valid else {"target_field": field, "value": value, "allowed": [5, 600]}
    if field in ranges:
        minimum, maximum = ranges[field]
        if not minimum <= value <= maximum:
            return {"target_field": field, "value": value, "allowed": [minimum, maximum]}
    return None


def _change(change_type: str, path: str, before: Any, after: Any) -> dict[str, Any]:
    return {"change_type": change_type, "path": path, "before": before, "after": after}
