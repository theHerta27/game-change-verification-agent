from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


FINDING = {
    "file_path": "service/client.go",
    "line_number": 6,
    "severity": "medium",
    "category": "timeout_missing",
    "title": "HTTP 请求缺少显式超时",
    "evidence": "resp, err := http.Get(url)",
    "suggestion": "使用配置了 Timeout 的 http.Client，并覆盖超时路径。",
    "confidence": 0.94,
    "source": "openai_compatible",
}

TEST_SUGGESTION = {
    "finding_index": 0,
    "target_file": "service/client.go",
    "test_name": "请求超时回归测试",
    "description": "1. 启动延迟测试服务器；2. 调用 Fetch；3. 断言请求在期限内返回超时错误。",
    "code": None,
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        payload = self._read_json()
        system_prompt = payload.get("messages", [{}])[0].get("content", "")
        user_prompt = payload.get("messages", [{}, {}])[-1].get("content", "")
        if "只输出 findings" in system_prompt:
            content: dict[str, Any] = {"findings": _findings_for_prompt(user_prompt)}
        elif "finding repair" in system_prompt:
            content = {"findings": _findings_for_prompt(user_prompt)}
        elif "只基于已验证 findings" in system_prompt:
            content = {"test_suggestions": _tests_for_prompt(user_prompt)}
        else:
            findings = _findings_for_prompt(user_prompt)
            content = {"findings": findings, "test_suggestions": _tests_for_findings(findings)}
        response = {
            "choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 80},
        }
        self._write_json(200, response)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _findings_for_prompt(prompt: str) -> list[dict[str, Any]]:
    if "user_repo.py" in prompt:
        return [
            {
                "file_path": "user_repo.py",
                "line_number": 5,
                "severity": "high",
                "category": "sql_injection",
                "title": "动态拼接 SQL 可能导致注入",
                "evidence": "sql = f\"SELECT * FROM users WHERE id = '{user_id}'\"",
                "suggestion": "使用参数化查询，并为恶意 user_id 增加回归测试。",
                "confidence": 0.97,
                "source": "openai_compatible",
            },
            {
                "file_path": "user_repo.py",
                "line_number": 9,
                "severity": "medium",
                "category": "timeout_missing",
                "title": "外部 HTTP 请求缺少超时控制",
                "evidence": "response = requests.get(url)",
                "suggestion": "为 requests.get 设置显式 timeout，并处理超时异常。",
                "confidence": 0.94,
                "source": "openai_compatible",
            },
        ]
    if "integrations/catalog.py" in prompt and "requests.get(url)" in prompt:
        return [
            {
                "file_path": "integrations/catalog.py",
                "line_number": 4,
                "severity": "medium",
                "category": "timeout_missing",
                "title": "外部请求缺少超时控制",
                "evidence": "response = requests.get(url)",
                "suggestion": "为 requests.get 设置显式 timeout，并处理超时异常。",
                "confidence": 0.95,
                "source": "openai_compatible",
            }
        ]
    if "repositories/users.py" in prompt and "sql = f" in prompt:
        return [
            {
                "file_path": "repositories/users.py",
                "line_number": 3,
                "severity": "high",
                "category": "sql_injection",
                "title": "动态拼接 SQL 可能导致注入",
                "evidence": "sql = f\"SELECT * FROM users WHERE id = '{user_id}'\"",
                "suggestion": "使用参数化查询替代字符串插值。",
                "confidence": 0.97,
                "source": "openai_compatible",
            }
        ]
    if "rules/expression.py" in prompt and "eval(expression" in prompt:
        return [
            {
                "file_path": "rules/expression.py",
                "line_number": 2,
                "severity": "high",
                "category": "unsafe_eval",
                "title": "直接执行表达式存在代码执行风险",
                "evidence": "return eval(expression, {}, context)",
                "suggestion": "改用受限表达式解析器并限制允许的操作。",
                "confidence": 0.96,
                "source": "openai_compatible",
            }
        ]
    if "service/profile.go" in prompt and "client.Get(url)" in prompt:
        return [
            {
                "file_path": "service/profile.go",
                "line_number": 6,
                "severity": "medium",
                "category": "resource_leak",
                "title": "HTTP 响应体未关闭",
                "evidence": "resp, err := client.Get(url)",
                "suggestion": "成功获得响应后立即 defer resp.Body.Close()。",
                "confidence": 0.96,
                "source": "openai_compatible",
            }
        ]
    if "http.Get(url)" in prompt:
        return [FINDING]
    return []


def _tests_for_prompt(prompt: str) -> list[dict[str, Any]]:
    return _tests_for_findings(_findings_for_prompt(prompt))


def _tests_for_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions = []
    for index, finding in enumerate(findings):
        suggestions.append(
            {
                "finding_index": index,
                "target_file": finding["file_path"],
                "test_name": f"{finding['title']}回归测试",
                "description": "1. 构造触发风险的输入；2. 执行目标函数；3. 断言风险路径被安全处理。",
                "code": None,
            }
        )
    return suggestions


def main() -> int:
    parser = argparse.ArgumentParser(description="Local OpenAI-compatible fixture for integration tests")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18081)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"fixture listening on http://{args.host}:{args.port}/v1", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
