"""Blackboard state and trace helpers."""

from __future__ import annotations

from typing import Any


def create_blackboard(requirement_text: str) -> dict[str, Any]:
    return {
        "requirement_text": requirement_text,
        "structured_requirement": {},
        "assumptions": [],
        "draft_configs": {},
        "design_reference": {},
        "validation_errors": [],
        "review_findings": [],
        "repair_actions": [],
        "repaired_configs": {},
        "final_validation": {},
        "trace": [],
        "validation_runs": {},
        "max_repair_rounds": 1,
    }


def record_trace(
    blackboard: dict[str, Any],
    *,
    actor: str,
    actor_type: str,
    action: str,
    input_refs: list[str],
    output_refs: list[str],
    status: str,
    error_count: int | None = None,
) -> None:
    event: dict[str, Any] = {
        "step": len(blackboard["trace"]) + 1,
        "actor": actor,
        "actor_type": actor_type,
        "action": action,
        "input_refs": input_refs,
        "output_refs": output_refs,
        "status": status,
    }
    if error_count is not None:
        event["error_count"] = error_count
    blackboard["trace"].append(event)
