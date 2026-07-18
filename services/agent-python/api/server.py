"""Single FastAPI entry point for the migrated Agent capabilities."""

from __future__ import annotations

from pathlib import Path

from agent_service.agents.dual_agent import run_dual_agent
from agent_service.agents.single_agent import run_single_agent
from agent_service.schemas import ReviewRequest, ReviewResponse
from gameconfig_agent.runtime_runs import RuntimeRunService
from gameconfig_agent.server import create_app


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


runtime_run_service = RuntimeRunService(
    project_root=REPOSITORY_ROOT,
    runs_dir=RUNTIME_ARTIFACTS_DIR / "runtime_runs",
    unity_executable=UNITY_EXECUTABLE,
)
app = create_app(runtime_run_service=runtime_run_service)
app.title = "Agentic Game R&D Lab API"


@app.get("/api/quality/health")
def quality_health() -> dict[str, str]:
    return {"status": "ok", "capability": "quality_review"}


@app.post("/api/quality/review", response_model=ReviewResponse)
def quality_review(request: ReviewRequest) -> ReviewResponse:
    if request.workflow == "dual_agent":
        return run_dual_agent(request)
    return run_single_agent(request)

