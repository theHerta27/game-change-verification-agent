from gameconfig_agent.cli import run_phase0_demo
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool
from gameconfig_agent.tools.rule_engine import RuleEngineTool
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


def test_repair_loop_generates_actions_and_final_config_passes(tmp_path):
    input_path = tmp_path / "requirement.txt"
    input_path.write_text(
        "设计一个新手武器 Training Sword，基础攻击力 50，可升级 3 次，每级攻击力 +5。升级消耗金币和强化石。该武器作为新手任务奖励发放，只能领取一次。",
        encoding="utf-8",
    )

    blackboard = run_phase0_demo(input_path, tmp_path / "outputs")
    final_configs = blackboard["repaired_configs"]

    assert blackboard["repair_actions"]
    assert blackboard["final_validation"]["passed"] is True
    assert final_configs["weapon_config"][0]["base_attack"] == 50
    assert [row["level"] for row in final_configs["upgrade_config"]] == [1, 2, 3]
    assert [row["attack_bonus"] for row in final_configs["upgrade_config"]] == [5, 5, 5]
    assert [
        next(cost["amount"] for cost in row["cost_items"] if cost["item_id"] == "item_gold")
        for row in final_configs["upgrade_config"]
    ] == [100, 150, 200]
    assert final_configs["reward_config"][0]["once_only"] is True
    assert "item_refine_stone" in {item["item_id"] for item in final_configs["item_config"]}

    assert SchemaValidatorTool().validate(blackboard["structured_requirement"], final_configs) == []
    assert ReferenceCheckerTool().check(final_configs) == []
    assert RuleEngineTool().evaluate(blackboard["structured_requirement"], final_configs)["violations"] == []
