from gameconfig_agent.runtime_contract import build_runtime_contract
from gameconfig_agent.runtime_evaluation import evaluate_runtime


def _configs() -> dict:
    return {
        "item_config": [],
        "weapon_config": [{"weapon_id": "weapon_sword", "base_attack": 50}],
        "upgrade_config": [
            {"level": 1, "cost_items": [{"item_id": "item_gold", "amount": 100}]},
            {"level": 2, "cost_items": [{"item_id": "item_gold", "amount": 150}]},
        ],
        "reward_config": [],
    }


def test_runtime_evaluation_exposes_gameplay_and_economy_failures() -> None:
    contract = build_runtime_contract(_configs())
    telemetry = {"status": "completed", "completion_time_seconds": 16.4, "gold_earned": 300}

    result = evaluate_runtime(contract, telemetry)

    assert result["passed"] is False
    assert result["runtime_target_pass_rate"] == 0.6
    assert {check["check_id"] for check in result["failed_checks"]} == {
        "completion_time_in_target",
        "second_upgrade_affordable",
    }


def test_runtime_evaluation_passes_balanced_result() -> None:
    contract = build_runtime_contract(_configs())
    contract["configs"]["upgrade_config"][1]["cost_items"][0]["amount"] = 250
    telemetry = {"status": "completed", "completion_time_seconds": 45.0, "gold_earned": 300}

    result = evaluate_runtime(contract, telemetry)

    assert result["passed"] is True
    assert result["runtime_target_pass_rate"] == 1.0
