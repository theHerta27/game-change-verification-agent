"""FastAPI local API wrapper for the Web Console."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from gameconfig_agent.agents.test_scenario import TestScenarioAgent
from gameconfig_agent.cli import run_phase0_demo
from gameconfig_agent.data.classic_cases import list_classic_cases
from gameconfig_agent.data.evaluation_dataset import EVALUATION_DATASET
from gameconfig_agent.env_loader import load_dotenv
from gameconfig_agent.evaluation_evidence import build_evaluation_evidence
from gameconfig_agent.phase3_benchmark import run_phase3_benchmark
from gameconfig_agent.providers import MockLLMProvider, OpenAICompatibleProvider
from gameconfig_agent.real_run import export_real_run, failed_evaluation_result, run_real_sample
from gameconfig_agent.requirement_intake import analyze_requirement
from gameconfig_agent.runtime_runs import RuntimeRunService
from gameconfig_agent.tools.evaluator import EvaluationTool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
OUTPUTS_DIR = Path(
    os.environ.get("AGENTIC_GAME_RD_RUNTIME_DIR", REPOSITORY_ROOT / "runtime-artifacts")
)
BACKEND_VERSION = "phase6g-real-runtime-handoff"
BACKEND_CAPABILITIES = {
    "real_provider_runtime_handoff": True,
    "runtime_run_polling": True,
    "planner_developer_views": True,
    "requirement_intake": True,
}


class DemoRunRequest(BaseModel):
    requirement_text: str = Field(..., min_length=1)
    provider: str = Field("mock", pattern="^(mock|openai_compatible)$")
    timeout_seconds: int = Field(60, ge=5, le=300)


class BenchmarkRunRequest(BaseModel):
    output: str = "outputs/phase3"


class RuntimeRunPrepareRequest(BaseModel):
    case_id: str = Field(..., min_length=1)
    requirement_text: str = Field(..., min_length=1)
    provider: str = Field("mock", pattern="^(mock|openai_compatible)$")
    structured_requirement: dict[str, Any] | None = None
    final_configs: dict[str, Any] | None = None
    model: str | None = None


class RuntimeRunLaunchRequest(BaseModel):
    mode: str = Field("manual", pattern="^(manual|auto)$")


class RequirementIntakeRequest(BaseModel):
    requirement_text: str = Field(..., min_length=1)


def create_app(runtime_run_service: RuntimeRunService | None = None) -> FastAPI:
    runtime_runs = runtime_run_service or RuntimeRunService()
    app = FastAPI(title="GameConfig Agent Web Console API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root() -> dict[str, Any]:
        return {
            "service": "GameConfig Agent Web Console API",
            "status": "ok",
            "message": "这是后端 API 服务。请打开前端页面 http://127.0.0.1:5173 使用 Web Console。",
            "health": "/api/health",
            "docs": "/docs",
            "frontend": "http://127.0.0.1:5173",
        }

    @app.get("/favicon.ico")
    def favicon() -> PlainTextResponse:
        return PlainTextResponse("", status_code=204)

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "gameconfig-agent-web-console",
            "backend_version": BACKEND_VERSION,
            "capabilities": BACKEND_CAPABILITIES,
        }

    @app.get("/api/classic-cases")
    def classic_cases() -> dict[str, Any]:
        return {"cases": list_classic_cases()}

    @app.get("/api/evaluation-evidence")
    def evaluation_evidence(case_id: str) -> dict[str, Any]:
        try:
            return build_evaluation_evidence(case_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/requirement-intake")
    def requirement_intake(request: RequirementIntakeRequest) -> dict[str, Any]:
        return analyze_requirement(request.requirement_text)

    @app.post("/api/runtime-runs")
    def prepare_runtime_run(request: RuntimeRunPrepareRequest) -> dict[str, Any]:
        try:
            return runtime_runs.prepare(
                case_id=request.case_id,
                requirement_text=request.requirement_text,
                provider=request.provider,
                structured_requirement=request.structured_requirement,
                final_configs=request.final_configs,
                model=request.model,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/runtime-runs/{run_id}/launch")
    def launch_runtime_run(run_id: str, request: RuntimeRunLaunchRequest) -> dict[str, Any]:
        try:
            return runtime_runs.launch(run_id, mode=request.mode)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/runtime-runs/{run_id}")
    def runtime_run_status(run_id: str) -> dict[str, Any]:
        try:
            return runtime_runs.get(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/runtime-runs/{run_id}/evaluate")
    def evaluate_runtime_run(run_id: str) -> dict[str, Any]:
        try:
            return runtime_runs.evaluate(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/runtime-runs/{run_id}/artifacts/{name}")
    def runtime_run_artifact(run_id: str, name: str) -> PlainTextResponse:
        try:
            path = runtime_runs.artifact(run_id, name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PlainTextResponse(path.read_text(encoding="utf-8"))

    @app.post("/api/runs/demo")
    def run_demo(request: DemoRunRequest) -> dict[str, Any]:
        load_dotenv(PROJECT_ROOT / ".env")
        phase0_dir = OUTPUTS_DIR / "phase0"
        phase1_dir = OUTPUTS_DIR / "phase1"
        phase2_dir = OUTPUTS_DIR / "phase2"
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
            handle.write(request.requirement_text)
            input_path = Path(handle.name)
        phase0: dict[str, Any] = {}
        scenarios: list[dict[str, Any]] = []
        evaluation: dict[str, Any] = {
            "coverage_percent": 0,
            "coverage": 0,
            "covered_tag_count": 0,
            "expected_tag_count": 0,
        }
        try:
            provider = _provider_for_request(request)
            if request.provider == "mock":
                phase0 = run_phase0_demo(input_path, phase0_dir)
                scenarios = TestScenarioAgent().generate(phase0["repaired_configs"])
                evaluation = EvaluationTool().evaluate(scenarios, EVALUATION_DATASET)
                _write_json(phase1_dir / "test_scenarios.json", scenarios)
                _write_json(phase1_dir / "evaluation.json", evaluation)

            real_result = run_real_sample(provider, request.requirement_text)
            if request.provider == "openai_compatible" and real_result.get("results"):
                primary_result = real_result["results"][0]
                scenarios = primary_result.get("test_scenarios", [])
                evaluation = primary_result.get("evaluation", evaluation)
            real_result["exported_files"] = [str(path) for path in export_real_run(real_result, phase2_dir)]
        except Exception as exc:
            if request.provider == "openai_compatible":
                real_result = failed_evaluation_result(request.provider, exc, request.requirement_text)
                real_result["exported_files"] = [str(path) for path in export_real_run(real_result, phase2_dir)]
                phase0 = {}
                scenarios = []
                evaluation = {"coverage_percent": 0, "coverage": 0, "covered_tag_count": 0, "expected_tag_count": 0}
            else:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
        finally:
            input_path.unlink(missing_ok=True)

        artifacts = {"phase2": _artifact_list(phase2_dir)}
        if request.provider == "mock":
            artifacts = {
                "phase0": _artifact_list(phase0_dir),
                "phase1": _artifact_list(phase1_dir),
                **artifacts,
            }
        return {
            "workflow_summary": _workflow_summary(phase0, scenarios, evaluation, real_result),
            "phase0": phase0,
            "test_scenarios": scenarios,
            "evaluation": evaluation,
            "real_run": real_result,
            "artifacts": artifacts,
        }

    @app.post("/api/runs/benchmark")
    def run_benchmark(request: BenchmarkRunRequest) -> dict[str, Any]:
        requested_output = Path(request.output)
        output_dir = (
            OUTPUTS_DIR.joinpath(*requested_output.parts[1:])
            if requested_output.parts and requested_output.parts[0] == "outputs"
            else PROJECT_ROOT / requested_output
        )
        result = run_phase3_benchmark(output_dir)
        return {"benchmark": result, "artifacts": {"phase3": _artifact_list(output_dir)}}

    @app.get("/api/artifacts/{phase}")
    def artifacts(phase: str) -> dict[str, Any]:
        phase_dir = OUTPUTS_DIR / phase
        if not phase_dir.exists():
            return {"phase": phase, "files": []}
        return {"phase": phase, "files": _artifact_list(phase_dir)}

    @app.get("/api/reports/{phase}/{name}")
    def report(phase: str, name: str) -> PlainTextResponse:
        if ".." in phase or ".." in name:
            raise HTTPException(status_code=400, detail="Invalid report path.")
        path = OUTPUTS_DIR / phase / name
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="Report not found.")
        return PlainTextResponse(path.read_text(encoding="utf-8"))

    return app


def _provider_for_request(request: DemoRunRequest):
    if request.provider == "mock":
        return MockLLMProvider()
    return OpenAICompatibleProvider(timeout_seconds=request.timeout_seconds)


def _workflow_summary(phase0: dict, scenarios: list[dict], evaluation: dict, real_result: dict) -> dict[str, Any]:
    primary_result = (real_result.get("results") or [{}])[0]
    is_real = real_result.get("provider") == "openai_compatible"
    final_validation = primary_result.get("final_validation", {}) if is_real else phase0.get("final_validation", {})
    metrics = real_result.get("metrics", {})
    return {
        "final_validation_passed": final_validation.get("passed", False),
        "trace_steps": len(primary_result.get("trace", [])) if is_real else len(phase0.get("trace", [])),
        "repair_actions": len(primary_result.get("repair_actions", [])) if is_real else len(phase0.get("repair_actions", [])),
        "test_scenarios": len(scenarios),
        "coverage_percent": evaluation.get("coverage_percent", 0),
        "real_run_badcases": metrics.get("badcase_count", 0),
        "provider": real_result.get("provider"),
    }


def _artifact_list(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    return [
        {"name": path.name, "path": str(path), "size": path.stat().st_size}
        for path in sorted(directory.iterdir())
        if path.is_file()
    ]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


app = create_app()
