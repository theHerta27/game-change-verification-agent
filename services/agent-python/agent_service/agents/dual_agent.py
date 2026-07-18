from __future__ import annotations

import json
import time

from pydantic import ValidationError

from agent_service.agents.review_agent import run_review_agent
from agent_service.agents.test_agent import run_test_agent
from agent_service.debug_info import build_debug_info
from agent_service.llm.base import LLMClient
from agent_service.llm.factory import create_llm_client
from agent_service.report_builder import build_markdown_report
from agent_service.schemas import AgentRun, Finding, ReviewRequest, ReviewResponse
from agent_service.tools.diff_parser import parse_unified_diff
from agent_service.tools.static_checker import run_static_checks
from agent_service.validator import validate_response


def run_dual_agent(request: ReviewRequest, llm: LLMClient | None = None) -> ReviewResponse:
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
            provider = request.llm_config.provider if request.llm_config else "openai_compatible"
            model = request.llm_config.model if request.llm_config else None
            response.agent_runs.append(
                AgentRun(
                    agent_name="review_agent",
                    latency_ms=0,
                    status="failed",
                    error_message=str(exc),
                    provider=provider,
                    model=model,
                )
            )
            response.validation_errors.append(str(exc))
            response.debug_info = build_debug_info(request, None, fallback_errors=[str(exc)])
            response.report_markdown = build_markdown_report(response, request.language)
            return response

    findings, review_run, review_errors = run_review_agent(request, static_hints, llm)
    response.findings = findings
    response.agent_runs.append(review_run)
    response.validation_errors.extend(review_errors)
    if review_errors:
        response.debug_info = build_debug_info(
            request, llm, fallback_errors=review_errors
        )

    finding_validation = validate_response(response, parsed_diff, validate_test_suggestions=False)
    if finding_validation.errors and not review_errors:
        repaired_findings, repair_run, repair_errors = _repair_findings(
            request,
            llm,
            response.findings,
            finding_validation.error_details,
            static_hints,
        )
        if repair_run is not None:
            response.agent_runs.append(repair_run)
        if repaired_findings is not None:
            response.findings = repaired_findings
            finding_validation = validate_response(
                response, parsed_diff, validate_test_suggestions=False
            )
            for detail in finding_validation.error_details:
                detail.stage = "post_repair_validator"
        if repair_errors:
            response.validation_errors.extend(repair_errors)

    response.validation_errors.extend(finding_validation.errors)
    if finding_validation.errors:
        response.debug_info = build_debug_info(
            request,
            llm,
            details=finding_validation.error_details,
            fallback_errors=finding_validation.errors,
        )

    if not response.validation_errors:
        suggestions, test_run, test_errors = run_test_agent(request, response.findings, llm)
        response.test_suggestions = suggestions
        response.agent_runs.append(test_run)
        response.validation_errors.extend(test_errors)
        if test_errors:
            response.debug_info = build_debug_info(
                request, llm, fallback_errors=test_errors
            )
        full_validation = validate_response(response, parsed_diff)
        response.validation_errors.extend(full_validation.errors)
        if full_validation.errors:
            response.debug_info = build_debug_info(
                request,
                llm,
                details=full_validation.error_details,
                fallback_errors=full_validation.errors,
            )

    response.report_markdown = build_markdown_report(response, request.language)
    return response


def _repair_findings(
    request: ReviewRequest,
    llm: LLMClient,
    findings: list[Finding],
    validation_details: list,
    static_hints: list,
) -> tuple[list[Finding] | None, AgentRun | None, list[str]]:
    started = time.perf_counter()
    details = [detail.model_dump() for detail in validation_details]
    try:
        raw = llm.repair_findings(
            request,
            [finding.model_dump() for finding in findings],
            details,
            static_hints,
        )
        if raw is None:
            return None, None, []
        payload = json.loads(raw)
        repaired = [Finding(**finding) for finding in payload.get("findings", [])]
        return repaired, AgentRun(
            agent_name="review_repair",
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
            status="succeeded",
            provider=llm.provider_name,
            model=llm.model_name,
        ), []
    except Exception as exc:  # noqa: BLE001 - provider/repair failures become structured runs
        message = f"review repair failed: {exc}"
        return None, AgentRun(
            agent_name="review_repair",
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
            status="failed",
            error_message=message,
            provider=llm.provider_name,
            model=llm.model_name,
        ), [message]
