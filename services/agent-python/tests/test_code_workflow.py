import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.server import create_unified_app
from workflow.code_workflow import CodeWorkflowService


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SAFE_PATCH = REPOSITORY_ROOT / "examples" / "csharp" / "runtime_args_null_guard.patch"
UNSAFE_PATCH = REPOSITORY_ROOT / "examples" / "csharp" / "unsafe_process_launch.patch"
TARGET = REPOSITORY_ROOT / "game-unity" / "Assets" / "Scripts" / "RuntimeRunSettings.cs"


def _service(tmp_path: Path, *, validation_passed: bool = True) -> CodeWorkflowService:
    def launcher(workflow_dir: Path, _workspace_root: Path) -> int:
        (workflow_dir / "validation_result.json").write_text(
            json.dumps(
                {
                    "passed": validation_passed,
                    "compilation_passed": validation_passed,
                    "editor_smoke_passed": validation_passed,
                    "player_runs_passed": validation_passed,
                    "repeatability_passed": validation_passed,
                    "repeatability_rate": 1.0 if validation_passed else 0.0,
                    "runtime_target_pass_rate": 0.8,
                    "error": None if validation_passed else {"type": "BuildError", "message": "failed"},
                }
            ),
            encoding="utf-8",
        )
        return 4321

    return CodeWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=tmp_path / "code_workflows",
        validation_launcher=launcher,
    )


def _create(service: CodeWorkflowService, patch: Path = SAFE_PATCH):
    return service.create(
        title="运行参数空值保护",
        change_reason="为运行参数解析增加明确失败路径，不改变玩法。",
        diff_text=patch.read_text(encoding="utf-8"),
    )


def test_safe_patch_requires_approval_before_isolated_apply(tmp_path: Path):
    service = _service(tmp_path)
    proposal = _create(service)

    assert proposal["status"] == "proposed"
    assert proposal["patch_safety_gate"]["passed"] is True
    assert proposal["quality_review"]["validation_errors"] == []
    with pytest.raises(ValueError, match="Workspace cannot be prepared"):
        service.prepare_workspace(proposal["workflow_id"])


def test_unsafe_patch_is_rejected_before_quality_review(tmp_path: Path):
    service = _service(tmp_path)

    proposal = _create(service, UNSAFE_PATCH)

    assert proposal["status"] == "rejected"
    assert "process_launch" in {
        item["rule_id"] for item in proposal["patch_safety_gate"]["errors"]
    }
    assert proposal["quality_review"] is None


def test_approved_patch_is_applied_only_in_isolated_workspace(tmp_path: Path):
    service = _service(tmp_path)
    baseline_hash = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    proposal = _create(service)
    service.approve(proposal["workflow_id"], approver="developer", note="进入隔离验证")

    prepared = service.prepare_workspace(proposal["workflow_id"])

    assert prepared["status"] == "workspace_prepared"
    assert prepared["isolated_apply"]["baseline_unchanged"] is True
    workspace_target = (
        tmp_path
        / "code_workflows"
        / proposal["workflow_id"]
        / "workspace"
        / TARGET.relative_to(REPOSITORY_ROOT)
    )
    assert "ArgumentNullException" in workspace_target.read_text(encoding="utf-8")
    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == baseline_hash


def test_validation_evidence_can_be_accepted_without_applying_to_repository(tmp_path: Path):
    service = _service(tmp_path)
    proposal = _create(service)
    service.approve(proposal["workflow_id"], approver="developer")
    service.prepare_workspace(proposal["workflow_id"])

    ready = service.start_validation(proposal["workflow_id"])
    accepted = service.decide(
        proposal["workflow_id"],
        decision="accept",
        actor="lead_developer",
        note="编译、确定性 smoke 和自动试玩证据通过，允许后续人工合并。",
    )

    assert ready["status"] == "evidence_ready"
    assert ready["validation_result"]["repeatability_rate"] == 1.0
    assert accepted["status"] == "accepted"
    assert accepted["final_decision"]["patch_applied_to_repository"] is False


def test_failed_unity_validation_keeps_failure_evidence(tmp_path: Path):
    service = _service(tmp_path, validation_passed=False)
    proposal = _create(service)
    service.approve(proposal["workflow_id"], approver="developer")
    service.prepare_workspace(proposal["workflow_id"])

    failed = service.start_validation(proposal["workflow_id"])

    assert failed["status"] == "failed"
    assert failed["error"]["type"] == "BuildError"


def test_code_workflow_api_enforces_human_gate(tmp_path: Path):
    service = _service(tmp_path)
    client = TestClient(create_unified_app(code_workflow_service=service))

    response = client.post(
        "/api/code-workflows",
        json={
            "title": "运行参数空值保护",
            "change_reason": "避免非法调用静默失败。",
            "diff_text": SAFE_PATCH.read_text(encoding="utf-8"),
            "provider": "mock",
        },
    )
    assert response.status_code == 200
    workflow_id = response.json()["workflow_id"]

    blocked = client.post(f"/api/code-workflows/{workflow_id}/workspace")
    assert blocked.status_code == 409

    approved = client.post(
        f"/api/code-workflows/{workflow_id}/approve",
        json={"approver": "developer", "note": "进入隔离验证"},
    )
    assert approved.status_code == 200
    prepared = client.post(f"/api/code-workflows/{workflow_id}/workspace")
    assert prepared.status_code == 200
    assert prepared.json()["status"] == "workspace_prepared"


def test_exited_validation_process_without_result_becomes_failed(tmp_path: Path):
    service = CodeWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=tmp_path / "code_workflows",
        validation_launcher=lambda _workflow_dir, _workspace_root: 99999,
        process_checker=lambda _process_id: False,
    )
    proposal = _create(service)
    service.approve(proposal["workflow_id"], approver="developer")
    service.prepare_workspace(proposal["workflow_id"])

    failed = service.start_validation(proposal["workflow_id"])

    assert failed["status"] == "failed"
    assert failed["error"]["type"] == "ValidationProcessError"


def test_powershell_bom_validation_result_is_read(tmp_path: Path):
    service = _service(tmp_path)
    proposal = _create(service)
    service.approve(proposal["workflow_id"], approver="developer")
    service.prepare_workspace(proposal["workflow_id"])
    workflow_dir = tmp_path / "code_workflows" / proposal["workflow_id"]
    payload = {
        "passed": True,
        "compilation_passed": True,
        "editor_smoke_passed": True,
        "player_runs_passed": True,
        "repeatability_passed": True,
        "repeatability_rate": 1.0,
        "runtime_target_pass_rate": 0.6,
        "error": None,
    }
    (workflow_dir / "validation_result.json").write_text(
        json.dumps(payload),
        encoding="utf-8-sig",
    )
    manifest_path = workflow_dir / "code_workflow_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "validation_running"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    ready = service.get(proposal["workflow_id"])

    assert ready["status"] == "evidence_ready"
    assert ready["validation_result"]["runtime_target_pass_rate"] == 0.6
