from __future__ import annotations

from agent_service.llm.base import LLMClient
from agent_service.schemas import (
    ReviewRequest,
    SanitizedDebugInfo,
    ValidationErrorDetail,
)


def build_debug_info(
    request: ReviewRequest,
    llm: LLMClient | None,
    details: list[ValidationErrorDetail] | None = None,
    fallback_errors: list[str] | None = None,
) -> SanitizedDebugInfo:
    merged = list(details or [])
    if llm is not None:
        merged = [ValidationErrorDetail(**item) for item in llm.validation_error_details] + merged
    if not merged:
        merged = [
            ValidationErrorDetail(
                stage="agent_workflow",
                field="$",
                expected="成功完成模型调用与结构化校验",
                reason=error[:300],
            )
            for error in (fallback_errors or [])
        ]
    unique: list[ValidationErrorDetail] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in merged:
        key = (item.stage, item.field, item.expected, item.reason)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return SanitizedDebugInfo(
        provider=llm.provider_name if llm else _requested_provider(request),
        model=llm.model_name if llm else (request.llm_config.model if request.llm_config else None),
        workflow=getattr(request, "workflow", None) or "unknown",
        language=request.language,
        validation_errors=unique,
        repair_attempted=bool(llm and llm.repair_attempted),
        final_status="failed",
    )


def _requested_provider(request: ReviewRequest) -> str:
    if request.mode == "mock":
        return "mock"
    if request.llm_config and request.llm_config.provider:
        return request.llm_config.provider
    return "openai_compatible"
