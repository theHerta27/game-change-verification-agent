from __future__ import annotations

import json
import time

from pydantic import ValidationError

from agent_service.debug_info import build_debug_info
from agent_service.llm.base import LLMClient
from agent_service.llm.factory import create_llm_client
from agent_service.report_builder import build_markdown_report
from agent_service.schemas import AgentRun, Finding, ReviewRequest, ReviewResponse, TestSuggestion
from agent_service.tools.diff_parser import parse_unified_diff
from agent_service.tools.static_checker import run_static_checks
from agent_service.validator import validate_response


def run_single_agent(request: ReviewRequest, llm: LLMClient | None = None) -> ReviewResponse:
    parsed_diff = parse_unified_diff(request.diff)
    static_hints = run_static_checks(parsed_diff, request.language)
    response = ReviewResponse(
        parsed_diff_json=parsed_diff.model_dump(),
        static_hints_json=[hint.model_dump() for hint in static_hints],
    )
    if llm is None:
        try:
            llm = create_llm_client(request)
        except Exception as exc:  # noqa: BLE001 - configuration failures are structured
            response.agent_runs.append(
                AgentRun(
                    agent_name="single_agent",
                    latency_ms=0,
                    status="failed",
                    error_message=str(exc),
                    provider=_requested_provider(request),
                    model=request.llm_config.model if request.llm_config else None,
                )
            )
            response.validation_errors.append(str(exc))
            response.debug_info = build_debug_info(request, None, fallback_errors=[str(exc)])
            response.report_markdown = build_markdown_report(response, request.language)
            return response

    started = time.perf_counter()

    try:
        raw_output = llm.generate(request, static_hints)
        latency_ms = int((time.perf_counter() - started) * 1000)
        response.agent_runs.append(
            AgentRun(
                agent_name="single_agent",
                input_tokens=llm.input_tokens or _rough_token_count(request.diff),
                output_tokens=llm.output_tokens or _rough_token_count(raw_output),
                latency_ms=latency_ms,
                status="succeeded",
                provider=llm.provider_name,
                model=llm.model_name,
            )
        )
        payload = json.loads(raw_output)
        response.findings = [Finding(**finding) for finding in payload.get("findings", [])]
        response.test_suggestions = [
            TestSuggestion(**suggestion) for suggestion in payload.get("test_suggestions", [])
        ]
    except TimeoutError as exc:
        response.agent_runs.append(
            AgentRun(
                agent_name="single_agent",
                latency_ms=int((time.perf_counter() - started) * 1000),
                status="failed",
                error_message=str(exc),
                provider=llm.provider_name,
                model=llm.model_name,
            )
        )
        response.validation_errors.append(str(exc))
        response.debug_info = build_debug_info(request, llm, fallback_errors=[str(exc)])
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        response.agent_runs.append(
            AgentRun(
                agent_name="single_agent",
                latency_ms=int((time.perf_counter() - started) * 1000),
                status="failed",
                error_message=str(exc),
                provider=llm.provider_name,
                model=llm.model_name,
            )
        )
        response.validation_errors.append(f"invalid {llm.output_label} output: {exc}")
        response.debug_info = build_debug_info(
            request,
            llm,
            fallback_errors=[f"invalid {llm.output_label} output: {exc}"],
        )
    except Exception as exc:  # noqa: BLE001 - provider failures become structured runs
        response.agent_runs.append(
            AgentRun(
                agent_name="single_agent",
                latency_ms=int((time.perf_counter() - started) * 1000),
                status="failed",
                error_message=str(exc),
                provider=llm.provider_name,
                model=llm.model_name,
            )
        )
        response.validation_errors.append(f"{llm.output_label} request failed: {exc}")
        response.debug_info = build_debug_info(
            request,
            llm,
            fallback_errors=[f"{llm.output_label} request failed: {exc}"],
        )

    validation = validate_response(response, parsed_diff)
    response.validation_errors.extend(validation.errors)
    if validation.errors:
        response.debug_info = build_debug_info(
            request,
            llm,
            details=validation.error_details,
            fallback_errors=validation.errors,
        )
    response.report_markdown = build_markdown_report(response, request.language)
    return response


def _rough_token_count(text: str) -> int:
    return max(1, len(text.split()))


def _requested_provider(request: ReviewRequest) -> str:
    if request.mode == "mock":
        return "mock"
    if request.llm_config and request.llm_config.provider:
        return request.llm_config.provider
    return "openai_compatible"
