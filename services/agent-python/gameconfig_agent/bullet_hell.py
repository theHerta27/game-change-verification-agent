"""Bullet Hell 1.0 contract and deterministic verification tools."""

from __future__ import annotations

from copy import deepcopy
from math import ceil
from pathlib import Path
from typing import Any, Literal
import json
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


PatternType = Literal["ring", "aimed_fan", "spiral", "petal"]
RepairAction = Literal[
    "REDUCE_BULLETS_PER_WAVE",
    "INCREASE_WAVE_INTERVAL",
    "REDUCE_BULLET_SPEED",
    "REDUCE_BULLET_LIFETIME",
    "REDUCE_PATTERN_LAYERS",
    "PRESERVE_VISUAL_STYLE",
    "REQUEST_HUMAN",
    "STOP",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScenarioConfig(StrictModel):
    scenario_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    duration_seconds: float = Field(ge=30, le=60)
    arena_width: float = Field(ge=8, le=20)
    arena_height: float = Field(ge=12, le=28)


class PlayerConfig(StrictModel):
    max_health: int = Field(ge=1, le=20)
    move_speed: float = Field(ge=1, le=12)
    focus_speed_multiplier: float = Field(gt=0, le=1)
    hit_radius: float = Field(gt=0, le=1)
    start_x: float = Field(ge=-10, le=10)
    start_z: float = Field(ge=-14, le=14)
    auto_fire_damage: int = Field(ge=1, le=100)
    auto_fire_interval_seconds: float = Field(ge=0.05, le=1)


class BossConfig(StrictModel):
    boss_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    max_health: int = Field(ge=100, le=100_000)
    position_x: float = Field(ge=-10, le=10)
    position_z: float = Field(ge=-14, le=14)


class PhaseTrigger(StrictModel):
    type: Literal["boss_hp_below"]
    value: float = Field(gt=0, le=1)


class PatternConfig(StrictModel):
    type: PatternType
    bullets_per_wave: int = Field(ge=1, le=64)
    wave_interval_ms: int = Field(ge=100, le=5000)
    bullet_speed: float = Field(ge=0.5, le=12)
    bullet_lifetime_seconds: float = Field(ge=0.5, le=12)
    rotation_per_wave_deg: float = Field(ge=-180, le=180)
    spread_angle_deg: float = Field(ge=1, le=360)
    layer_count: int = Field(ge=1, le=4)
    bidirectional: bool = False

    @model_validator(mode="after")
    def validate_pattern_shape(self) -> "PatternConfig":
        if self.type == "aimed_fan" and self.spread_angle_deg > 180:
            raise ValueError("aimed_fan spread_angle_deg must be <= 180")
        if self.type == "petal" and self.layer_count < 2:
            raise ValueError("petal layer_count must be >= 2")
        return self


class BossPhase(StrictModel):
    phase_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    trigger: PhaseTrigger
    pattern: PatternConfig


class SafetyConstraints(StrictModel):
    max_alive_bullets: int = Field(ge=1, le=350)
    min_fps: float = Field(ge=1, le=240)
    max_player_hits: int = Field(ge=0, le=20)


class RuntimeTargets(StrictModel):
    max_alive_bullets: int = Field(ge=1, le=350)
    max_player_hits: int = Field(ge=0, le=20)
    min_survival_seconds: float = Field(ge=1, le=60)
    min_fps: float = Field(ge=1, le=240)
    require_all_phases: bool = True


class BulletHellContract(StrictModel):
    bullet_hell_contract_version: Literal["1.0"]
    source: str = Field(min_length=1)
    scenario: ScenarioConfig
    player: PlayerConfig
    boss: BossConfig
    phases: list[BossPhase] = Field(min_length=2, max_length=3)
    constraints: SafetyConstraints
    runtime_targets: RuntimeTargets

    @model_validator(mode="after")
    def validate_phases(self) -> "BulletHellContract":
        identifiers = [phase.phase_id for phase in self.phases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("phase_id values must be unique")
        triggers = [phase.trigger.value for phase in self.phases]
        if triggers != sorted(triggers, reverse=True):
            raise ValueError("phase trigger values must be ordered from high to low")
        if self.runtime_targets.min_survival_seconds > self.scenario.duration_seconds:
            raise ValueError("min_survival_seconds cannot exceed scenario duration")
        if self.runtime_targets.max_alive_bullets > self.constraints.max_alive_bullets:
            raise ValueError("runtime target cannot exceed max_alive_bullets constraint")
        return self


def load_bullet_hell_contract(path: Path) -> dict[str, Any]:
    return BulletHellContract.model_validate_json(path.read_text(encoding="utf-8")).model_dump(mode="json")


def validate_bullet_hell_contract(value: Any) -> dict[str, Any]:
    try:
        contract = BulletHellContract.model_validate(value)
    except ValidationError as exc:
        return {
            "passed": False,
            "schema_errors": [
                {
                    "path": ".".join(str(part) for part in error["loc"]),
                    "error_type": error["type"],
                    "message": error["msg"],
                }
                for error in exc.errors()
            ],
            "rule_errors": [],
            "estimates": [],
        }

    estimates = [
        {
            "phase_id": phase.phase_id,
            "estimated_peak_alive_bullets": estimate_peak_alive(phase.pattern),
        }
        for phase in contract.phases
    ]
    rule_errors: list[dict[str, Any]] = []
    for estimate in estimates:
        if estimate["estimated_peak_alive_bullets"] > contract.constraints.max_alive_bullets:
            rule_errors.append(
                {
                    "rule_id": "estimated_alive_bullet_limit",
                    "path": f"phases[{estimate['phase_id']}].pattern",
                    "actual": estimate["estimated_peak_alive_bullets"],
                    "limit": contract.constraints.max_alive_bullets,
                    "message": "预计同时存活子弹数超过安全约束。",
                }
            )
    return {
        "passed": not rule_errors,
        "schema_errors": [],
        "rule_errors": rule_errors,
        "estimates": estimates,
    }


def validate_bullet_hell_proposal(
    *,
    baseline: dict[str, Any],
    candidate: Any,
    structured_goal: Any,
) -> dict[str, Any]:
    """Run the four explicit validation layers used before engine execution."""
    contract_validation = validate_bullet_hell_contract(candidate)
    schema_errors = contract_validation["schema_errors"]
    rule_errors = contract_validation["rule_errors"]
    reference_errors: list[dict[str, Any]] = []
    safety_errors: list[dict[str, Any]] = []

    if not schema_errors:
        parsed_candidate = BulletHellContract.model_validate(candidate).model_dump(mode="json")
        parsed_baseline = BulletHellContract.model_validate(baseline).model_dump(mode="json")
        phase_ids = [row["phase_id"] for row in parsed_candidate["phases"]]
        target_phase = structured_goal.get("target_phase_id") if isinstance(structured_goal, dict) else None
        requested_pattern = structured_goal.get("requested_pattern") if isinstance(structured_goal, dict) else None
        if not isinstance(structured_goal, dict):
            reference_errors.append(
                {
                    "reference_id": "structured_goal_required",
                    "path": "structured_goal",
                    "message": "structured_goal must be an object.",
                }
            )
        if target_phase not in phase_ids:
            reference_errors.append(
                {
                    "reference_id": "target_phase_exists",
                    "path": "structured_goal.target_phase_id",
                    "actual": target_phase,
                    "available": phase_ids,
                    "message": "目标阶段不存在于候选配置。",
                }
            )
        if requested_pattern not in {"ring", "aimed_fan", "spiral", "petal"}:
            reference_errors.append(
                {
                    "reference_id": "pattern_capability",
                    "path": "structured_goal.requested_pattern",
                    "actual": requested_pattern,
                    "message": "需求引用了 Bullet Hell 1.0 未支持的 Pattern。",
                }
            )
        elif target_phase in phase_ids:
            target = next(row for row in parsed_candidate["phases"] if row["phase_id"] == target_phase)
            if target["pattern"]["type"] != requested_pattern:
                reference_errors.append(
                    {
                        "reference_id": "goal_candidate_alignment",
                        "path": f"phases[{target_phase}].pattern.type",
                        "expected": requested_pattern,
                        "actual": target["pattern"]["type"],
                        "message": "候选 Pattern 与结构化需求不一致。",
                    }
                )

        baseline_phase_ids = [row["phase_id"] for row in parsed_baseline["phases"]]
        if phase_ids != baseline_phase_ids:
            safety_errors.append(
                {
                    "safety_id": "phase_identity_immutable",
                    "path": "phases",
                    "expected": baseline_phase_ids,
                    "actual": phase_ids,
                    "message": "配置变更不得新增、删除或重命名阶段。",
                }
            )
        allowed_prefixes = ("phases[", "constraints.", "runtime_targets.")
        for change in build_config_diff(parsed_baseline, parsed_candidate):
            path = change["path"]
            phase_pattern_change = path.startswith("phases[") and "].pattern." in path
            allowed = phase_pattern_change or path.startswith(allowed_prefixes[1:])
            if not allowed:
                safety_errors.append(
                    {
                        "safety_id": "candidate_write_scope",
                        "path": path,
                        "message": "候选只能修改 Pattern、约束和运行目标。",
                    }
                )

    layers = {
        "schema": {"passed": not schema_errors, "errors": schema_errors},
        "reference": {"passed": not reference_errors, "errors": reference_errors},
        "rule_engine": {
            "passed": not rule_errors,
            "errors": rule_errors,
            "estimates": contract_validation["estimates"],
        },
        "safety_gate": {"passed": not safety_errors, "errors": safety_errors},
    }
    return {
        "passed": all(layer["passed"] for layer in layers.values()),
        "schema_errors": schema_errors,
        "reference_errors": reference_errors,
        "rule_errors": rule_errors,
        "safety_errors": safety_errors,
        "estimates": contract_validation["estimates"],
        "layers": layers,
    }


def estimate_peak_alive(pattern: PatternConfig | dict[str, Any]) -> int:
    row = pattern if isinstance(pattern, PatternConfig) else PatternConfig.model_validate(pattern)
    waves_alive = ceil(row.bullet_lifetime_seconds * 1000 / row.wave_interval_ms)
    direction_factor = 2 if row.bidirectional else 1
    return waves_alive * row.bullets_per_wave * row.layer_count * direction_factor


def propose_mock_change(
    baseline: dict[str, Any],
    requirement_text: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    text = requirement_text.strip()
    if not text:
        return deepcopy(baseline), {}, _gate("needs_clarification", "请描述要修改的阶段、弹幕模式或运行目标。")
    if _is_unrelated(text):
        return deepcopy(baseline), {}, _gate("needs_clarification", "需求未描述弹幕玩法、阶段或验证目标。")

    unsafe = _unsafe_request(text)
    if unsafe:
        return deepcopy(baseline), {}, _gate(
            "blocked",
            "需求明确超过 Bullet Hell 1.0 安全边界，未生成或运行候选配置。",
            unsafe,
        )

    candidate = deepcopy(baseline)
    phase_index = _phase_index(text, len(candidate["phases"]))
    phase = candidate["phases"][phase_index]
    pattern = phase["pattern"]
    requested_pattern = _pattern_from_text(text)
    if requested_pattern:
        pattern["type"] = requested_pattern
        if requested_pattern == "petal":
            pattern["layer_count"] = max(2, pattern["layer_count"])
        if requested_pattern == "aimed_fan":
            pattern["spread_angle_deg"] = min(pattern["spread_angle_deg"], 100)
    if "双向" in text or "bidirectional" in text.lower():
        pattern["bidirectional"] = True
    if any(word in text for word in ("提高密度", "增加密度", "更密", "压迫感")):
        pattern["bullets_per_wave"] = min(64, max(pattern["bullets_per_wave"] + 4, round(pattern["bullets_per_wave"] * 1.25)))
        if not pattern["bidirectional"]:
            pattern["wave_interval_ms"] = max(100, round(pattern["wave_interval_ms"] * 0.88))

    max_alive = _extract_number(text, r"(?:最大|同时存在|峰值)[^\d]{0,12}(\d+)\s*(?:发|颗|个)?")
    min_fps = _extract_number(text, r"(?:最低|不低于|至少)[^\d]{0,8}(\d+)\s*FPS", flags=re.IGNORECASE)
    max_hits = _extract_number(text, r"(?:最多|不超过)[^\d]{0,8}(\d+)\s*(?:次碰撞|次命中|次受击)")
    if max_alive is not None:
        candidate["constraints"]["max_alive_bullets"] = max_alive
        candidate["runtime_targets"]["max_alive_bullets"] = max_alive
    if min_fps is not None:
        candidate["constraints"]["min_fps"] = min_fps
        candidate["runtime_targets"]["min_fps"] = min_fps
    if max_hits is not None:
        candidate["constraints"]["max_player_hits"] = max_hits
        candidate["runtime_targets"]["max_player_hits"] = max_hits

    goal = {
        "target_phase_id": phase["phase_id"],
        "requested_pattern": requested_pattern or pattern["type"],
        "increase_pressure": any(word in text for word in ("提高密度", "增加密度", "更密", "压迫感")),
        "preserve_visual_style": True,
        "constraints": deepcopy(candidate["constraints"]),
        "source_text": text,
    }
    return candidate, goal, _gate("accepted", "需求位于 Bullet Hell 1.0 配置能力范围内。")


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


def evaluate_bullet_hell_telemetry(contract: dict[str, Any], telemetry: dict[str, Any]) -> dict[str, Any]:
    targets = BulletHellContract.model_validate(contract).runtime_targets
    checks = [
        _check("normal_completion", "completed", telemetry.get("status"), telemetry.get("status") == "completed", "telemetry.status"),
        _check(
            "peak_alive_bullets",
            f"<= {targets.max_alive_bullets}",
            telemetry.get("peak_alive_bullets"),
            _lte(telemetry.get("peak_alive_bullets"), targets.max_alive_bullets),
            "telemetry.peak_alive_bullets",
        ),
        _check(
            "player_hits",
            f"<= {targets.max_player_hits}",
            telemetry.get("player_hits"),
            _lte(telemetry.get("player_hits"), targets.max_player_hits),
            "telemetry.player_hits",
        ),
        _check(
            "survival_time",
            f">= {targets.min_survival_seconds}",
            telemetry.get("player_survival_seconds"),
            _gte(telemetry.get("player_survival_seconds"), targets.min_survival_seconds),
            "telemetry.player_survival_seconds",
        ),
        _check(
            "low_percentile_fps",
            f">= {targets.min_fps}",
            telemetry.get("low_percentile_fps"),
            _gte(telemetry.get("low_percentile_fps"), targets.min_fps),
            "telemetry.low_percentile_fps",
        ),
        _check(
            "phase_coverage",
            len(contract["phases"]),
            len(telemetry.get("phase_results") or []),
            not targets.require_all_phases or len(telemetry.get("phase_results") or []) == len(contract["phases"]),
            "telemetry.phase_results",
        ),
        _check(
            "exception_logs",
            0,
            telemetry.get("exception_log_count"),
            telemetry.get("exception_log_count") == 0,
            "telemetry.exception_log_count",
        ),
    ]
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "evidence_scope": "固定种子与固定轨迹下的可重复运行证据，不代表所有玩家体验。",
    }


def choose_repair_action(evaluation: dict[str, Any]) -> RepairAction:
    failed = {row["check_id"]: row for row in evaluation["checks"] if not row["passed"]}
    if "peak_alive_bullets" in failed:
        return "REDUCE_BULLETS_PER_WAVE"
    if "low_percentile_fps" in failed:
        return "INCREASE_WAVE_INTERVAL"
    if "player_hits" in failed:
        return "REDUCE_BULLET_SPEED"
    if "survival_time" in failed:
        return "REDUCE_BULLET_LIFETIME"
    return "REQUEST_HUMAN"


def apply_repair(
    contract: dict[str, Any],
    action: RepairAction,
    evaluation: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = deepcopy(contract)
    phase = max(candidate["phases"], key=lambda row: estimate_peak_alive(row["pattern"]))
    pattern = phase["pattern"]
    before = deepcopy(pattern)
    if action == "REDUCE_BULLETS_PER_WAVE":
        check = _find_check(evaluation, "peak_alive_bullets")
        actual = max(float(check.get("actual") or 1), 1)
        limit = candidate["runtime_targets"]["max_alive_bullets"]
        factor = min(0.85, max(0.5, limit / actual * 0.9))
        pattern["bullets_per_wave"] = max(1, round(pattern["bullets_per_wave"] * factor))
    elif action == "INCREASE_WAVE_INTERVAL":
        pattern["wave_interval_ms"] = min(5000, max(pattern["wave_interval_ms"] + 100, round(pattern["wave_interval_ms"] * 1.2)))
    elif action == "REDUCE_BULLET_SPEED":
        pattern["bullet_speed"] = max(0.5, round(pattern["bullet_speed"] * 0.85, 2))
    elif action == "REDUCE_BULLET_LIFETIME":
        pattern["bullet_lifetime_seconds"] = max(0.5, round(pattern["bullet_lifetime_seconds"] * 0.85, 2))
    elif action == "REDUCE_PATTERN_LAYERS":
        pattern["layer_count"] = max(1 if pattern["type"] != "petal" else 2, pattern["layer_count"] - 1)
    else:
        return candidate, {
            "action": action,
            "applied": False,
            "reason": "该动作不直接修改配置，需要人工判断。",
        }
    return candidate, {
        "action": action,
        "applied": before != pattern,
        "phase_id": phase["phase_id"],
        "before": before,
        "after": deepcopy(pattern),
        "reason": "根据上一轮 Unity 失败证据执行受约束数值调整，并保留 Pattern 类型。",
    }


def simulate_telemetry(contract: dict[str, Any], *, seed: int = 20260727) -> dict[str, Any]:
    """Deterministic offline evidence used by unit tests and benchmark dry-runs."""
    parsed = BulletHellContract.model_validate(contract)
    estimates = [estimate_peak_alive(phase.pattern) for phase in parsed.phases]
    peak = max(estimates)
    hits = max(0, round((peak - 120) / 70))
    low_fps = max(20.0, round(66.0 - peak * 0.035, 2))
    duration = parsed.scenario.duration_seconds
    survived = duration if hits < parsed.player.max_health else round(duration * parsed.player.max_health / max(hits, 1), 2)
    return {
        "scenario_id": parsed.scenario.scenario_id,
        "bullet_hell_contract_version": parsed.bullet_hell_contract_version,
        "status": "completed" if survived >= duration else "failed",
        "run_mode": "auto",
        "random_seed": seed,
        "duration_seconds": duration,
        "total_bullets_spawned": sum(estimates) * 3,
        "peak_alive_bullets": peak,
        "bullets_per_second": round(sum(estimates) / duration, 2),
        "player_hits": hits,
        "player_survival_seconds": survived,
        "average_fps": round(low_fps + 3.5, 2),
        "low_percentile_fps": low_fps,
        "minimum_fps": round(low_fps - 5, 2),
        "exception_log_count": 0,
        "phase_results": [
            {"phase_id": phase.phase_id, "duration_seconds": round(duration / len(parsed.phases), 2)}
            for phase in parsed.phases
        ],
    }


def _unsafe_request(text: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    interval_seconds = _extract_number(text, r"(?:每|间隔)\s*(\d+(?:\.\d+)?)\s*秒")
    bullets = _extract_number(text, r"(?:发射|每波)\s*(\d+)\s*(?:颗|发|个)")
    if interval_seconds is not None and interval_seconds * 1000 < 100:
        issues.append({"field": "wave_interval_ms", "value": interval_seconds * 1000, "allowed": [100, 5000]})
    if bullets is not None and bullets > 64:
        issues.append({"field": "bullets_per_wave", "value": bullets, "allowed": [1, 64]})
    return issues


def _is_unrelated(text: str) -> bool:
    words = ("弹", "Boss", "boss", "阶段", "密度", "速度", "FPS", "碰撞", "生存", "螺旋", "扇形", "环形", "花瓣")
    return not any(word in text for word in words)


def _phase_index(text: str, count: int) -> int:
    mapping = {"第一阶段": 0, "第二阶段": 1, "第三阶段": 2, "phase 1": 0, "phase 2": 1, "phase 3": 2}
    lowered = text.lower()
    for label, index in mapping.items():
        if label in lowered:
            return min(index, count - 1)
    return min(1, count - 1)


def _pattern_from_text(text: str) -> PatternType | None:
    lowered = text.lower()
    for words, value in (
        (("花瓣", "petal"), "petal"),
        (("扇形", "瞄准", "aimed", "fan"), "aimed_fan"),
        (("螺旋", "spiral"), "spiral"),
        (("环形", "ring"), "ring"),
    ):
        if any(word in lowered for word in words):
            return value  # type: ignore[return-value]
    return None


def _extract_number(text: str, pattern: str, *, flags: int = 0) -> int | float | None:
    match = re.search(pattern, text, flags)
    if not match:
        return None
    value = float(match.group(1))
    return int(value) if value.is_integer() else value


def _gate(decision: str, reason: str, issues: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "gate": "bullet_hell_feasibility",
        "decision": decision,
        "reason": reason,
        "issues": issues or [],
        "config_only": True,
        "requires_code_change": False,
    }


def _check(check_id: str, expected: Any, actual: Any, passed: bool, evidence: str) -> dict[str, Any]:
    return {"check_id": check_id, "expected": expected, "actual": actual, "passed": passed, "evidence": evidence}


def _change(change_type: str, path: str, before: Any, after: Any) -> dict[str, Any]:
    return {"change_type": change_type, "path": path, "before": before, "after": after}


def _lte(value: Any, maximum: float) -> bool:
    return isinstance(value, (int, float)) and value <= maximum


def _gte(value: Any, minimum: float) -> bool:
    return isinstance(value, (int, float)) and value >= minimum


def _find_check(evaluation: dict[str, Any], check_id: str) -> dict[str, Any]:
    return next((row for row in evaluation["checks"] if row["check_id"] == check_id), {})


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
