from __future__ import annotations

from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field


VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_CATEGORIES = {
    "timeout_missing",
    "resource_leak",
    "sql_injection",
    "error_handling",
    "unsafe_eval",
    "security",
    "performance",
    "determinism",
}


class DiffLine(BaseModel):
    line_type: str
    content: str
    old_line_number: Optional[int] = None
    new_line_number: Optional[int] = None


class DiffHunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    section_header: str = ""
    lines: list[DiffLine] = Field(default_factory=list)


class DiffFile(BaseModel):
    old_path: str
    new_path: str
    hunks: list[DiffHunk] = Field(default_factory=list)


class ParsedDiff(BaseModel):
    files: list[DiffFile] = Field(default_factory=list)

    @property
    def file_paths(self) -> set[str]:
        return {file.new_path for file in self.files if file.new_path != "/dev/null"}

    def mapped_new_lines(self, file_path: str) -> set[int]:
        lines: set[int] = set()
        for file in self.files:
            if file.new_path != file_path:
                continue
            for hunk in file.hunks:
                for line in hunk.lines:
                    if line.new_line_number is not None:
                        lines.add(line.new_line_number)
        return lines


class Finding(BaseModel):
    file_path: str
    line_number: int
    severity: str
    category: str
    title: str
    evidence: str
    suggestion: str
    confidence: float
    source: str = "single_agent"


class TestSuggestion(BaseModel):
    __test__: ClassVar[bool] = False

    finding_index: int
    target_file: str
    test_name: str
    description: str
    code: Optional[str] = None


class StaticHint(BaseModel):
    rule_id: str
    language: str
    file_path: str
    line_number: int
    category: str
    message: str
    evidence_line: str
    confidence: float = 0.8


class AgentRun(BaseModel):
    agent_name: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: int
    status: str
    error_message: Optional[str] = None
    provider: str = "mock"
    model: Optional[str] = None


class ValidationErrorDetail(BaseModel):
    stage: str
    field: str
    expected: str
    reason: str


class SanitizedDebugInfo(BaseModel):
    provider: str
    model: Optional[str] = None
    workflow: str
    language: str
    validation_errors: list[ValidationErrorDetail] = Field(default_factory=list)
    repair_attempted: bool = False
    final_status: str


class LLMConfig(BaseModel):
    provider: str = "openai_compatible"
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(default=None, repr=False)
    model: Optional[str] = None
    timeout_seconds: int = Field(default=30, ge=1, le=120)


class ReviewRequest(BaseModel):
    diff: str
    language: str
    mode: str = "mock"
    mock_case: str = "success"
    mock_latency_ms: int = 0
    prompt_version: str = "single-agent-v1"
    schema_version: str = "phase1-v1"
    static_rule_version: str = "phase1-rules-v1"
    llm_config: Optional[LLMConfig] = Field(default=None, repr=False)
    workflow: str = "single_agent"


class ReviewResponse(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    test_suggestions: list[TestSuggestion] = Field(default_factory=list)
    agent_runs: list[AgentRun] = Field(default_factory=list)
    report_markdown: str = ""
    validation_errors: list[str] = Field(default_factory=list)
    parsed_diff_json: Optional[dict[str, Any]] = None
    static_hints_json: Optional[list[dict[str, Any]]] = None
    debug_info: Optional[SanitizedDebugInfo] = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    error_details: list[ValidationErrorDetail] = Field(default_factory=list)
