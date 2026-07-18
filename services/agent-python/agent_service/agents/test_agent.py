from __future__ import annotations

import json
import time

from pydantic import ValidationError

from agent_service.llm.base import LLMClient
from agent_service.llm.factory import create_llm_client
from agent_service.schemas import AgentRun, Finding, ReviewRequest, TestSuggestion


def run_test_agent(
    request: ReviewRequest,
    validated_findings: list[Finding],
    llm: LLMClient | None = None,
) -> tuple[list[TestSuggestion], AgentRun, list[str]]:
    llm = llm or create_llm_client(request)
    started = time.perf_counter()
    errors: list[str] = []
    finding_payload = [finding.model_dump() for finding in validated_findings]

    try:
        raw_output = llm.generate_tests(request, finding_payload)
        payload = json.loads(raw_output)
        suggestions = [
            TestSuggestion(**suggestion) for suggestion in payload.get("test_suggestions", [])
        ]
        run = AgentRun(
            agent_name="test_agent",
            input_tokens=llm.input_tokens or _rough_token_count(json.dumps(finding_payload, ensure_ascii=False)),
            output_tokens=llm.output_tokens or _rough_token_count(raw_output),
            latency_ms=int((time.perf_counter() - started) * 1000),
            status="succeeded",
            provider=llm.provider_name,
            model=llm.model_name,
        )
        return suggestions, run, errors
    except TimeoutError as exc:
        errors.append(str(exc))
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        errors.append(f"invalid test agent output: {exc}")
    except Exception as exc:  # noqa: BLE001 - provider failures become structured runs
        errors.append(f"test provider request failed: {exc}")

    return [], AgentRun(
        agent_name="test_agent",
        latency_ms=int((time.perf_counter() - started) * 1000),
        status="failed",
        error_message="; ".join(errors),
        provider=llm.provider_name,
        model=llm.model_name,
    ), errors


def _rough_token_count(text: str) -> int:
    return max(1, len(text.split()))
