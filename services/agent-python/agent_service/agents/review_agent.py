from __future__ import annotations

import json
import time

from pydantic import ValidationError

from agent_service.llm.base import LLMClient
from agent_service.llm.factory import create_llm_client
from agent_service.schemas import AgentRun, Finding, ReviewRequest, StaticHint


def run_review_agent(
    request: ReviewRequest,
    static_hints: list[StaticHint],
    llm: LLMClient | None = None,
) -> tuple[list[Finding], AgentRun, list[str]]:
    llm = llm or create_llm_client(request)
    started = time.perf_counter()
    errors: list[str] = []

    try:
        raw_output = llm.generate_findings(request, static_hints)
        payload = json.loads(raw_output)
        findings = [Finding(**finding) for finding in payload.get("findings", [])]
        run = AgentRun(
            agent_name="review_agent",
            input_tokens=llm.input_tokens or _rough_token_count(request.diff),
            output_tokens=llm.output_tokens or _rough_token_count(raw_output),
            latency_ms=int((time.perf_counter() - started) * 1000),
            status="succeeded",
            provider=llm.provider_name,
            model=llm.model_name,
        )
        return findings, run, errors
    except TimeoutError as exc:
        errors.append(str(exc))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        errors.append(f"invalid review agent output: {exc}")
    except Exception as exc:  # noqa: BLE001 - provider failures become structured runs
        errors.append(f"review provider request failed: {exc}")

    return [], AgentRun(
        agent_name="review_agent",
        latency_ms=int((time.perf_counter() - started) * 1000),
        status="failed",
        error_message="; ".join(errors),
        provider=llm.provider_name,
        model=llm.model_name,
    ), errors


def _rough_token_count(text: str) -> int:
    return max(1, len(text.split()))
