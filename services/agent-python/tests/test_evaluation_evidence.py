import json
from pathlib import Path

from gameconfig_agent.data.classic_cases import PROJECT_ROOT
from gameconfig_agent.evaluation_evidence import build_evaluation_evidence
from gameconfig_agent.runtime_telemetry import RuntimeTelemetryNormalizer


def test_telemetry_normalizer_supports_aliases_without_mutating_raw():
    raw = {"clear_time_seconds": 16.45, "skills_used": 1, "basic_attacks": 12}
    snapshot = dict(raw)

    normalized = RuntimeTelemetryNormalizer().normalize(raw)

    assert normalized["values"]["completion_time_seconds"] == 16.45
    assert normalized["values"]["skill_uses"] == 1
    assert normalized["values"]["normal_attacks"] == 12
    assert normalized["values"]["gold_earned"] == "unavailable"
    assert raw == snapshot


def test_reward_overgrant_uses_gold_and_refine_stone(tmp_path):
    outputs = _outputs_with_configs_and_telemetry(tmp_path)

    evidence = build_evaluation_evidence("case_02_reward_overgrant", outputs_dir=outputs)
    checks = {check["check_id"]: check for check in evidence["checks"]}

    assert checks["first_upgrade"]["actual"] is True
    assert checks["first_upgrade"]["status"] == "passed"
    assert checks["second_upgrade_after_first"]["actual"] is True
    assert checks["second_upgrade_after_first"]["status"] == "failed"
    assert "reward_grants" in checks["second_upgrade_after_first"]["evidence"]


def test_fast_combat_fails_sixty_to_ninety_second_target(tmp_path):
    outputs = _outputs_with_configs_and_telemetry(tmp_path, completion_time=16.45)

    evidence = build_evaluation_evidence("case_03_combat_too_fast", outputs_dir=outputs)
    check = evidence["checks"][0]

    assert check["target"] == "60-90s"
    assert check["actual"] == 16.45
    assert check["status"] == "failed"


def test_missing_reference_case_returns_static_checker_and_repair_evidence(tmp_path):
    outputs = _outputs_with_configs_and_telemetry(tmp_path)

    evidence = build_evaluation_evidence("case_04_missing_reference", outputs_dir=outputs)
    checks = {check["check_id"]: check for check in evidence["checks"]}

    assert evidence["evidence_type"] == "static_validation"
    assert evidence["telemetry_source"] is None
    assert checks["trial_medal_reference"]["status"] == "failed"
    assert checks["trial_medal_repair"]["status"] == "passed"


def test_skill_guidance_is_explicitly_weak_validation(tmp_path):
    outputs = _outputs_with_configs_and_telemetry(tmp_path)

    evidence = build_evaluation_evidence("case_05_skill_guidance_balance", outputs_dir=outputs)

    assert evidence["design_targets"]["validation_strength"] == "weak"
    assert {check["check_id"] for check in evidence["checks"]} == {"skill_usage", "completion_time"}


def _outputs_with_configs_and_telemetry(tmp_path: Path, completion_time: float = 16.45) -> Path:
    outputs = tmp_path / "outputs"
    phase0 = outputs / "phase0"
    unity = outputs / "unity"
    phase0.mkdir(parents=True)
    unity.mkdir(parents=True)
    source = Path(__file__).resolve().parent / "fixtures" / "gameconfig" / "final_configs.json"
    (phase0 / "final_configs.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    telemetry = {
        "completion_time_seconds": completion_time,
        "enemies_defeated": 5,
        "basic_attacks": 12,
        "skill_uses": 1,
        "gold_earned": 300,
        "gold_spent": 0,
    }
    (unity / "telemetry.json").write_text(json.dumps(telemetry), encoding="utf-8")
    return outputs
