from copy import deepcopy

from gameconfig_agent.data.starter_trial_catalog import STARTER_TRIAL_CAPABILITY, STARTER_TRIAL_DEFAULT_V2_CONFIGS
from gameconfig_agent.runtime_contract import build_runtime_contract
from gameconfig_agent.runtime_evaluation import evaluate_runtime
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool
from gameconfig_agent.tools.rule_engine import RuleEngineTool
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


STRUCTURED_REQUIREMENT = {
    "request_id": "req_training_sword_beginner_weapon",
    "item_name": "Training Sword",
    "category": "beginner_weapon",
    "base_attack": 50,
    "upgrade_times": 2,
    "upgrade_attack_bonus": 5,
    "cost_item_tags": ["gold", "refine_stone"],
    "reward_channel": "beginner_quest",
    "once_only": True,
}


def _v2_configs() -> dict:
    configs = {
        "item_config": [
            {"item_id": "item_training_sword", "display_name": "Training Sword", "item_type": "weapon", "rarity": "common"},
            {"item_id": "item_gold", "display_name": "Gold", "item_type": "currency", "rarity": "common"},
            {"item_id": "item_refine_stone", "display_name": "Refine Stone", "item_type": "material", "rarity": "common"},
        ],
        "weapon_config": [
            {
                "weapon_id": "weapon_training_sword",
                "item_id": "item_training_sword",
                "weapon_type": "sword",
                "base_attack": 50,
                "strength_tier": "common",
            }
        ],
        "upgrade_config": [
            {
                "weapon_id": "weapon_training_sword",
                "level": 1,
                "attack_bonus": 5,
                "cost_items": [{"item_id": "item_gold", "amount": 100}, {"item_id": "item_refine_stone", "amount": 1}],
            },
            {
                "weapon_id": "weapon_training_sword",
                "level": 2,
                "attack_bonus": 5,
                "cost_items": [{"item_id": "item_gold", "amount": 150}, {"item_id": "item_refine_stone", "amount": 2}],
            },
        ],
        "reward_config": [
            {
                "reward_id": "reward_beginner_trial_first_clear",
                "quest_id": "quest_beginner_trial",
                "reward_item_id": "item_training_sword",
                "weapon_id": "weapon_training_sword",
                "once_only": True,
                "source": "beginner_quest",
                "reward_items": [
                    {"item_id": "item_training_sword", "amount": 1},
                    {"item_id": "item_gold", "amount": 300},
                    {"item_id": "item_refine_stone", "amount": 3},
                ],
            }
        ],
    }
    configs.update(deepcopy(STARTER_TRIAL_DEFAULT_V2_CONFIGS))
    return configs


def test_starter_trial_capability_catalog_exposes_controlled_groups() -> None:
    assert STARTER_TRIAL_CAPABILITY["capability"] == "starter_trial_config"
    assert "enemy_config" in STARTER_TRIAL_CAPABILITY["optional_groups"]
    assert "max_health" in STARTER_TRIAL_CAPABILITY["change_field_allowlist"]["enemy_config"]


def test_v2_starter_trial_config_passes_static_validation() -> None:
    configs = _v2_configs()

    assert SchemaValidatorTool().validate(STRUCTURED_REQUIREMENT, configs) == []
    assert ReferenceCheckerTool().check(configs) == []
    assert RuleEngineTool().evaluate(STRUCTURED_REQUIREMENT, configs)["violations"] == []


def test_schema_validator_checks_v2_nested_reward_items() -> None:
    configs = _v2_configs()
    configs["reward_config"][0]["reward_items"] = ["bad reward"]

    errors = SchemaValidatorTool().validate(STRUCTURED_REQUIREMENT, configs)

    assert any(error["path"] == "reward_config[0].reward_items[0]" for error in errors)


def test_reference_checker_validates_reward_items_and_wave_enemy_ids() -> None:
    configs = _v2_configs()
    configs["reward_config"][0]["reward_items"].append({"item_id": "item_unknown_material", "amount": 1})
    configs["wave_config"][0]["enemy_id"] = "enemy_unknown"

    errors = ReferenceCheckerTool().check(configs)

    assert any(error["path"] == "reward_config[0].reward_items[3].item_id" for error in errors)
    assert any(error["path"] == "wave_config[0].enemy_id" for error in errors)


def test_rule_engine_validates_v2_balance_bounds() -> None:
    configs = _v2_configs()
    configs["reward_config"][0]["reward_items"][1]["amount"] = 0
    configs["enemy_config"][0]["max_health"] = 0
    configs["runtime_target_config"][0]["completion_time_seconds_min"] = 90.0
    configs["runtime_target_config"][0]["completion_time_seconds_max"] = 60.0

    codes = {violation["code"] for violation in RuleEngineTool().evaluate(STRUCTURED_REQUIREMENT, configs)["violations"]}

    assert "non_positive_reward_amount" in codes
    assert "non_positive_enemy_stat" in codes
    assert "invalid_completion_time_target" in codes


def test_runtime_contract_v2_maps_configs_into_unity_scenario() -> None:
    contract = build_runtime_contract(_v2_configs())

    assert contract["contract_version"] == "2.0"
    assert contract["runtime_scenario"]["enemies"][2]["enemy_id"] == "enemy_training_elite"
    assert contract["runtime_scenario"]["waves"][1]["count"] == 2
    assert contract["runtime_scenario"]["skill"]["damage"] == 100
    assert contract["runtime_scenario"]["targets"]["enemies_defeated"] == 5


def test_runtime_evaluation_uses_multi_resource_reward_vector() -> None:
    configs = _v2_configs()
    contract = build_runtime_contract(configs)
    telemetry = {
        "status": "completed",
        "completion_time_seconds": 70.0,
        "enemies_defeated": 5,
        "skill_uses": 1,
        "gold_earned": 300,
    }

    result = evaluate_runtime(contract, telemetry)

    assert any(check["check_id"] == "second_upgrade_affordable" and not check["passed"] for check in result["checks"])
    assert result["check_count"] == 7
