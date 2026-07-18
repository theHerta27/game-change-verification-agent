from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_service.agents.dual_agent import run_dual_agent
from agent_service.agents.single_agent import run_single_agent
from agent_service.schemas import ReviewRequest, ReviewResponse


@dataclass(frozen=True)
class Sample:
    name: str
    language: str
    path: str
    notes: str


SAMPLES = [
    Sample("go_http_no_timeout", "go", "examples/go_http_no_timeout.patch", "err is returned; should not be ignored-error after Phase 1.5 fix"),
    Sample("go_resp_body_not_closed", "go", "examples/go_resp_body_not_closed.patch", "resource leak sample"),
    Sample("python_requests_no_timeout", "python", "examples/python_requests_no_timeout.patch", "timeout sample"),
    Sample("python_sql_injection", "python", "examples/python_sql_injection.patch", "SQL interpolation and eval sample"),
    Sample("negative_safe_logging", "python", "examples/negative_safe_logging.patch", "negative diff; expected zero findings"),
]


def generate_phase1_summary(project_root: Path) -> None:
    rows = []
    for sample in SAMPLES:
        response = _run_sample(project_root, sample, mode="single_agent")
        categories = ", ".join(sorted({finding.category for finding in response.findings})) or "-"
        rows.append(
            [
                sample.name,
                sample.language,
                str(len(response.findings)),
                str(len(response.test_suggestions)),
                str(not response.validation_errors),
                categories,
                sample.notes,
            ]
        )

    _write_table(
        project_root / "outputs" / "phase1_summary.md",
        "Phase 1 Summary",
        ["sample name", "language", "findings count", "test suggestions count", "validator passed", "main categories", "notes / badcase"],
        rows,
    )


def generate_phase1_badcases(project_root: Path) -> None:
    content = """# Phase 1 Badcases

## go_ignored_err false positive on returned error

- Sample: `go_http_no_timeout.patch`
- Original behavior: `resp, err := http.Get(url)` followed by `return resp, err` was flagged as `go_ignored_err`.
- Reason: the first implementation only checked for `if err` in the file context and did not recognize returning `err` to the caller as valid handling.
- Fix: `static_checker` now scans added/context lines after the assignment. If it sees `if err != nil` or `return ..., err`, it suppresses `go_ignored_err`.
- Tests added:
  - `test_go_err_returned_should_not_trigger_ignored_err`
  - `test_go_err_checked_should_not_trigger_ignored_err`
  - `test_go_err_assigned_but_unused_should_trigger_ignored_err`
- Fix result: `go_http_no_timeout.patch` now reports only `timeout_missing`; it no longer reports `error_handling`.
"""
    path = project_root / "outputs" / "phase1_badcases.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_phase2_comparison(project_root: Path) -> None:
    rows = []
    details = []
    for sample in SAMPLES:
        single = _run_sample(project_root, sample, mode="single_agent")
        dual = _run_sample(project_root, sample, mode="dual_agent")
        single_refs_ok = _suggestions_reference_findings(single)
        dual_refs_ok = _suggestions_reference_findings(dual)
        rows.append(
            [
                sample.name,
                sample.language,
                str(not single.validation_errors),
                str(not dual.validation_errors),
                str(len(single.findings)),
                str(len(dual.findings)),
                str(len(single.test_suggestions)),
                str(len(dual.test_suggestions)),
                str(single_refs_ok),
                str(dual_refs_ok),
                str(_latency_ms(single)),
                str(_latency_ms(dual)),
                str(_token_estimate(single)),
                str(_token_estimate(dual)),
            ]
        )
        details.append(
            f"- `{sample.name}`: dual mode separates review validation before test generation, "
            f"so review failures and test-generation failures are easier to attribute."
        )

    content = _table_markdown(
        "Phase 2 Comparison",
        ["sample", "language", "single JSON stable", "dual JSON stable", "single findings", "dual findings", "single tests", "dual tests", "single refs ok", "dual refs ok", "single latency ms", "dual latency ms", "single token estimate", "dual token estimate"],
        rows,
    )
    content += "\n## Badcase Attribution\n\n" + "\n".join(details) + "\n"
    path = project_root / "outputs" / "phase2_comparison.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _run_sample(project_root: Path, sample: Sample, mode: str) -> ReviewResponse:
    request = ReviewRequest(
        diff=(project_root / sample.path).read_text(encoding="utf-8"),
        language=sample.language,
        mode="mock",
    )
    if mode == "dual_agent":
        return run_dual_agent(request)
    return run_single_agent(request)


def _write_table(path: Path, title: str, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_table_markdown(title, headers, rows), encoding="utf-8")


def _table_markdown(title: str, headers: list[str], rows: list[list[str]]) -> str:
    lines = [f"# {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _suggestions_reference_findings(response: ReviewResponse) -> bool:
    return all(0 <= suggestion.finding_index < len(response.findings) for suggestion in response.test_suggestions)


def _latency_ms(response: ReviewResponse) -> int:
    return sum(run.latency_ms for run in response.agent_runs)


def _token_estimate(response: ReviewResponse) -> int:
    return sum((run.input_tokens or 0) + (run.output_tokens or 0) for run in response.agent_runs)
