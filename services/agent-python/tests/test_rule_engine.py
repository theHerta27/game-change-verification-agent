from gameconfig_agent.blackboard import create_blackboard
from gameconfig_agent.agents.generator import ConfigGeneratorAgent
from gameconfig_agent.tools.rule_engine import RuleEngineTool


def test_rule_engine_finds_expected_flawed_draft_violations():
    blackboard = create_blackboard("training sword")
    ConfigGeneratorAgent().generate(blackboard)

    result = RuleEngineTool().evaluate(
        blackboard["structured_requirement"], blackboard["draft_configs"]
    )
    codes = {violation["code"] for violation in result["violations"]}

    assert "non_continuous_upgrade_levels" in codes
    assert "zero_gold_cost" in codes
    assert "beginner_reward_not_once_only" in codes
    assert len(result["violations"]) == 3
    assert result["coupled_fields"]
