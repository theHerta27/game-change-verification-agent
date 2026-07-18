import json

import pytest

from gameconfig_agent.runtime_contract import build_runtime_contract, export_runtime_contract


def test_build_runtime_contract_keeps_agent_configs() -> None:
    configs = {
        "item_config": [{"item_id": "item_sword"}],
        "weapon_config": [{"weapon_id": "weapon_sword", "base_attack": 50}],
        "upgrade_config": [],
        "reward_config": [],
    }

    contract = build_runtime_contract(configs)

    assert contract["contract_version"] == "1.0"
    assert contract["configs"] == configs
    assert contract["runtime_scenario"]["waves"][0]["enemy_id"] == "enemy_training_dummy"


def test_build_runtime_contract_rejects_missing_groups() -> None:
    with pytest.raises(ValueError, match="upgrade_config"):
        build_runtime_contract({"item_config": [], "weapon_config": [{}], "reward_config": []})


def test_export_runtime_contract_writes_json(tmp_path) -> None:
    source = tmp_path / "final_configs.json"
    source.write_text(
        json.dumps(
            {
                "item_config": [],
                "weapon_config": [{"weapon_id": "weapon_sword", "base_attack": 50}],
                "upgrade_config": [],
                "reward_config": [],
            }
        ),
        encoding="utf-8",
    )

    destination = export_runtime_contract(source, tmp_path / "runtime" / "game_config.json")

    assert destination.exists()
    assert json.loads(destination.read_text(encoding="utf-8"))["configs"]["weapon_config"][0]["base_attack"] == 50
