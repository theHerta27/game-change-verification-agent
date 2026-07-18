from __future__ import annotations

import json
import socket
from typing import Any, Literal, TypeVar
from urllib import error, request

from pydantic import BaseModel, Field, ValidationError

from agent_service.llm.base import LLMClient
from agent_service.schemas import Finding, ReviewRequest, StaticHint, TestSuggestion
from agent_service.tools.diff_parser import parse_unified_diff


class _RealFinding(Finding):
    severity: Literal["low", "medium", "high", "critical"]
    category: Literal[
        "timeout_missing",
        "resource_leak",
        "sql_injection",
        "error_handling",
        "unsafe_eval",
        "security",
    ]
    source: Literal["openai_compatible"]


class _RealTestSuggestion(TestSuggestion):
    finding_index: int


class _CombinedOutput(BaseModel):
    findings: list[_RealFinding] = Field(default_factory=list)
    test_suggestions: list[_RealTestSuggestion] = Field(default_factory=list)


class _FindingsOutput(BaseModel):
    findings: list[_RealFinding] = Field(default_factory=list)


class _TestsOutput(BaseModel):
    test_suggestions: list[_RealTestSuggestion] = Field(default_factory=list)


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class OpenAICompatibleLLM(LLMClient):
    provider_name = "openai_compatible"
    output_label = "openai-compatible llm"

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self.input_tokens = 0
        self.output_tokens = 0
        self.repair_attempted = False
        self.validation_error_details: list[dict[str, str]] = []

    def generate(self, review_request: ReviewRequest, static_hints: list[StaticHint]) -> str:
        return self._generate(
            system_prompt=_system_prompt("同时输出 findings 和 test_suggestions"),
            user_prompt=_review_prompt(review_request, static_hints),
            output_model=_CombinedOutput,
        )

    def generate_findings(self, review_request: ReviewRequest, static_hints: list[StaticHint]) -> str:
        return self._generate(
            system_prompt=_system_prompt("只输出 findings，不要输出测试建议"),
            user_prompt=_review_prompt(review_request, static_hints),
            output_model=_FindingsOutput,
        )

    def generate_tests(self, review_request: ReviewRequest, findings: list[dict]) -> str:
        payload = json.dumps(findings, ensure_ascii=False, indent=2)
        return self._generate(
            system_prompt=_system_prompt("只基于已验证 findings 输出 test_suggestions"),
            user_prompt=(
                f"语言：{review_request.language}\n"
                "以下 findings 已通过确定性校验。每条测试建议必须使用有效的 finding_index，"
                "target_file 必须与对应 finding.file_path 一致。\n"
                f"findings:\n{payload}"
            ),
            output_model=_TestsOutput,
        )

    def repair_findings(
        self,
        review_request: ReviewRequest,
        findings: list[dict],
        validation_errors: list[dict[str, str]],
        static_hints: list[StaticHint],
    ) -> str:
        self.input_tokens = 0
        self.output_tokens = 0
        self.repair_attempted = True
        self.validation_error_details = validation_errors.copy()
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 DevQuality finding repair 工具。只输出 JSON；禁止 Markdown fence；"
                    "禁止解释文字；必须严格符合给定 schema。"
                    "只能修正字段值，不得增加与 diff 无关的风险。"
                    "file_path 和 line_number 必须从 allowed_locations 选择。"
                    "severity 和 category 必须使用 schema 中的英文枚举。"
                    "title 和 suggestion 必须使用简体中文。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"目标 schema：{json.dumps(_FindingsOutput.model_json_schema(), ensure_ascii=False)}\n"
                    f"allowed_locations：{json.dumps(_allowed_locations(review_request), ensure_ascii=False)}\n"
                    f"static_hints：{json.dumps([hint.model_dump() for hint in static_hints], ensure_ascii=False)}\n"
                    f"validator_errors：{json.dumps(validation_errors, ensure_ascii=False)}\n"
                    f"待修复 findings：{json.dumps(findings, ensure_ascii=False)}"
                ),
            },
        ]
        raw = self._chat(messages)
        try:
            return _validate_output(raw, _FindingsOutput)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            self.validation_error_details.extend(_exception_details(exc, "schema_repair"))
            raise ValueError(f"finding repair 输出无效: {_safe_error(exc)}") from exc

    def _generate(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: type[OutputModel],
    ) -> str:
        # Metadata is scoped to one agent stage; repair calls within the stage are accumulated.
        self.input_tokens = 0
        self.output_tokens = 0
        self.repair_attempted = False
        self.validation_error_details = []
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        raw = self._chat(messages)
        try:
            return _validate_output(raw, output_model)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
            self.validation_error_details = _exception_details(exc, "first_output")
            self.repair_attempted = True
            repair_messages = [
                {
                    "role": "system",
                    "content": (
                        "你是 JSON schema repair 工具。只输出一个 JSON 对象；禁止 Markdown fence；"
                        "禁止解释文字；必须严格符合给定 JSON Schema。"
                        "finding_index 必须指向输入中已有 finding；"
                        "severity 只能使用 low、medium、high、critical；"
                        "category 只能使用 timeout_missing、resource_leak、sql_injection、"
                        "error_handling、unsafe_eval、security。"
                        "不得新增输入中不存在的文件路径或行号。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"目标 schema：{json.dumps(output_model.model_json_schema(), ensure_ascii=False)}\n"
                        f"校验错误：{_safe_error(exc)}\n"
                        f"待修复输出：\n{raw}"
                    ),
                },
            ]
            repaired = self._chat(repair_messages)
            try:
                return _validate_output(repaired, output_model)
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as repair_exc:
                self.validation_error_details.extend(
                    _exception_details(repair_exc, "schema_repair")
                )
                raise ValueError(
                    f"模型在一次 schema repair 后仍未返回有效结构: {_safe_error(repair_exc)}"
                ) from repair_exc

    def _chat(self, messages: list[dict[str, str]]) -> str:
        payload = json.dumps(
            {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(self._chat_completions_url(), data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, socket.timeout) as exc:
            raise TimeoutError(f"OpenAI-compatible 请求超过 {self.timeout_seconds}s") from exc
        except error.HTTPError as exc:
            raise RuntimeError(f"OpenAI-compatible API 返回 HTTP {exc.code}") from exc
        except error.URLError as exc:
            reason = self._redact(str(exc.reason))
            raise RuntimeError(f"OpenAI-compatible API 连接失败: {reason}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError("OpenAI-compatible API 返回了无法解析的响应") from exc

        usage = response_payload.get("usage") or {}
        self.input_tokens = (self.input_tokens or 0) + int(usage.get("prompt_tokens") or 0)
        self.output_tokens = (self.output_tokens or 0) + int(usage.get("completion_tokens") or 0)
        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenAI-compatible API 响应缺少 choices[0].message.content") from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenAI-compatible API 返回了空内容")
        return content

    def _chat_completions_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _redact(self, value: str) -> str:
        if self.api_key:
            return value.replace(self.api_key, "<redacted>")
        return value


def _system_prompt(task: str) -> str:
    return (
        "你是 DevQuality 代码审查 Agent。"
        f"{task}。只输出单个 JSON 对象，禁止 Markdown fence，禁止额外解释。"
        "只审查 Git Diff 中可映射的新行；file_path 和 line_number 必须来自 diff。"
        "severity 只能是 low、medium、high、critical，confidence 必须在 0 到 1。"
        "category 只能是 timeout_missing、resource_leak、sql_injection、error_handling、"
        "unsafe_eval、security。"
        "evidence 必须非空并引用具体新增代码。source 填写 openai_compatible。"
        "展示字段必须使用简体中文：finding.title 和 finding.suggestion 使用中文；"
        "test_suggestion.test_name 使用简短中文标题；test_suggestion.description 使用中文编号步骤。"
        "结构字段 category、severity、source、finding_index、file_path 保持英文枚举或原始路径。"
        "静态规则提示只是线索，不是必须照抄的结论。"
    )


def _review_prompt(review_request: ReviewRequest, static_hints: list[StaticHint]) -> str:
    hints = json.dumps([hint.model_dump() for hint in static_hints], ensure_ascii=False, indent=2)
    return (
        f"语言：{review_request.language}\n"
        f"prompt_version：{review_request.prompt_version}\n"
        f"allowed_locations：{json.dumps(_allowed_locations(review_request), ensure_ascii=False)}\n"
        f"static_hints：\n{hints}\n"
        f"Git Diff：\n{review_request.diff}"
    )


def _allowed_locations(review_request: ReviewRequest) -> dict[str, list[int]]:
    parsed = parse_unified_diff(review_request.diff)
    return {
        file.new_path: sorted(parsed.mapped_new_lines(file.new_path))
        for file in parsed.files
        if file.new_path != "/dev/null"
    }


def _validate_output(raw: str, output_model: type[OutputModel]) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    payload: Any = json.loads(cleaned)
    validated = output_model.model_validate(payload)
    return validated.model_dump_json()


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors()
        )
    return str(exc)[:500]


def _exception_details(exc: Exception, stage: str) -> list[dict[str, str]]:
    if isinstance(exc, ValidationError):
        return [
            {
                "stage": stage,
                "field": ".".join(str(part) for part in item["loc"]) or "$",
                "expected": _expected_from_error(item),
                "reason": item["msg"],
            }
            for item in exc.errors(include_input=False)
        ]
    if isinstance(exc, json.JSONDecodeError):
        return [
            {
                "stage": stage,
                "field": "$",
                "expected": "符合给定 schema 的 JSON 对象",
                "reason": f"JSON 解析失败：{exc.msg}（位置 {exc.pos}）",
            }
        ]
    return [
        {
            "stage": stage,
            "field": "$",
            "expected": "符合给定 schema 的 JSON 对象",
            "reason": str(exc)[:300],
        }
    ]


def _expected_from_error(item: dict[str, Any]) -> str:
    error_type = item.get("type", "")
    if error_type == "literal_error":
        return "允许的枚举值"
    if error_type.startswith("int"):
        return "整数"
    if error_type.startswith("float"):
        return "数字"
    if error_type.startswith("string"):
        return "字符串"
    if error_type.startswith("list"):
        return "数组"
    return "符合 JSON Schema 的字段类型或枚举"
