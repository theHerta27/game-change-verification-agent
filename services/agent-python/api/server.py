"""Single FastAPI entry point for the unified Agent capabilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from agent_service.agents.dual_agent import run_dual_agent
from agent_service.agents.single_agent import run_single_agent
from agent_service.schemas import ReviewRequest, ReviewResponse
from gameconfig_agent.runtime_runs import RuntimeRunService
from gameconfig_agent.server import create_app
from workflow import BulletHellWorkflowService, ChangeWorkflowService, CodeWorkflowService, CodeChangeAgentService
from workflow.code_change_benchmark import load_code_change_benchmark, run_code_change_benchmark
from workflow.bullet_hell_benchmark import load_bullet_hell_benchmark, run_bullet_hell_benchmark
from workflow.real_code_evaluation import (
    load_real_code_dataset,
    real_provider_configuration_status,
    replay_real_code_evaluation,
    run_real_code_evaluation,
)


SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SERVICE_ROOT.parents[1]
RUNTIME_ARTIFACTS_DIR = REPOSITORY_ROOT / "runtime-artifacts"
UNITY_EXECUTABLE = (
    REPOSITORY_ROOT
    / "game-unity"
    / "Builds"
    / "Windows"
    / "GameConfigRuntimeDemo.exe"
)
BULLET_HELL_EXECUTABLE = (
    REPOSITORY_ROOT
    / "game-unity"
    / "Builds"
    / "BulletHellWindows"
    / "BulletHellDemo.exe"
)


class ChangeWorkflowCreateRequest(BaseModel):
    requirement_text: str = Field(..., min_length=1)
    case_id: str = Field("case_01_baseline_trial", min_length=1)
    provider: str = Field("mock", pattern="^(mock|openai_compatible)$")
    timeout_seconds: int = Field(60, ge=5, le=300)


class ChangeWorkflowApprovalRequest(BaseModel):
    approver: str = Field(..., min_length=1)
    note: str = ""


class ChangeWorkflowLaunchRequest(BaseModel):
    mode: str = Field("manual", pattern="^(manual|auto)$")


class ChangeWorkflowDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(accept|revise|rollback)$")
    actor: str = Field(..., min_length=1)
    note: str = Field(..., min_length=1)


class CodeWorkflowCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    change_reason: str = Field(..., min_length=1)
    diff_text: str = Field(..., min_length=1)
    provider: str = Field("mock", pattern="^(mock|openai_compatible)$")
    timeout_seconds: int = Field(60, ge=5, le=300)


class CodeWorkflowApprovalRequest(BaseModel):
    approver: str = Field(..., min_length=1)
    note: str = ""


class CodeWorkflowDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(accept|revise|rollback)$")
    actor: str = Field(..., min_length=1)
    note: str = Field(..., min_length=1)


class CodeChangeProposalRequest(BaseModel):
    requirement_text: str = Field(..., min_length=1)
    target_files: list[str] = Field(..., min_length=1, max_length=3)
    provider: str = Field("mock", pattern="^(mock|openai_compatible)$")
    timeout_seconds: int = Field(60, ge=5, le=300)


class RealCodeEvaluationRequest(BaseModel):
    timeout_seconds: int = Field(60, ge=5, le=180)


class BulletHellWorkflowCreateRequest(BaseModel):
    requirement_text: str = Field(..., min_length=1)
    provider: str = Field("mock", pattern="^(mock|openai_compatible)$")
    timeout_seconds: int = Field(60, ge=5, le=300)
    engine: str = Field("unity", pattern="^(unity|unreal)$")


class BulletHellAuthorizationRequest(BaseModel):
    actor: str = Field(..., min_length=1)
    note: str = ""


class BulletHellDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(accept|revise|rollback)$")
    actor: str = Field(..., min_length=1)
    note: str = Field(..., min_length=1)


def create_unified_app(
    *,
    runtime_run_service: RuntimeRunService | None = None,
    change_workflow_service: ChangeWorkflowService | None = None,
    code_workflow_service: CodeWorkflowService | None = None,
    code_change_agent_service: CodeChangeAgentService | None = None,
    code_change_benchmark_dir: Path | None = None,
    real_code_evaluation_dir: Path | None = None,
    real_code_provider_factory: Any | None = None,
    bullet_hell_workflow_service: BulletHellWorkflowService | None = None,
    bullet_hell_benchmark_dir: Path | None = None,
):
    runtime_runs = runtime_run_service or RuntimeRunService(
        project_root=REPOSITORY_ROOT,
        runs_dir=RUNTIME_ARTIFACTS_DIR / "runtime_runs",
        unity_executable=UNITY_EXECUTABLE,
    )
    change_workflows = change_workflow_service or ChangeWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=RUNTIME_ARTIFACTS_DIR / "change_workflows",
        runtime_runs=runtime_runs,
    )
    code_workflows = code_workflow_service or CodeWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=RUNTIME_ARTIFACTS_DIR / "code_workflows",
    )
    code_change_agent = code_change_agent_service or CodeChangeAgentService(
        repository_root=REPOSITORY_ROOT,
        proposals_dir=RUNTIME_ARTIFACTS_DIR / "code_change_agent",
        code_workflows=code_workflows,
    )
    benchmark_dir = code_change_benchmark_dir or RUNTIME_ARTIFACTS_DIR / "code_change_benchmark"
    real_evaluation_dir = real_code_evaluation_dir or RUNTIME_ARTIFACTS_DIR / "real-code-evaluation"
    bullet_hell_workflows = bullet_hell_workflow_service or BulletHellWorkflowService(
        repository_root=REPOSITORY_ROOT,
        workflows_dir=RUNTIME_ARTIFACTS_DIR / "bullet-hell-workflows",
        unity_executable=BULLET_HELL_EXECUTABLE,
    )
    bullet_benchmark_dir = bullet_hell_benchmark_dir or RUNTIME_ARTIFACTS_DIR / "bullet-hell-benchmark"
    application = create_app(runtime_run_service=runtime_runs)
    application.title = "Agentic Game R&D Lab API"

    @application.get("/api/quality/health")
    def quality_health() -> dict[str, str]:
        return {"status": "ok", "capability": "quality_review"}

    @application.post("/api/quality/review", response_model=ReviewResponse)
    def quality_review(request: ReviewRequest) -> ReviewResponse:
        if request.workflow == "dual_agent":
            return run_dual_agent(request)
        return run_single_agent(request)

    @application.get("/api/bullet-hell/capabilities")
    def bullet_hell_capabilities() -> dict[str, Any]:
        return bullet_hell_workflows.capabilities()

    @application.get("/api/bullet-hell/benchmark/dataset")
    def bullet_hell_benchmark_dataset() -> dict[str, Any]:
        dataset = load_bullet_hell_benchmark(REPOSITORY_ROOT)
        return {
            "dataset_id": dataset["dataset_id"],
            "title": dataset["title"],
            "provider_mode": dataset["provider_mode"],
            "disclaimer": dataset["disclaimer"],
            "sample_count": len(dataset["samples"]),
            "samples": [
                {
                    "sample_id": row["sample_id"],
                    "category": row["category"],
                    "expected_decision": row["expected_decision"],
                }
                for row in dataset["samples"]
            ],
        }

    @application.post("/api/bullet-hell/benchmark")
    def execute_bullet_hell_benchmark() -> dict[str, Any]:
        return run_bullet_hell_benchmark(REPOSITORY_ROOT, bullet_benchmark_dir)

    @application.post("/api/bullet-hell/workflows")
    def create_bullet_hell_workflow(request: BulletHellWorkflowCreateRequest) -> dict[str, Any]:
        try:
            return bullet_hell_workflows.create(
                requirement_text=request.requirement_text,
                provider=request.provider,
                timeout_seconds=request.timeout_seconds,
                engine=request.engine,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.get("/api/bullet-hell/workflows/latest")
    def latest_bullet_hell_workflow() -> dict[str, Any]:
        try:
            return bullet_hell_workflows.latest()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.get("/api/bullet-hell/workflows/{workflow_id}")
    def get_bullet_hell_workflow(workflow_id: str) -> dict[str, Any]:
        try:
            return bullet_hell_workflows.get(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.post("/api/bullet-hell/workflows/{workflow_id}/authorize")
    def authorize_bullet_hell_workflow(
        workflow_id: str,
        request: BulletHellAuthorizationRequest,
    ) -> dict[str, Any]:
        try:
            return bullet_hell_workflows.authorize(workflow_id, actor=request.actor, note=request.note)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/bullet-hell/workflows/{workflow_id}/run")
    def run_bullet_hell_workflow(workflow_id: str) -> dict[str, Any]:
        try:
            return bullet_hell_workflows.start(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/bullet-hell/workflows/{workflow_id}/play")
    def play_bullet_hell_workflow(workflow_id: str) -> dict[str, Any]:
        try:
            return bullet_hell_workflows.launch_manual(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/bullet-hell/workflows/{workflow_id}/play/{variant}")
    def play_bullet_hell_workflow_variant(workflow_id: str, variant: str) -> dict[str, Any]:
        try:
            return bullet_hell_workflows.launch_manual(workflow_id, variant=variant)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/bullet-hell/workflows/{workflow_id}/visual-comparison")
    def generate_bullet_hell_visual_comparison(workflow_id: str) -> dict[str, Any]:
        try:
            return bullet_hell_workflows.generate_visual_comparison(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/bullet-hell/workflows/{workflow_id}/visuals/{variant}/{name}")
    def bullet_hell_visual_artifact(workflow_id: str, variant: str, name: str) -> FileResponse:
        try:
            path = bullet_hell_workflows.visual_artifact(workflow_id, variant, name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return FileResponse(path, media_type="image/png", filename=path.name)

    @application.post("/api/bullet-hell/workflows/{workflow_id}/decision")
    def decide_bullet_hell_workflow(
        workflow_id: str,
        request: BulletHellDecisionRequest,
    ) -> dict[str, Any]:
        try:
            return bullet_hell_workflows.decide(
                workflow_id,
                decision=request.decision,
                actor=request.actor,
                note=request.note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/bullet-hell/workflows/{workflow_id}/artifacts/{name}")
    def bullet_hell_workflow_artifact(workflow_id: str, name: str) -> PlainTextResponse:
        try:
            path = bullet_hell_workflows.artifact(workflow_id, name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PlainTextResponse(path.read_text(encoding="utf-8-sig"))

    @application.post("/api/change-workflows")
    def create_change_workflow(request: ChangeWorkflowCreateRequest) -> dict[str, Any]:
        try:
            return change_workflows.create(
                requirement_text=request.requirement_text,
                case_id=request.case_id,
                provider=request.provider,
                timeout_seconds=request.timeout_seconds,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.get("/api/change-workflows/{workflow_id}")
    def get_change_workflow(workflow_id: str) -> dict[str, Any]:
        try:
            return change_workflows.get(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.post("/api/change-workflows/{workflow_id}/approve")
    def approve_change_workflow(
        workflow_id: str,
        request: ChangeWorkflowApprovalRequest,
    ) -> dict[str, Any]:
        try:
            return change_workflows.approve(
                workflow_id,
                approver=request.approver,
                note=request.note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/change-workflows/{workflow_id}/runtime")
    def prepare_change_workflow_runtime(workflow_id: str) -> dict[str, Any]:
        try:
            return change_workflows.prepare_runtime(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/change-workflows/{workflow_id}/launch")
    def launch_change_workflow_runtime(
        workflow_id: str,
        request: ChangeWorkflowLaunchRequest,
    ) -> dict[str, Any]:
        try:
            return change_workflows.launch_runtime(workflow_id, mode=request.mode)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/change-workflows/{workflow_id}/decision")
    def decide_change_workflow(
        workflow_id: str,
        request: ChangeWorkflowDecisionRequest,
    ) -> dict[str, Any]:
        try:
            return change_workflows.decide(
                workflow_id,
                decision=request.decision,
                actor=request.actor,
                note=request.note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/change-workflows/{workflow_id}/artifacts/{name}")
    def change_workflow_artifact(workflow_id: str, name: str) -> PlainTextResponse:
        try:
            path = change_workflows.artifact(workflow_id, name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PlainTextResponse(path.read_text(encoding="utf-8"))

    @application.post("/api/code-workflows")
    def create_code_workflow(request: CodeWorkflowCreateRequest) -> dict[str, Any]:
        try:
            return code_workflows.create(
                title=request.title,
                change_reason=request.change_reason,
                diff_text=request.diff_text,
                provider=request.provider,
                timeout_seconds=request.timeout_seconds,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.get("/api/code-workflows/{workflow_id}")
    def get_code_workflow(workflow_id: str) -> dict[str, Any]:
        try:
            return code_workflows.get(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.post("/api/code-workflows/{workflow_id}/approve")
    def approve_code_workflow(
        workflow_id: str,
        request: CodeWorkflowApprovalRequest,
    ) -> dict[str, Any]:
        try:
            return code_workflows.approve(
                workflow_id,
                approver=request.approver,
                note=request.note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/code-workflows/{workflow_id}/workspace")
    def prepare_code_workflow_workspace(workflow_id: str) -> dict[str, Any]:
        try:
            return code_workflows.prepare_workspace(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, FileNotFoundError, FileExistsError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/code-workflows/{workflow_id}/validate")
    def validate_code_workflow(workflow_id: str) -> dict[str, Any]:
        try:
            return code_workflows.start_validation(workflow_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.post("/api/code-workflows/{workflow_id}/decision")
    def decide_code_workflow(
        workflow_id: str,
        request: CodeWorkflowDecisionRequest,
    ) -> dict[str, Any]:
        try:
            return code_workflows.decide(
                workflow_id,
                decision=request.decision,
                actor=request.actor,
                note=request.note,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @application.get("/api/code-workflows/{workflow_id}/artifacts/{name}")
    def code_workflow_artifact(workflow_id: str, name: str) -> PlainTextResponse:
        try:
            path = code_workflows.artifact(workflow_id, name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PlainTextResponse(path.read_text(encoding="utf-8-sig"))

    @application.get("/api/code-change-agent/capabilities")
    def code_change_capabilities() -> dict[str, Any]:
        return code_change_agent.capabilities()

    @application.post("/api/code-change-agent/proposals")
    def create_code_change_proposal(request: CodeChangeProposalRequest) -> dict[str, Any]:
        try:
            return code_change_agent.propose(
                requirement_text=request.requirement_text,
                target_files=request.target_files,
                provider=request.provider,
                timeout_seconds=request.timeout_seconds,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.get("/api/code-change-agent/proposals/{proposal_id}")
    def get_code_change_proposal(proposal_id: str) -> dict[str, Any]:
        try:
            return code_change_agent.get(proposal_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @application.get("/api/code-change-agent/benchmark/dataset")
    def get_code_change_benchmark_dataset() -> dict[str, Any]:
        dataset = load_code_change_benchmark(REPOSITORY_ROOT)
        return {
            "dataset_id": dataset["dataset_id"],
            "title": dataset["title"],
            "evaluation_subject": dataset["evaluation_subject"],
            "provider_mode": dataset["provider_mode"],
            "disclaimer": dataset["disclaimer"],
            "sample_count": len(dataset["samples"]),
            "samples": [
                {
                    "sample_id": sample["sample_id"],
                    "category": sample["category"],
                    "expected_status": sample["expected_status"],
                    "expected_stage": sample["expected_stage"],
                }
                for sample in dataset["samples"]
            ],
        }

    @application.post("/api/code-change-agent/benchmark")
    def execute_code_change_benchmark() -> dict[str, Any]:
        return run_code_change_benchmark(REPOSITORY_ROOT, benchmark_dir)

    @application.get("/api/code-change-agent/real-evaluation/config")
    def get_real_code_provider_configuration() -> dict[str, Any]:
        if real_code_provider_factory is not None:
            return {"configured": True, "variables": {}, "missing": [], "injected_for_test": True}
        return real_provider_configuration_status(REPOSITORY_ROOT)

    @application.get("/api/code-change-agent/real-evaluation/dataset")
    def get_real_code_evaluation_dataset() -> dict[str, Any]:
        dataset = load_real_code_dataset(REPOSITORY_ROOT)
        return {
            "dataset_id": dataset["dataset_id"],
            "title": dataset["title"],
            "scope": dataset["scope"],
            "sample_count": len(dataset["samples"]),
            "samples": [
                {
                    "sample_id": sample["sample_id"],
                    "title": sample["title"],
                    "target_files": sample["target_files"],
                    "semantic_check_count": len(sample["semantic_checks"]),
                }
                for sample in dataset["samples"]
            ],
        }

    @application.post("/api/code-change-agent/real-evaluation")
    def execute_real_code_evaluation(request: RealCodeEvaluationRequest) -> dict[str, Any]:
        return run_real_code_evaluation(
            REPOSITORY_ROOT,
            real_evaluation_dir,
            timeout_seconds=request.timeout_seconds,
            provider_factory=real_code_provider_factory,
        )

    @application.get("/api/code-change-agent/real-evaluation/latest")
    def get_latest_real_code_evaluation() -> dict[str, Any]:
        result_path = real_evaluation_dir / "real_code_evaluation.json"
        if not result_path.is_file():
            raise HTTPException(status_code=404, detail="No real code evaluation result is available.")
        return json.loads(result_path.read_text(encoding="utf-8-sig"))

    @application.post("/api/code-change-agent/real-evaluation/replay")
    def replay_latest_real_code_evaluation() -> dict[str, Any]:
        try:
            return replay_real_code_evaluation(REPOSITORY_ROOT, real_evaluation_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return application


app = create_unified_app()
