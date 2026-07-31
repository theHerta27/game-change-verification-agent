"""Bounded agents for the Bullet Hell change-verification workflow."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Literal
import json

from pydantic import BaseModel, ConfigDict, Field

from gameconfig_agent.bullet_hell import (
    BulletHellContract,
    PatternType,
    RepairAction,
    SafetyConstraints,
    choose_repair_action,
    propose_mock_change,
)
from gameconfig_agent.env_loader import load_dotenv
from gameconfig_agent.prompts import load_prompt


ProviderFactory = Callable[[int], Any]
ReviewDecision = Literal["accept", "repair", "human_review"]


class StrictAgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BulletHellStructuredGoal(StrictAgentModel):
    target_phase_id: str = Field(min_length=1)
    requested_pattern: PatternType
    increase_pressure: bool
    preserve_visual_style: bool
    constraints: SafetyConstraints
    source_text: str = Field(min_length=1)


class RequirementAgentOutput(StrictAgentModel):
    structured_goal: BulletHellStructuredGoal
    candidate_config: BulletHellContract


class QualityReviewOutput(StrictAgentModel):
    decision: ReviewDecision
    repair_action: RepairAction | None = None
    reason: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)


class BulletHellAgentError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        stage: str,
        evidence: dict[str, Any],
        raw_output: str | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.evidence = evidence
        self.raw_output = raw_output


class RequirementAgent:
    """Proposes a complete candidate without permission to run or apply it."""

    name = "requirement_agent"
    prompt_name = "bullet_hell_requirement_agent"

    def __init__(self, repository_root: Path, provider_factory: ProviderFactory) -> None:
        self.repository_root = repository_root
        self.provider_factory = provider_factory

    def run(
        self,
        *,
        baseline: dict[str, Any],
        requirement: str,
        provider_name: str,
        timeout_seconds: int,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        if provider_name == "mock":
            candidate, goal, gate = propose_mock_change(baseline, requirement)
            if gate["decision"] == "accepted":
                goal = BulletHellStructuredGoal.model_validate(goal).model_dump(mode="json")
            return candidate, goal, gate, _agent_run(
                agent_name=self.name,
                prompt_name=self.prompt_name,
                provider="mock",
                model="deterministic_bullet_hell_fixture",
                latency_ms=0,
                usage=None,
                token_estimate=None,
                status="succeeded",
                model_call=False,
                input_artifacts=["requirement.json", "baseline_config.json"],
                output_artifacts=["structured_goal.json", "candidate_config.json"],
            )

        load_dotenv(self.repository_root / ".env")
        evidence = _agent_run(
            agent_name=self.name,
            prompt_name=self.prompt_name,
            provider=provider_name,
            model=None,
            latency_ms=0,
            usage=None,
            token_estimate=None,
            status="failed",
            model_call=True,
            input_artifacts=["requirement.json", "baseline_config.json"],
            output_artifacts=["structured_goal.json", "candidate_config.json"],
        )
        raw_output: str | None = None
        try:
            provider = self.provider_factory(timeout_seconds)
            evidence["model"] = getattr(provider, "model", None)
            response = provider.complete_json(
                prompt_name=self.prompt_name,
                system_prompt=load_prompt(self.prompt_name),
                user_prompt=json.dumps(
                    {"requirement": requirement, "baseline": baseline},
                    ensure_ascii=False,
                ),
            )
            raw_output = response.content
            evidence.update(
                {
                    "latency_ms": response.latency_ms,
                    "usage": response.usage,
                    "token_estimate": response.token_estimate,
                }
            )
            payload = RequirementAgentOutput.model_validate(json.loads(raw_output))
            evidence["status"] = "succeeded"
            candidate = payload.candidate_config.model_dump(mode="json")
            goal = payload.structured_goal.model_dump(mode="json")
            gate = {
                "gate": "bullet_hell_feasibility",
                "decision": "accepted",
                "reason": "Requirement Agent 已生成候选，等待四层确定性校验。",
                "issues": [],
                "config_only": True,
                "requires_code_change": False,
            }
            return candidate, goal, gate, evidence
        except Exception as exc:
            evidence["error_type"] = type(exc).__name__
            evidence["error_message"] = str(exc)
            raise BulletHellAgentError(
                f"Requirement Agent failed: {exc}",
                stage="requirement_agent",
                evidence=evidence,
                raw_output=raw_output,
            ) from exc


class QualityReviewAgent:
    """Reviews evidence and selects a bounded intent; it never changes numbers."""

    name = "quality_review_agent"
    prompt_name = "bullet_hell_quality_review_agent"

    def __init__(self, repository_root: Path, provider_factory: ProviderFactory) -> None:
        self.repository_root = repository_root
        self.provider_factory = provider_factory

    def review(
        self,
        *,
        requirement: str,
        structured_goal: dict[str, Any],
        config_diff: list[dict[str, Any]],
        evaluation: dict[str, Any],
        repair_history: list[dict[str, Any]],
        provider_name: str,
        timeout_seconds: int,
        iteration: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        expected_action = None if evaluation["passed"] else choose_repair_action(evaluation)
        if provider_name == "mock":
            output = _deterministic_review(evaluation, expected_action)
            evidence = _agent_run(
                agent_name=self.name,
                prompt_name=self.prompt_name,
                provider="mock",
                model="deterministic_quality_policy",
                latency_ms=0,
                usage=None,
                token_estimate=None,
                status="succeeded",
                model_call=False,
                input_artifacts=[
                    "requirement.json",
                    "structured_goal.json",
                    "config_diff.json",
                    "comparison_report.json",
                    "repair_history.json",
                ],
                output_artifacts=["quality_reviews.json"],
                iteration=iteration,
            )
        else:
            output, evidence = self._real_review(
                requirement=requirement,
                structured_goal=structured_goal,
                config_diff=config_diff,
                evaluation=evaluation,
                repair_history=repair_history,
                timeout_seconds=timeout_seconds,
                iteration=iteration,
            )
        review = {
            "iteration": iteration,
            "agent_output": output.model_dump(mode="json"),
            "policy_gate": _review_policy_gate(output, evaluation, expected_action),
            "deterministic_evaluation_passed": evaluation["passed"],
        }
        return review, evidence

    def _real_review(
        self,
        *,
        requirement: str,
        structured_goal: dict[str, Any],
        config_diff: list[dict[str, Any]],
        evaluation: dict[str, Any],
        repair_history: list[dict[str, Any]],
        timeout_seconds: int,
        iteration: int,
    ) -> tuple[QualityReviewOutput, dict[str, Any]]:
        load_dotenv(self.repository_root / ".env")
        evidence = _agent_run(
            agent_name=self.name,
            prompt_name=self.prompt_name,
            provider="openai_compatible",
            model=None,
            latency_ms=0,
            usage=None,
            token_estimate=None,
            status="failed",
            model_call=True,
            input_artifacts=[
                "requirement.json",
                "structured_goal.json",
                "config_diff.json",
                "comparison_report.json",
                "repair_history.json",
            ],
            output_artifacts=["quality_reviews.json"],
            iteration=iteration,
        )
        raw_output: str | None = None
        try:
            provider = self.provider_factory(timeout_seconds)
            evidence["model"] = getattr(provider, "model", None)
            response = provider.complete_json(
                prompt_name=self.prompt_name,
                system_prompt=load_prompt(self.prompt_name),
                user_prompt=json.dumps(
                    {
                        "requirement": requirement,
                        "structured_goal": structured_goal,
                        "config_diff": config_diff,
                        "deterministic_evaluation": evaluation,
                        "repair_history": repair_history,
                    },
                    ensure_ascii=False,
                ),
            )
            raw_output = response.content
            evidence.update(
                {
                    "latency_ms": response.latency_ms,
                    "usage": response.usage,
                    "token_estimate": response.token_estimate,
                }
            )
            output = QualityReviewOutput.model_validate(json.loads(raw_output))
            evidence["status"] = "succeeded"
            return output, evidence
        except Exception as exc:
            evidence["error_type"] = type(exc).__name__
            evidence["error_message"] = str(exc)
            raise BulletHellAgentError(
                f"Quality Review Agent failed: {exc}",
                stage="quality_review_agent",
                evidence=evidence,
                raw_output=raw_output,
            ) from exc


def _deterministic_review(
    evaluation: dict[str, Any],
    expected_action: RepairAction | None,
) -> QualityReviewOutput:
    if evaluation["passed"]:
        return QualityReviewOutput(
            decision="accept",
            repair_action=None,
            reason="全部确定性运行目标通过，可以进入最终人工决策。",
            evidence_refs=["comparison_report.json.evaluation.checks"],
        )
    if expected_action == "REQUEST_HUMAN":
        return QualityReviewOutput(
            decision="human_review",
            repair_action="REQUEST_HUMAN",
            reason="失败项没有对应的已授权确定性修复动作。",
            evidence_refs=["comparison_report.json.evaluation.checks"],
        )
    return QualityReviewOutput(
        decision="repair",
        repair_action=expected_action,
        reason="根据未通过的确定性检查选择现有有限修复动作。",
        evidence_refs=["comparison_report.json.evaluation.checks", "repair_history.json"],
    )


def _review_policy_gate(
    output: QualityReviewOutput,
    evaluation: dict[str, Any],
    expected_action: RepairAction | None,
) -> dict[str, Any]:
    if output.decision == "human_review":
        return {
            "passed": True,
            "effective_decision": "human_review",
            "effective_action": "REQUEST_HUMAN",
            "expected_action": expected_action,
            "reason": "人工复核是任何阶段都允许的保守决策。",
        }
    if evaluation["passed"]:
        passed = output.decision == "accept" and output.repair_action in {None, "STOP"}
        return {
            "passed": passed,
            "effective_decision": "accept" if passed else "human_review",
            "effective_action": None if passed else "REQUEST_HUMAN",
            "expected_action": None,
            "reason": (
                "确定性硬指标全部通过，Agent 接受建议有效。"
                if passed
                else "硬指标已通过，但 Agent 输出与允许的接受决策冲突，转人工复核。"
            ),
        }
    passed = output.decision == "repair" and output.repair_action == expected_action
    return {
        "passed": passed,
        "effective_decision": "repair" if passed else "human_review",
        "effective_action": expected_action if passed else "REQUEST_HUMAN",
        "expected_action": expected_action,
        "reason": (
            "修复意图与现有确定性修复策略一致。"
            if passed
            else "Agent 建议与确定性失败路由不一致，拒绝自动修改并转人工复核。"
        ),
    }


def _agent_run(
    *,
    agent_name: str,
    prompt_name: str,
    provider: str,
    model: str | None,
    latency_ms: int,
    usage: dict[str, Any] | None,
    token_estimate: int | None,
    status: str,
    model_call: bool,
    input_artifacts: list[str],
    output_artifacts: list[str],
    iteration: int | None = None,
) -> dict[str, Any]:
    value = {
        "agent_name": agent_name,
        "prompt_name": prompt_name,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "usage": deepcopy(usage),
        "token_estimate": token_estimate,
        "status": status,
        "model_call": model_call,
        "input_artifacts": input_artifacts,
        "output_artifacts": output_artifacts,
    }
    if iteration is not None:
        value["iteration"] = iteration
    return value
