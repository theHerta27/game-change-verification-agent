from __future__ import annotations

from agent_service.schemas import ReviewResponse


def build_markdown_report(response: ReviewResponse, language: str) -> str:
    lines = [
        "# DevQuality Agent 代码审查报告",
        "",
        f"- 语言：`{language}`",
        f"- 风险项：{len(response.findings)}",
        f"- 测试建议：{len(response.test_suggestions)}",
        f"- Validator 通过：{not response.validation_errors}",
        "",
    ]

    if response.validation_errors:
        lines.extend(["## 校验错误", ""])
        for error in response.validation_errors:
            lines.append(f"- {error}")
        lines.append("")

    lines.extend(["## 风险项", ""])
    if not response.findings:
        lines.extend(["未发现风险项。", ""])
    for index, finding in enumerate(response.findings):
        lines.extend(
            [
                f"### F{index}: {finding.title}",
                "",
                f"- 文件：`{finding.file_path}`",
                f"- 行号：{finding.line_number}",
                f"- 严重程度：`{finding.severity}`",
                f"- 分类：{_category_label(finding.category)} (`{finding.category}`)",
                f"- 置信度：{finding.confidence:.2f}",
                f"- 来源：`{finding.source}`",
                f"- 证据：`{finding.evidence}`",
                f"- 建议：{finding.suggestion}",
                "",
            ]
        )

    lines.extend(["## 测试建议", ""])
    if not response.test_suggestions:
        lines.extend(["暂无测试建议。", ""])
    for suggestion in response.test_suggestions:
        lines.extend(
            [
                f"### {suggestion.test_name}",
                "",
                f"- Finding 索引：{suggestion.finding_index}",
                f"- 目标文件：`{suggestion.target_file}`",
                f"- 说明：{suggestion.description}",
                "",
            ]
        )
        if suggestion.code:
            lines.extend(["```", suggestion.code, "```", ""])

    lines.extend(["## Agent 运行记录", ""])
    for run in response.agent_runs:
        lines.append(
            f"- `{run.agent_name}` provider={run.provider} model={run.model or '-'} "
            f"status={run.status} latency_ms={run.latency_ms}"
            + (f" error={run.error_message}" if run.error_message else "")
        )
    lines.append("")
    return "\n".join(lines)


def _category_label(category: str) -> str:
    return {
        "timeout_missing": "缺少超时控制",
        "resource_leak": "资源泄露",
        "sql_injection": "SQL 注入风险",
        "error_handling": "错误处理问题",
        "unsafe_eval": "不安全 eval/exec",
        "security": "安全风险",
    }.get(category, "其他风险")
