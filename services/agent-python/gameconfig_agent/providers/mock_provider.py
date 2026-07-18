"""Deterministic mock provider for Phase 2 real-run pipeline tests."""

from __future__ import annotations

import json
import time

from gameconfig_agent.agents.test_scenario import TestScenarioAgent
from gameconfig_agent.agents.repairer import ConfigRepairAgent
from gameconfig_agent.agents.reviewer import ConfigReviewerAgent
from gameconfig_agent.blackboard import create_blackboard
from gameconfig_agent.data.design_reference import BALANCE_POLICY_LOOKUP
from gameconfig_agent.mock_llm import MockLLM
from gameconfig_agent.providers.base import LLMResponse


class MockLLMProvider:
    name = "mock"

    def complete_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str) -> LLMResponse:
        started = time.perf_counter()
        content = self._content_for(prompt_name, user_prompt)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return LLMResponse(
            content=content,
            latency_ms=latency_ms,
            token_estimate=max(1, len(system_prompt.split()) + len(user_prompt.split()) + len(content.split())),
        )

    def _content_for(self, prompt_name: str, user_prompt: str) -> str:
        llm = MockLLM()
        requirement, assumptions = llm.infer_training_sword_requirement(user_prompt)
        draft = llm.create_intentionally_flawed_draft(requirement)
        blackboard = create_blackboard(user_prompt)
        blackboard["structured_requirement"] = requirement
        blackboard["assumptions"] = assumptions
        blackboard["draft_configs"] = draft
        blackboard["design_reference"] = BALANCE_POLICY_LOOKUP

        if prompt_name == "generator":
            payload = {
                "structured_requirement": requirement,
                "assumptions": assumptions,
                "draft_configs": draft,
            }
        elif prompt_name == "reviewer":
            payload = {"review_findings": ConfigReviewerAgent().review(blackboard)}
        elif prompt_name == "repairer":
            ConfigReviewerAgent().review(blackboard)
            payload = {}
            payload["repair_actions"] = ConfigRepairAgent().repair(blackboard)
            payload["repaired_configs"] = blackboard["repaired_configs"]
        elif prompt_name == "test_scenario":
            ConfigReviewerAgent().review(blackboard)
            ConfigRepairAgent().repair(blackboard)
            payload = {"test_scenarios": TestScenarioAgent().generate(blackboard["repaired_configs"])}
        else:
            payload = {"error": f"Unknown prompt: {prompt_name}"}
        return json.dumps(payload, ensure_ascii=False)
