from __future__ import annotations

import json
import time

from agent_service.llm.base import LLMClient
from agent_service.schemas import ReviewRequest, StaticHint


class MockLLM(LLMClient):
    provider_name = "mock"
    model_name = "deterministic-mock-v1"
    output_label = "mock llm"

    def generate(self, request: ReviewRequest, static_hints: list[StaticHint]) -> str:
        if request.mock_latency_ms > 0:
            time.sleep(request.mock_latency_ms / 1000)

        if request.mock_case == "timeout":
            raise TimeoutError("mock llm timeout")
        if request.mock_case == "invalid_json":
            return "{invalid json"

        findings = [_finding_from_hint(hint) for hint in static_hints]
        test_suggestions = [
            _test_suggestion_from_finding(index, finding) for index, finding in enumerate(findings)
        ]
        return json.dumps(
            {"findings": findings, "test_suggestions": test_suggestions},
            ensure_ascii=False,
        )

    def generate_findings(self, request: ReviewRequest, static_hints: list[StaticHint]) -> str:
        if request.mock_latency_ms > 0:
            time.sleep(request.mock_latency_ms / 1000)

        if request.mock_case == "timeout":
            raise TimeoutError("mock review agent timeout")
        if request.mock_case == "invalid_json":
            return "{invalid json"

        findings = [_finding_from_hint(hint) for hint in static_hints]
        return json.dumps({"findings": findings}, ensure_ascii=False)

    def generate_tests(self, request: ReviewRequest, findings: list[dict]) -> str:
        if request.mock_latency_ms > 0:
            time.sleep(request.mock_latency_ms / 1000)

        if request.mock_case == "timeout":
            raise TimeoutError("mock test agent timeout")
        if request.mock_case == "invalid_json":
            return "{invalid json"

        test_suggestions = [
            _test_suggestion_from_finding(index, finding) for index, finding in enumerate(findings)
        ]
        return json.dumps({"test_suggestions": test_suggestions}, ensure_ascii=False)


def _finding_from_hint(hint: StaticHint) -> dict:
    title_by_category = {
        "timeout_missing": "调用缺少显式超时",
        "resource_leak": "资源可能未释放",
        "error_handling": "错误处理不完整",
        "sql_injection": "SQL 查询使用动态字符串构造",
        "security": "引入了动态代码执行",
        "performance": "引入了每帧性能风险",
        "determinism": "破坏了固定种子可重复性",
    }
    suggestion_by_category = {
        "timeout_missing": "使用带显式超时的客户端或调用参数，并覆盖超时行为。",
        "resource_leak": "在所有成功路径关闭资源，并增加回归测试。",
        "error_handling": "显式检查错误，并返回或处理该错误。",
        "sql_injection": "使用参数化查询，不要拼接或格式化 SQL 字符串。",
        "security": "避免 eval/exec，改用显式解析或分发逻辑。",
        "performance": "把 I/O、全局查找和对象创建移出每帧回调，并缓存依赖。",
        "determinism": "使用工作流传入的固定种子和确定性随机源，并增加双跑一致性测试。",
    }
    severity_by_category = {
        "timeout_missing": "medium",
        "resource_leak": "high",
        "error_handling": "medium",
        "sql_injection": "high",
        "security": "critical",
        "performance": "high",
        "determinism": "high",
    }
    return {
        "file_path": hint.file_path,
        "line_number": hint.line_number,
        "severity": severity_by_category.get(hint.category, "medium"),
        "category": hint.category,
        "title": title_by_category.get(hint.category, hint.message),
        "evidence": hint.evidence_line,
        "suggestion": suggestion_by_category.get(hint.category, hint.message),
        "confidence": hint.confidence,
        "source": f"mock_llm:{hint.rule_id}",
    }


def _test_suggestion_from_finding(index: int, finding: dict) -> dict:
    safe_name = "".join(part.capitalize() for part in finding["category"].split("_"))
    return {
        "finding_index": index,
        "target_file": finding["file_path"],
        "test_name": f"Test{safe_name}Regression",
        "description": (
            f"覆盖 {finding['file_path']}:{finding['line_number']} 的 "
            f"{finding['category']} 风险，并断言失败路径得到正确处理。"
        ),
        "code": None,
    }
