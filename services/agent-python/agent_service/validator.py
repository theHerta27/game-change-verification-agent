from __future__ import annotations

from agent_service.schemas import (
    ParsedDiff,
    ReviewResponse,
    VALID_CATEGORIES,
    VALID_SEVERITIES,
    ValidationErrorDetail,
    ValidationResult,
)


def validate_response(
    response: ReviewResponse,
    parsed_diff: ParsedDiff,
    validate_test_suggestions: bool = True,
) -> ValidationResult:
    errors: list[str] = []
    details: list[ValidationErrorDetail] = []
    files = parsed_diff.file_paths

    for index, finding in enumerate(response.findings):
        prefix = f"findings[{index}]"
        if finding.file_path not in files:
            reason = f"文件不在当前 diff 中：{finding.file_path}"
            errors.append(f"{prefix}.file_path is not present in diff: {finding.file_path}")
            details.append(_detail(f"{prefix}.file_path", "diff 中存在的文件路径", reason))
            continue

        mapped_lines = parsed_diff.mapped_new_lines(finding.file_path)
        if finding.line_number not in mapped_lines:
            errors.append(f"{prefix}.line_number is not mapped in diff: {finding.line_number}")
            details.append(
                _detail(
                    f"{prefix}.line_number",
                    "该文件 diff 中可映射的新行号",
                    f"行号 {finding.line_number} 无法映射到新增行",
                )
            )

        if finding.severity not in VALID_SEVERITIES:
            errors.append(f"{prefix}.severity is invalid: {finding.severity}")
            details.append(
                _detail(f"{prefix}.severity", "low | medium | high | critical", f"不允许的枚举值：{finding.severity}")
            )

        if finding.category not in VALID_CATEGORIES:
            errors.append(f"{prefix}.category is invalid: {finding.category}")
            details.append(
                _detail(
                    f"{prefix}.category",
                    " | ".join(sorted(VALID_CATEGORIES)),
                    f"不允许的枚举值：{finding.category}",
                )
            )

        if not 0 <= finding.confidence <= 1:
            errors.append(f"{prefix}.confidence must be between 0 and 1")
            details.append(_detail(f"{prefix}.confidence", "0 到 1 之间的数字", "数值超出范围"))

        if not finding.evidence.strip():
            errors.append(f"{prefix}.evidence must be non-empty")
            details.append(_detail(f"{prefix}.evidence", "非空代码证据", "字段为空"))

    if validate_test_suggestions:
        for index, suggestion in enumerate(response.test_suggestions):
            if suggestion.finding_index < 0 or suggestion.finding_index >= len(response.findings):
                errors.append(
                    f"test_suggestions[{index}].finding_index is out of range: {suggestion.finding_index}"
                )
                details.append(
                    _detail(
                        f"test_suggestions[{index}].finding_index",
                        f"0 到 {max(len(response.findings) - 1, 0)} 的已有 finding 索引",
                        f"索引 {suggestion.finding_index} 越界",
                    )
                )

    return ValidationResult(valid=not errors, errors=errors, error_details=details)


def _detail(field: str, expected: str, reason: str) -> ValidationErrorDetail:
    return ValidationErrorDetail(
        stage="deterministic_validator",
        field=field,
        expected=expected,
        reason=reason,
    )
