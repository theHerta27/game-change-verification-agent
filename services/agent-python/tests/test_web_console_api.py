from fastapi.testclient import TestClient

import gameconfig_agent.server as server_module
from gameconfig_agent.providers import MockLLMProvider
from gameconfig_agent.server import create_app
from gameconfig_agent.runtime_runs import RuntimeRunService


def test_root_endpoint_points_to_frontend():
    client = TestClient(create_app())
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["frontend"] == "http://127.0.0.1:5173"
    assert payload["health"] == "/api/health"


def test_favicon_endpoint_is_empty_success():
    client = TestClient(create_app())
    response = client.get("/favicon.ico")

    assert response.status_code == 204


def test_health_endpoint():
    client = TestClient(create_app())
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["backend_version"] == "milestone6-real-code-evaluation"
    assert payload["capabilities"]["real_provider_runtime_handoff"] is True
    assert payload["capabilities"]["change_workflow"] is True
    assert payload["capabilities"]["code_workflow"] is True
    assert payload["capabilities"]["code_change_agent"] is True


def test_classic_cases_endpoint_returns_fixed_registry():
    client = TestClient(create_app())
    response = client.get("/api/classic-cases")

    assert response.status_code == 200
    cases = response.json()["cases"]
    assert [case["case_id"] for case in cases] == [
        "case_01_baseline_trial",
        "case_02_reward_overgrant",
        "case_03_combat_too_fast",
        "case_04_missing_reference",
        "case_05_skill_guidance_balance",
    ]


def test_evaluation_evidence_endpoint_and_unknown_case():
    client = TestClient(create_app())

    response = client.get("/api/evaluation-evidence", params={"case_id": "case_04_missing_reference"})
    assert response.status_code == 200
    assert response.json()["evidence_type"] == "static_validation"
    assert response.json()["telemetry_source"] is None

    missing = client.get("/api/evaluation-evidence", params={"case_id": "case_unknown"})
    assert missing.status_code == 404


def test_demo_endpoint_with_mock_provider():
    client = TestClient(create_app())
    response = client.post(
        "/api/runs/demo",
        json={
            "requirement_text": "设计一个新手武器 Training Sword，基础攻击力 50，可升级 3 次，每级攻击力 +5。升级消耗金币和强化石。该武器作为新手任务奖励发放，只能领取一次。",
            "provider": "mock",
            "timeout_seconds": 30,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_summary"]["final_validation_passed"] is True
    assert payload["workflow_summary"]["test_scenarios"] == 7
    assert payload["phase0"]["final_validation"]["passed"] is True


def test_demo_endpoint_real_provider_runs_only_current_requirement(monkeypatch):
    class OpenAIShapedMockProvider(MockLLMProvider):
        name = "openai_compatible"
        model = "test-model"

    monkeypatch.setattr(server_module, "_provider_for_request", lambda _request: OpenAIShapedMockProvider())
    client = TestClient(create_app())
    response = client.post(
        "/api/runs/demo",
        json={
            "requirement_text": "设计一个新手武器 Training Sword。",
            "provider": "openai_compatible",
            "timeout_seconds": 30,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["real_run"]["metrics"]["sample_count"] == 1
    assert [item["sample_id"] for item in payload["real_run"]["results"]] == ["real_demo_input"]
    assert payload["phase0"] == {}
    assert payload["workflow_summary"]["final_validation_passed"] is True


def test_benchmark_endpoint():
    client = TestClient(create_app())
    response = client.post("/api/runs/benchmark", json={"output": "outputs/phase3"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["benchmark"]["metrics"]["sample_count"] == 10
    assert payload["artifacts"]["phase3"]


def test_guided_runtime_run_api_uses_injected_local_launcher(tmp_path):
    executable = tmp_path / "GameConfigRuntimeDemo.exe"
    executable.write_bytes(b"fixture")
    (tmp_path / "guided_runtime_version.txt").write_text("guided-runtime-v1", encoding="utf-8")
    launches = []

    def launcher(command, cwd):
        launches.append((command, cwd))
        return 7788

    service = RuntimeRunService(
        runs_dir=tmp_path / "runtime_runs",
        unity_executable=executable,
        launcher=launcher,
        process_checker=lambda _process_id: True,
    )
    client = TestClient(create_app(service))
    prepared = client.post(
        "/api/runtime-runs",
        json={
            "case_id": "case_01_baseline_trial",
            "requirement_text": "创建标准 Training Sword 试炼。",
            "provider": "mock",
        },
    )
    assert prepared.status_code == 200
    run_id = prepared.json()["run_id"]

    launched = client.post(f"/api/runtime-runs/{run_id}/launch", json={"mode": "manual"})
    assert launched.status_code == 200
    assert launched.json()["status"] == "launched"
    assert launched.json()["process_id"] == 7788
    assert len(launches) == 1

    status = client.get(f"/api/runtime-runs/{run_id}")
    assert status.status_code == 200
    assert status.json()["run_id"] == run_id


def test_guided_runtime_run_api_rejects_static_only_case(tmp_path):
    service = RuntimeRunService(runs_dir=tmp_path / "runtime_runs")
    client = TestClient(create_app(service))

    response = client.post(
        "/api/runtime-runs",
        json={
            "case_id": "case_04_missing_reference",
            "requirement_text": "检查 Trial Medal 引用。",
            "provider": "mock",
        },
    )

    assert response.status_code == 400
    assert "static validation" in response.json()["detail"]
