from agent_service.schemas import Finding, ReviewResponse, TestSuggestion
from agent_service.tools.diff_parser import parse_unified_diff
from agent_service.validator import validate_response


DIFF = """diff --git a/app/client.py b/app/client.py
--- a/app/client.py
+++ b/app/client.py
@@ -1,3 +1,4 @@
 import requests
+response = requests.get(url)
"""


def _valid_finding(**overrides):
    data = {
        "file_path": "app/client.py",
        "line_number": 2,
        "severity": "medium",
        "category": "timeout_missing",
        "title": "Missing timeout",
        "evidence": "response = requests.get(url)",
        "suggestion": "Add timeout",
        "confidence": 0.8,
        "source": "test",
    }
    data.update(overrides)
    return Finding(**data)


def test_validator_rejects_illegal_file_path():
    parsed = parse_unified_diff(DIFF)
    response = ReviewResponse(findings=[_valid_finding(file_path="missing.py")])

    result = validate_response(response, parsed)

    assert not result.valid
    assert any("file_path" in error for error in result.errors)


def test_validator_rejects_illegal_severity():
    parsed = parse_unified_diff(DIFF)
    response = ReviewResponse(findings=[_valid_finding(severity="urgent")])

    result = validate_response(response, parsed)

    assert not result.valid
    assert any("severity" in error for error in result.errors)


def test_validator_rejects_out_of_range_finding_index():
    parsed = parse_unified_diff(DIFF)
    response = ReviewResponse(
        findings=[_valid_finding()],
        test_suggestions=[
            TestSuggestion(
                finding_index=3,
                target_file="app/client.py",
                test_name="test_timeout",
                description="covers timeout",
            )
        ],
    )

    result = validate_response(response, parsed)

    assert not result.valid
    assert any("finding_index" in error for error in result.errors)

