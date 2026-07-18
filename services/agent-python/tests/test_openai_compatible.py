from __future__ import annotations

import json
import os
from copy import deepcopy
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agent_service.agents.single_agent import run_single_agent
from agent_service.agents.dual_agent import run_dual_agent
from agent_service.schemas import LLMConfig, ReviewRequest
from agent_service.llm.factory import create_llm_client
from agent_service.server import load_environment


DIFF = """diff --git a/main.go b/main.go
--- a/main.go
+++ b/main.go
@@ -1,1 +1,2 @@
 package main
+resp, err := http.Get(url)
"""


VALID_OUTPUT = {
    "findings": [
        {
            "file_path": "main.go",
            "line_number": 2,
            "severity": "medium",
            "category": "timeout_missing",
            "title": "HTTP 请求缺少超时",
            "evidence": "resp, err := http.Get(url)",
            "suggestion": "使用配置了 Timeout 的 http.Client。",
            "confidence": 0.93,
            "source": "openai_compatible",
        }
    ],
    "test_suggestions": [
        {
            "finding_index": 0,
            "target_file": "main.go",
            "test_name": "TestHTTPClientTimeout",
            "description": "模拟服务端阻塞并验证请求按超时返回。",
            "code": None,
        }
    ],
}


class _ProviderHandler(BaseHTTPRequestHandler):
    responses: list[str] = []
    requests: list[dict] = []
    authorizations: list[str | None] = []

    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        self.__class__.requests.append(json.loads(raw.decode("utf-8")))
        self.__class__.authorizations.append(self.headers.get("Authorization"))
        content = self.__class__.responses.pop(0)
        payload = {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 17, "completion_tokens": 11},
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def test_openai_compatible_single_agent_records_provider_without_api_key() -> None:
    server, thread = _start_provider([json.dumps(VALID_OUTPUT, ensure_ascii=False)])
    api_key = "test-secret-key-not-for-output"
    try:
        response = run_single_agent(_request(server.server_port, api_key))
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert not response.validation_errors
    assert len(response.findings) == 1
    assert len(response.test_suggestions) == 1
    assert response.agent_runs[0].provider == "openai_compatible"
    assert response.agent_runs[0].model == "local-test-model"
    assert response.agent_runs[0].input_tokens == 17
    assert response.agent_runs[0].output_tokens == 11
    assert _ProviderHandler.authorizations == [f"Bearer {api_key}"]
    assert api_key not in response.model_dump_json()
    assert api_key not in response.report_markdown
    system_prompt = _ProviderHandler.requests[0]["messages"][0]["content"]
    assert "finding.title" in system_prompt
    assert "简体中文" in system_prompt
    assert "category 只能是" in system_prompt


def test_openai_compatible_retries_once_for_schema_repair() -> None:
    server, thread = _start_provider(
        ["not-json", json.dumps(VALID_OUTPUT, ensure_ascii=False)]
    )
    try:
        response = run_single_agent(_request(server.server_port, "repair-secret"))
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert not response.validation_errors
    assert len(_ProviderHandler.requests) == 2
    repair_message = _ProviderHandler.requests[1]["messages"][0]["content"]
    assert "schema repair" in repair_message
    assert "禁止 Markdown fence" in repair_message
    assert "禁止解释文字" in repair_message
    assert "finding_index 必须指向" in repair_message
    assert "severity 只能使用" in repair_message
    assert "category 只能使用" in repair_message
    assert response.agent_runs[0].input_tokens == 34
    assert response.agent_runs[0].output_tokens == 22


def test_openai_compatible_dual_agent_tokens_are_scoped_per_stage() -> None:
    encoded = json.dumps(VALID_OUTPUT, ensure_ascii=False)
    server, thread = _start_provider([encoded, encoded])
    try:
        response = run_dual_agent(_request(server.server_port, "dual-stage-secret"))
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert not response.validation_errors
    assert [run.input_tokens for run in response.agent_runs] == [17, 17]
    assert [run.output_tokens for run in response.agent_runs] == [11, 11]


def test_openai_compatible_uses_environment_configuration(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_BASE", "http://127.0.0.1:18081/v1")
    monkeypatch.setenv("LLM_API_KEY", "environment-secret")
    monkeypatch.setenv("LLM_MODEL", "environment-model")

    client = create_llm_client(ReviewRequest(diff=DIFF, language="go", mode="real"))

    assert client.provider_name == "openai_compatible"
    assert client.model_name == "environment-model"


def test_request_configuration_does_not_mix_with_environment(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_BASE", "http://environment.invalid/v1")
    monkeypatch.setenv("LLM_API_KEY", "environment-secret")
    monkeypatch.setenv("LLM_MODEL", "environment-model")

    client = create_llm_client(
        ReviewRequest(
            diff=DIFF,
            language="go",
            mode="real",
            llm_config=LLMConfig(
                base_url="http://request.invalid/v1",
                api_key="request-secret",
                model="request-model",
                timeout_seconds=7,
            ),
        )
    )

    assert client.base_url == "http://request.invalid/v1"
    assert client.api_key == "request-secret"
    assert client.model_name == "request-model"
    assert client.timeout_seconds == 7


def test_agent_service_loads_local_env_without_overriding_process_env(
    monkeypatch, tmp_path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_PROVIDER=openai_compatible\n"
        "LLM_API_BASE=http://dotenv.invalid/v1\n"
        "LLM_API_KEY=dotenv-secret\n"
        "LLM_MODEL=dotenv-model\n",
        encoding="utf-8",
    )
    for key in ("LLM_PROVIDER", "LLM_API_BASE", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("LLM_MODEL", "process-model")

    load_environment(env_file)

    assert os.environ["LLM_API_BASE"] == "http://dotenv.invalid/v1"
    assert os.environ["LLM_API_KEY"] == "dotenv-secret"
    assert os.environ["LLM_MODEL"] == "process-model"


def test_missing_real_configuration_returns_structured_agent_run(monkeypatch) -> None:
    for key in ("LLM_PROVIDER", "LLM_API_BASE", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)

    response = run_dual_agent(ReviewRequest(diff=DIFF, language="go", mode="real"))

    assert response.validation_errors
    assert response.validation_errors == ["real LLM config missing"]
    assert response.agent_runs[0].status == "failed"
    assert response.agent_runs[0].provider == "openai_compatible"


def test_deterministic_validation_failure_returns_sanitized_debug_info() -> None:
    invalid_line = deepcopy(VALID_OUTPUT)
    invalid_line["findings"][0]["line_number"] = 999
    invalid_payload = json.dumps(invalid_line, ensure_ascii=False)
    server, thread = _start_provider([invalid_payload, invalid_payload])
    try:
        response = run_dual_agent(_request(server.server_port, "debug-secret"))
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response.validation_errors
    assert response.debug_info is not None
    assert response.debug_info.repair_attempted is True
    assert response.debug_info.validation_errors[0].stage == "deterministic_validator"
    assert response.debug_info.validation_errors[0].field == "findings[0].line_number"
    assert response.debug_info.validation_errors[-1].stage == "post_repair_validator"
    assert "debug-secret" not in response.model_dump_json()


def test_deterministic_validation_repair_can_fix_invalid_location() -> None:
    invalid_line = deepcopy(VALID_OUTPUT)
    invalid_line["findings"][0]["line_number"] = 999
    server, thread = _start_provider(
        [
            json.dumps(invalid_line, ensure_ascii=False),
            json.dumps({"findings": VALID_OUTPUT["findings"]}, ensure_ascii=False),
            json.dumps({"test_suggestions": VALID_OUTPUT["test_suggestions"]}, ensure_ascii=False),
        ]
    )
    try:
        response = run_dual_agent(_request(server.server_port, "location-repair-secret"))
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert not response.validation_errors
    assert response.findings[0].line_number == 2
    assert [run.agent_name for run in response.agent_runs] == [
        "review_agent",
        "review_repair",
        "test_agent",
    ]


def test_failed_schema_repair_reports_both_output_stages() -> None:
    server, thread = _start_provider(["not-json", "still-not-json"])
    try:
        response = run_single_agent(_request(server.server_port, "repair-failure-secret"))
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert response.validation_errors
    assert response.debug_info is not None
    assert response.debug_info.repair_attempted is True
    assert [item.stage for item in response.debug_info.validation_errors] == [
        "first_output",
        "schema_repair",
    ]
    assert "repair-failure-secret" not in response.model_dump_json()


def _request(port: int, api_key: str) -> ReviewRequest:
    return ReviewRequest(
        diff=DIFF,
        language="go",
        mode="real",
        llm_config=LLMConfig(
            base_url=f"http://127.0.0.1:{port}/v1",
            api_key=api_key,
            model="local-test-model",
            timeout_seconds=5,
        ),
    )


def _start_provider(responses: list[str]) -> tuple[ThreadingHTTPServer, threading.Thread]:
    _ProviderHandler.responses = responses.copy()
    _ProviderHandler.requests = []
    _ProviderHandler.authorizations = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
