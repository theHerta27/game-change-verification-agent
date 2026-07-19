from __future__ import annotations

import re

from agent_service.schemas import ParsedDiff, StaticHint
from agent_service.tools.diff_parser import iter_added_lines


SQL_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


def run_static_checks(parsed_diff: ParsedDiff, language: str) -> list[StaticHint]:
    language = language.lower()
    if language == "go":
        return _check_go(parsed_diff)
    if language == "python":
        return _check_python(parsed_diff)
    if language in {"csharp", "cs", "c#"}:
        return _check_csharp(parsed_diff)
    return []


def _hint(
    rule_id: str,
    language: str,
    file_path: str,
    line_number: int,
    category: str,
    message: str,
    evidence_line: str,
    confidence: float = 0.82,
) -> StaticHint:
    return StaticHint(
        rule_id=rule_id,
        language=language,
        file_path=file_path,
        line_number=line_number,
        category=category,
        message=message,
        evidence_line=evidence_line.strip(),
        confidence=confidence,
    )


def _file_lines(file) -> list[tuple[int | None, str]]:
    lines: list[tuple[int | None, str]] = []
    for hunk in file.hunks:
        for line in hunk.lines:
            if line.line_type in {"added", "context"}:
                lines.append((line.new_line_number, line.content))
    return lines


def _file_text(file) -> str:
    return "\n".join(content for _line_number, content in _file_lines(file))


def _err_is_handled_after_assignment(file, assignment_line_number: int) -> bool:
    for line_number, content in _file_lines(file):
        if line_number is None or line_number < assignment_line_number:
            continue
        stripped = content.strip()
        if re.search(r"\bif\s+err\s*!=\s*nil\b", stripped):
            return True
        if stripped.startswith("return ") and re.search(r"(^|,\s*)err(\s*,|$)", stripped.removeprefix("return ").strip()):
            return True
    return False


def _check_go(parsed_diff: ParsedDiff) -> list[StaticHint]:
    hints: list[StaticHint] = []
    file_text_cache = {file.new_path: _file_text(file) for file in parsed_diff.files}

    for file, _hunk, line in iter_added_lines(parsed_diff):
        content = line.content.strip()
        line_number = line.new_line_number or 0

        if re.search(r"\bhttp\.(Get|Post|Head)\s*\(", content):
            hints.append(
                _hint(
                    "go_http_no_timeout",
                    "go",
                    file.new_path,
                    line_number,
                    "timeout_missing",
                    "http package helper is used without an explicit timeout",
                    content,
                )
            )

        if "resp.Body" in content and "Close()" not in file_text_cache.get(file.new_path, ""):
            hints.append(
                _hint(
                    "go_resp_body_not_closed",
                    "go",
                    file.new_path,
                    line_number,
                    "resource_leak",
                    "response body is used but no resp.Body.Close() is visible in the diff context",
                    content,
                )
            )

        if re.search(r"\berr\s*:?=", content) and not _err_is_handled_after_assignment(file, line_number):
            hints.append(
                _hint(
                    "go_ignored_err",
                    "go",
                    file.new_path,
                    line_number,
                    "error_handling",
                    "err is assigned but no error handling is visible in the diff context",
                    content,
                )
            )
        elif re.search(r"\b_\s*,\s*err\s*:=", content) or re.search(r"\berr\s*=\s*_", content):
            hints.append(
                _hint(
                    "go_ignored_err",
                    "go",
                    file.new_path,
                    line_number,
                    "error_handling",
                    "error value appears to be ignored",
                    content,
                )
            )

        if SQL_RE.search(content) and ("+" in content or "fmt.Sprintf" in content):
            hints.append(
                _hint(
                    "go_sql_string_concat",
                    "go",
                    file.new_path,
                    line_number,
                    "sql_injection",
                    "SQL statement appears to be built with string formatting or concatenation",
                    content,
                )
            )

    return hints


def _check_python(parsed_diff: ParsedDiff) -> list[StaticHint]:
    hints: list[StaticHint] = []

    for file, _hunk, line in iter_added_lines(parsed_diff):
        content = line.content.strip()
        line_number = line.new_line_number or 0

        if re.search(r"\brequests\.(get|post|put|delete|patch)\s*\(", content) and "timeout=" not in content:
            hints.append(
                _hint(
                    "python_requests_no_timeout",
                    "python",
                    file.new_path,
                    line_number,
                    "timeout_missing",
                    "requests call has no explicit timeout",
                    content,
                )
            )

        if content == "except:" or content.startswith("except Exception:"):
            hints.append(
                _hint(
                    "python_bare_except",
                    "python",
                    file.new_path,
                    line_number,
                    "error_handling",
                    "broad exception handler can hide failures",
                    content,
                )
            )

        if SQL_RE.search(content) and ("+" in content or "f\"" in content or "f'" in content or "%" in content):
            hints.append(
                _hint(
                    "python_sql_string_concat",
                    "python",
                    file.new_path,
                    line_number,
                    "sql_injection",
                    "SQL statement appears to use interpolation or concatenation",
                    content,
                )
            )

        if re.search(r"\b(eval|exec)\s*\(", content):
            hints.append(
                _hint(
                    "python_eval_exec",
                    "python",
                    file.new_path,
                    line_number,
                    "security",
                    "dynamic code execution is introduced",
                    content,
                )
            )

    return hints


def _check_csharp(parsed_diff: ParsedDiff) -> list[StaticHint]:
    hints: list[StaticHint] = []

    for file in parsed_diff.files:
        current_method = ""
        for line_number, raw_content in _file_lines(file):
            content = raw_content.strip()
            method_match = re.search(
                r"\b(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?"
                r"(?:void|[A-Za-z_][\w<>\[\],.?]*)\s+([A-Za-z_]\w*)\s*\(",
                content,
            )
            if method_match:
                current_method = method_match.group(1)
            if line_number is None or not _is_added_line(file, line_number, raw_content):
                continue

            if re.search(r"\bProcess\.Start\s*\(|\bSystem\.Diagnostics\.Process\b|\bDllImport\s*\(", content):
                hints.append(
                    _hint(
                        "csharp_external_execution",
                        "csharp",
                        file.new_path,
                        line_number,
                        "security",
                        "C# patch introduces process or native-code execution",
                        content,
                        confidence=0.97,
                    )
                )

            if re.search(r"\bcatch\s*\(\s*Exception(?:\s+\w+)?\s*\)", content) or re.match(r"catch\s*\{", content):
                hints.append(
                    _hint(
                        "csharp_broad_catch",
                        "csharp",
                        file.new_path,
                        line_number,
                        "error_handling",
                        "Broad exception handling can hide Unity runtime failures",
                        content,
                    )
                )

            if current_method in {"Update", "FixedUpdate", "LateUpdate"}:
                if re.search(r"\b(?:File|Directory)\.(?:Read|Write|Open|Create)|\bResources\.Load|\bGameObject\.Find", content):
                    hints.append(
                        _hint(
                            "csharp_per_frame_io_or_lookup",
                            "csharp",
                            file.new_path,
                            line_number,
                            "performance",
                            "Per-frame I/O or global lookup can cause frame-time spikes",
                            content,
                        )
                    )
                if re.search(r"\b(?:Instantiate|Destroy)\s*\(", content):
                    hints.append(
                        _hint(
                            "csharp_per_frame_allocation",
                            "csharp",
                            file.new_path,
                            line_number,
                            "performance",
                            "Per-frame object creation or destruction can cause allocations and frame-time spikes",
                            content,
                        )
                    )

            if "UnityEngine.Random" in content and file.new_path.endswith("RuntimeDemoBootstrap.cs"):
                hints.append(
                    _hint(
                        "csharp_unseeded_runtime_random",
                        "csharp",
                        file.new_path,
                        line_number,
                        "determinism",
                        "Runtime demo introduces UnityEngine.Random outside the fixed-seed test contract",
                        content,
                    )
                )

    return hints


def _is_added_line(file, line_number: int, content: str) -> bool:
    return any(
        line.line_type == "added"
        and line.new_line_number == line_number
        and line.content == content
        for hunk in file.hunks
        for line in hunk.lines
    )
