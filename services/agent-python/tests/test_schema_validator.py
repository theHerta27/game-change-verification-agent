from gameconfig_agent.blackboard import create_blackboard
from gameconfig_agent.agents.generator import ConfigGeneratorAgent
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


def test_flawed_draft_schema_is_valid():
    blackboard = create_blackboard("training sword")
    ConfigGeneratorAgent().generate(blackboard)

    errors = SchemaValidatorTool().validate(
        blackboard["structured_requirement"], blackboard["draft_configs"]
    )

    assert errors == []
