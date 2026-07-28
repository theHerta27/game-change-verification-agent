from copy import deepcopy
from pathlib import Path

from gameconfig_agent.bullet_hell import (
    apply_repair,
    build_config_diff,
    choose_repair_action,
    evaluate_bullet_hell_telemetry,
    load_bullet_hell_contract,
    propose_mock_change,
    simulate_telemetry,
    validate_bullet_hell_contract,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = REPOSITORY_ROOT / "configs" / "bullet-hell" / "baseline.json"


def test_baseline_contract_is_valid_and_has_four_supported_pattern_shapes():
    baseline = load_bullet_hell_contract(BASELINE_PATH)
    result = validate_bullet_hell_contract(baseline)

    assert result["passed"]
    assert baseline["bullet_hell_contract_version"] == "1.0"
    assert {row["pattern"]["type"] for row in baseline["phases"]} == {"ring", "spiral", "petal"}


def test_mock_change_targets_second_phase_and_preserves_baseline():
    baseline = load_bullet_hell_contract(BASELINE_PATH)
    original = deepcopy(baseline)

    candidate, goal, gate = propose_mock_change(
        baseline,
        "第二阶段改为双向螺旋弹，提高密度，但最大同时存在子弹不能超过350发，最低55 FPS。",
    )

    assert gate["decision"] == "accepted"
    assert goal["target_phase_id"] == "phase_2"
    assert candidate["phases"][1]["pattern"]["type"] == "spiral"
    assert candidate["phases"][1]["pattern"]["bidirectional"] is True
    assert candidate != baseline
    assert baseline == original
    assert build_config_diff(baseline, candidate)


def test_extreme_request_is_blocked_before_unity():
    baseline = load_bullet_hell_contract(BASELINE_PATH)

    _, _, gate = propose_mock_change(baseline, "每0.02秒发射200颗高速弹，越密越好。")

    assert gate["decision"] == "blocked"
    assert {issue["field"] for issue in gate["issues"]} == {"wave_interval_ms", "bullets_per_wave"}


def test_unrelated_requirement_requests_clarification():
    baseline = load_bullet_hell_contract(BASELINE_PATH)

    _, _, gate = propose_mock_change(baseline, "帮我讲一个笑话。")

    assert gate["decision"] == "needs_clarification"


def test_runtime_failure_selects_bounded_repair_and_improves_peak():
    baseline = load_bullet_hell_contract(BASELINE_PATH)
    candidate, _, _ = propose_mock_change(baseline, "第二阶段改为双向螺旋弹并提高密度。")
    telemetry = simulate_telemetry(candidate)
    telemetry["peak_alive_bullets"] = 420
    evaluation = evaluate_bullet_hell_telemetry(candidate, telemetry)

    action = choose_repair_action(evaluation)
    repaired, evidence = apply_repair(candidate, action, evaluation)

    assert action == "REDUCE_BULLETS_PER_WAVE"
    assert evidence["applied"]
    assert simulate_telemetry(repaired)["peak_alive_bullets"] < telemetry["peak_alive_bullets"]


def test_invalid_pattern_and_limit_return_structured_errors():
    baseline = load_bullet_hell_contract(BASELINE_PATH)
    baseline["phases"][0]["pattern"]["type"] = "unknown"
    baseline["constraints"]["max_alive_bullets"] = 351

    result = validate_bullet_hell_contract(baseline)

    assert not result["passed"]
    assert result["schema_errors"]
