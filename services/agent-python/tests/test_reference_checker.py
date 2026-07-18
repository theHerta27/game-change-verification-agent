from gameconfig_agent.blackboard import create_blackboard
from gameconfig_agent.agents.generator import ConfigGeneratorAgent
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool


def test_reference_checker_finds_missing_refine_stone():
    blackboard = create_blackboard("training sword")
    ConfigGeneratorAgent().generate(blackboard)

    errors = ReferenceCheckerTool().check(blackboard["draft_configs"])

    assert errors
    assert all(error["code"] == "missing_reference" for error in errors)
    assert {error["value"] for error in errors} == {"item_refine_stone"}
