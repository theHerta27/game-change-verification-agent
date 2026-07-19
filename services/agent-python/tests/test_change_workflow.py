import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.server import create_unified_app
from gameconfig_agent.runtime_runs import RuntimeRunService
from workflow.change_workflow import ChangeWorkflowService
from workflow.config_change import run_feasibility_gate


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BASELINE_CONTRACT = REPOSITORY_ROOT / "game-unity" / "Assets" / "StreamingAssets" / "game_config.json"


def _services(tmp_path: Path):
    executable = tmp_path / "GameConfigRuntimeDemo.exe"
    executable.write_bytes(b"fixture")
    (tmp_path / "guided_runtime_version.txt").write_text("guided-runtime-v1", encoding="utf-8")
    launches = []

    def launcher(command, cwd):
        launches.append((command, cwd))
        return 2468

    runtime = RuntimeRunService(
        project_root=REPOSITORY_ROOT,
        runs_dir=tmp_path / "runtime_runs",
        unity_executable=executable,
        launcher=launcher,
        process_checker=lambda _process_id: True,
    )
    workflow = ChangeWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=tmp_path / "change_workflows",
        runtime_runs=runtime,
    )
    return workflow, runtime, launches


def _requirement() -> str:
    return "将新手试炼武器基础攻击力改为 45，通关目标 60-90 秒，击败 5 个敌人，技能至少使用 1 次。"


def test_feasibility_gate_rejects_off_topic_and_out_of_range():
    off_topic = run_feasibility_gate("帮我设计一个精美角色并讲个笑话")
    out_of_range = run_feasibility_gate("将新手试炼武器基础攻击力改为 999")

    assert off_topic["decision"] == "rejected"
    assert out_of_range["decision"] == "rejected"
    assert out_of_range["out_of_range"][0]["target_field"] == "weapon_config.base_attack"


def test_create_proposal_maps_constraints_and_generates_diff(tmp_path):
    workflow, _, _ = _services(tmp_path)

    proposal = workflow.create(requirement_text=_requirement())

    assert proposal["status"] == "proposed"
    assert proposal["static_validation"]["passed"] is True
    assert proposal["quality_review"]["approval_recommended"] is True
    paths = {change["path"] for change in proposal["config_diff"]}
    assert "weapon_config[0].base_attack" in paths
    assert "runtime_target_config[0].completion_time_seconds_min" in paths
    assert "runtime_target_config[0].completion_time_seconds_max" in paths
    assert proposal["change_count"] == len(proposal["config_diff"])


def test_runtime_requires_approval_and_uses_isolated_snapshot(tmp_path):
    workflow, runtime, _ = _services(tmp_path)
    before_hash = hashlib.sha256(BASELINE_CONTRACT.read_bytes()).hexdigest()
    proposal = workflow.create(requirement_text=_requirement())

    with pytest.raises(ValueError, match="Runtime cannot be prepared"):
        workflow.prepare_runtime(proposal["workflow_id"])

    approved = workflow.approve(proposal["workflow_id"], approver="designer", note="进入固定种子验证")
    prepared = workflow.prepare_runtime(approved["workflow_id"])

    assert prepared["status"] == "runtime_prepared"
    assert prepared["approval"]["approver"] == "designer"
    run = prepared["runtime_run"]
    assert run["provider"] == "workflow_snapshot"
    assert run["source_provider"] == "mock"
    assert run["source_workflow_id"] == proposal["workflow_id"]
    assert (runtime.runs_dir / run["run_id"] / "final_configs.json").is_file()
    assert hashlib.sha256(BASELINE_CONTRACT.read_bytes()).hexdigest() == before_hash


def test_completed_runtime_evidence_can_be_accepted(tmp_path):
    workflow, runtime, launches = _services(tmp_path)
    proposal = workflow.create(requirement_text=_requirement())
    workflow.approve(proposal["workflow_id"], approver="designer")
    workflow.prepare_runtime(proposal["workflow_id"])
    launched = workflow.launch_runtime(proposal["workflow_id"], mode="manual")
    run_id = launched["runtime_run_id"]
    run_dir = runtime.runs_dir / run_id
    (run_dir / "telemetry.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completion_time_seconds": 65.0,
                "enemies_defeated": 5,
                "skill_uses": 1,
                "gold_earned": 300,
            }
        ),
        encoding="utf-8",
    )

    evidence_ready = workflow.get(proposal["workflow_id"])
    accepted = workflow.decide(
        proposal["workflow_id"],
        decision="accept",
        actor="lead_designer",
        note="运行证据符合当前验收结论",
    )

    assert launches
    assert evidence_ready["status"] == "evidence_ready"
    assert evidence_ready["runtime_evidence_review"]["evidence_complete"] is True
    assert accepted["status"] == "accepted"
    assert accepted["final_decision"]["active_config_hash"] == accepted["candidate_hash"]


def test_approved_candidate_can_be_rolled_back_without_runtime(tmp_path):
    workflow, _, _ = _services(tmp_path)
    proposal = workflow.create(requirement_text=_requirement())
    workflow.approve(proposal["workflow_id"], approver="designer")

    rolled_back = workflow.decide(
        proposal["workflow_id"],
        decision="rollback",
        actor="designer",
        note="取消本次候选，不进入 Unity",
    )

    assert rolled_back["status"] == "rolled_back"
    assert rolled_back["final_decision"]["active_config_hash"] == rolled_back["baseline_hash"]


def test_change_workflow_api_enforces_human_gate(tmp_path):
    workflow, runtime, _ = _services(tmp_path)
    client = TestClient(
        create_unified_app(runtime_run_service=runtime, change_workflow_service=workflow)
    )

    response = client.post(
        "/api/change-workflows",
        json={"requirement_text": _requirement(), "provider": "mock"},
    )
    assert response.status_code == 200
    workflow_id = response.json()["workflow_id"]

    blocked = client.post(f"/api/change-workflows/{workflow_id}/runtime")
    assert blocked.status_code == 409

    approved = client.post(
        f"/api/change-workflows/{workflow_id}/approve",
        json={"approver": "designer", "note": "同意进入验证"},
    )
    assert approved.status_code == 200

    prepared = client.post(f"/api/change-workflows/{workflow_id}/runtime")
    assert prepared.status_code == 200
    assert prepared.json()["status"] == "runtime_prepared"


def test_change_workflow_rejects_unknown_case_and_blank_approver(tmp_path):
    workflow, _, _ = _services(tmp_path)

    with pytest.raises(ValueError, match="Unknown classic case"):
        workflow.create(requirement_text=_requirement(), case_id="case_unknown")

    proposal = workflow.create(requirement_text=_requirement())
    with pytest.raises(ValueError, match="approver must not be blank"):
        workflow.approve(proposal["workflow_id"], approver="   ")
