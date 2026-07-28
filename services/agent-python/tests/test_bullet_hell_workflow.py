import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.server import create_unified_app
from gameconfig_agent.bullet_hell import simulate_telemetry
from workflow.bullet_hell_workflow import BulletHellWorkflowService


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _service(tmp_path: Path, runner=None) -> BulletHellWorkflowService:
    return BulletHellWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=tmp_path / "bullet-workflows",
        unity_executable=tmp_path / "BulletHellDemo.exe",
        telemetry_runner=runner or (lambda config, _directory, seed: simulate_telemetry(config, seed=seed)),
    )


def _requirement() -> str:
    return "第二阶段改为双向螺旋弹，提高密度，但同时存在的子弹不能超过350发，最低帧率不能低于55 FPS。"


def _wait(service: BulletHellWorkflowService, workflow_id: str) -> dict:
    for _ in range(100):
        value = service.get(workflow_id)
        if value["status"] in {"evidence_ready", "budget_exhausted", "blocked", "failed"}:
            return value
        time.sleep(0.01)
    raise AssertionError("workflow did not finish")


def test_create_requires_authorization_and_never_changes_baseline(tmp_path):
    service = _service(tmp_path)
    baseline_before = service.baseline_path.read_bytes()

    workflow = service.create(requirement_text=_requirement())

    assert workflow["status"] == "awaiting_authorization"
    assert workflow["static_validation"]["passed"]
    assert workflow["config_diff"]
    assert workflow["structured_goal"]["target_phase_id"] == "phase_2"
    assert service.latest()["workflow_id"] == workflow["workflow_id"]
    with pytest.raises(ValueError, match="cannot run"):
        service.start(workflow["workflow_id"])
    assert service.baseline_path.read_bytes() == baseline_before


def test_authorized_workflow_runs_paired_evidence_and_can_be_accepted(tmp_path):
    service = _service(tmp_path)
    created = service.create(requirement_text=_requirement())
    workflow_id = created["workflow_id"]

    service.authorize(workflow_id, actor="designer", note="允许最多三轮隔离测试")
    service.start(workflow_id)
    completed = _wait(service, workflow_id)
    accepted = service.decide(
        workflow_id,
        decision="accept",
        actor="designer",
        note="固定轨迹证据达到当前目标",
    )

    assert completed["status"] == "evidence_ready"
    assert completed["baseline_telemetry"]
    assert completed["candidate_telemetry"]
    assert completed["comparison_report"]["passed"]
    assert accepted["status"] == "accepted"
    assert accepted["final_decision"]["baseline_overwritten"] is False


def test_failed_first_candidate_uses_bounded_repair(tmp_path):
    calls = {"candidate": 0}

    def runner(config, directory, seed):
        telemetry = simulate_telemetry(config, seed=seed)
        if directory.name.startswith("candidate"):
            calls["candidate"] += 1
            if calls["candidate"] == 1:
                telemetry["peak_alive_bullets"] = 420
        return telemetry

    service = _service(tmp_path, runner)
    created = service.create(requirement_text=_requirement())
    service.authorize(created["workflow_id"], actor="designer")
    service.start(created["workflow_id"])
    completed = _wait(service, created["workflow_id"])

    assert completed["status"] == "evidence_ready"
    assert completed["budget"]["unity_runs_used"] == 2
    assert completed["repair_history"][0]["action"] == "REDUCE_BULLETS_PER_WAVE"
    assert completed["candidate_history"][-1]["evaluation"]["passed"]


def test_dangerous_request_is_blocked_without_runner(tmp_path):
    called = False

    def runner(_config, _directory, _seed):
        nonlocal called
        called = True
        return {}

    service = _service(tmp_path, runner)
    workflow = service.create(requirement_text="每0.02秒发射200颗高速弹，越密越好。")

    assert workflow["status"] == "blocked"
    assert not called
    with pytest.raises(ValueError, match="cannot be authorized"):
        service.authorize(workflow["workflow_id"], actor="designer")


def test_api_exposes_bullet_hell_workflow(tmp_path):
    service = _service(tmp_path)
    client = TestClient(create_unified_app(bullet_hell_workflow_service=service))

    capabilities = client.get("/api/bullet-hell/capabilities")
    created = client.post(
        "/api/bullet-hell/workflows",
        json={"requirement_text": _requirement(), "provider": "mock"},
    )

    assert capabilities.status_code == 200
    assert capabilities.json()["patterns"] == ["ring", "aimed_fan", "spiral", "petal"]
    assert created.status_code == 200
    workflow_id = created.json()["workflow_id"]
    blocked = client.post(f"/api/bullet-hell/workflows/{workflow_id}/run")
    assert blocked.status_code == 409
    authorized = client.post(
        f"/api/bullet-hell/workflows/{workflow_id}/authorize",
        json={"actor": "designer", "note": "隔离运行"},
    )
    assert authorized.status_code == 200


def test_gameplay_failure_exit_code_keeps_valid_telemetry(tmp_path, monkeypatch):
    executable = tmp_path / "BulletHellDemo.exe"
    executable.write_bytes(b"placeholder")
    service = BulletHellWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=tmp_path / "workflows",
        unity_executable=executable,
    )

    def fake_run(command, **_kwargs):
        telemetry_path = Path(command[command.index("--telemetry-output") + 1])
        telemetry_path.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "random_seed": 20260727,
                    "player_hits": 5,
                    "phase_results": [],
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr("workflow.bullet_hell_workflow.subprocess.run", fake_run)
    baseline = json.loads(
        (REPOSITORY_ROOT / "configs" / "bullet-hell" / "baseline.json").read_text(encoding="utf-8")
    )
    telemetry = service._run_unity(baseline, tmp_path / "run", 20260727)

    assert telemetry["status"] == "failed"
    assert telemetry["player_hits"] == 5
