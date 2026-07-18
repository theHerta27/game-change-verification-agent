"""Config Generator Agent."""

from __future__ import annotations

from gameconfig_agent.mock_llm import MockLLM


class ConfigGeneratorAgent:
    name = "Config Generator Agent"

    def __init__(self, llm: MockLLM | None = None) -> None:
        self.llm = llm or MockLLM()

    def generate(self, blackboard: dict) -> None:
        structured_requirement, assumptions = self.llm.infer_training_sword_requirement(
            blackboard["requirement_text"]
        )
        blackboard["structured_requirement"] = structured_requirement
        blackboard["assumptions"] = assumptions
        blackboard["draft_configs"] = self.llm.create_intentionally_flawed_draft(structured_requirement)
