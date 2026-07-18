from pathlib import Path

from gameconfig_agent.agents.repairer import ConfigRepairAgent
from gameconfig_agent.data.classic_cases import PROJECT_ROOT, list_classic_cases
from gameconfig_agent.data.design_reference import BALANCE_POLICY_LOOKUP, RESOURCE_ITEM_CATALOG
from gameconfig_agent.mock_llm import MockLLM
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool


def test_exactly_five_unique_classic_cases_are_loadable():
    cases = list_classic_cases()

    assert len(cases) == 5
    assert len({case["case_id"] for case in cases}) == 5
    assert [case["demo_priority"] for case in cases] == ["main", "main", "main", "backup", "backup"]
    for case in cases:
        assert (PROJECT_ROOT / case["file_path"]).is_file()
        assert case["requirement_text"]
        assert case["expected_observations"]
        assert case["recommended_demo_usage"]


def test_trial_medal_catalog_does_not_bypass_reference_checker():
    assert "item_trial_medal" in RESOURCE_ITEM_CATALOG
    configs = _base_configs()
    configs["upgrade_config"][0]["cost_items"].append({"item_id": "item_trial_medal", "amount": 1})

    errors = ReferenceCheckerTool().check(configs)

    assert any(error["code"] == "missing_reference" and error["value"] == "item_trial_medal" for error in errors)


def test_repairer_adds_only_known_catalog_resources_and_records_unknown_ids():
    requirement, _ = MockLLM().infer_training_sword_requirement("classic repair boundary")
    configs = _base_configs()
    configs["upgrade_config"][0]["cost_items"].extend(
        [
            {"item_id": "item_trial_medal", "amount": 1},
            {"item_id": "item_unknown_fragment", "amount": 1},
        ]
    )
    blackboard = {
        "structured_requirement": requirement,
        "design_reference": BALANCE_POLICY_LOOKUP,
        "draft_configs": configs,
    }

    actions = ConfigRepairAgent().repair(blackboard)

    assert any(action["action"] == "add_missing_item_reference" and action["after"]["item_id"] == "item_trial_medal" for action in actions)
    assert any(action["action"] == "record_unresolved_item_reference" and action["after"] == "item_unknown_fragment" for action in actions)
    assert blackboard["requires_regeneration"] is True


def _base_configs() -> dict:
    import json

    fixture = Path(__file__).resolve().parent / "fixtures" / "gameconfig" / "final_configs.json"
    return json.loads(fixture.read_text(encoding="utf-8"))
