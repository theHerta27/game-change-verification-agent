"""File-backed Milestone 3A config-change workflow state machine."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import hashlib
import json
import uuid

from gameconfig_agent.env_loader import load_dotenv
from gameconfig_agent.data.classic_cases import load_classic_case
from gameconfig_agent.providers import MockLLMProvider, OpenAICompatibleProvider
from gameconfig_agent.real_run import run_real_sample
from gameconfig_agent.runtime_runs import RuntimeRunService
from workflow.config_change import (
    apply_constraints,
    build_config_diff,
    build_quality_review,
    load_baseline_configs,
    review_runtime_evidence,
    run_feasibility_gate,
    validate_candidate,
)


ProviderFactory = Callable[[str, int], Any]
TERMINAL_STATUSES = {"accepted", "revision_requested", "rolled_back", "rejected", "needs_clarification"}


class ChangeWorkflowService:
    def __init__(
        self,
        *,
        repository_root: Path,
        workflows_dir: Path,
        runtime_runs: RuntimeRunService,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        self.repository_root = repository_root
        self.workflows_dir = workflows_dir
        self.runtime_runs = runtime_runs
        self.provider_factory = provider_factory or _provider_factory
        self.baseline_contract = repository_root / "game-unity" / "Assets" / "StreamingAssets" / "game_config.json"

    def create(
        self,
        *,
        requirement_text: str,
        case_id: str = "case_01_baseline_trial",
        provider: str = "mock",
        timeout_seconds: int = 60,
    ) -> dict[str, Any]:
        if provider not in {"mock", "openai_compatible"}:
            raise ValueError(f"Unsupported provider: {provider}")
        try:
            load_classic_case(case_id)
        except KeyError as exc:
            raise ValueError(f"Unknown classic case: {case_id}") from exc
        workflow_id = _new_workflow_id()
        workflow_dir = self.workflows_dir / workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=False)
        (workflow_dir / "requirement.txt").write_text(requirement_text.strip(), encoding="utf-8")
        now = _utc_now()
        manifest: dict[str, Any] = {
            "workflow_id": workflow_id,
            "case_id": case_id,
            "provider": provider,
            "model": None,
            "status": "proposing",
            "created_at": now,
            "updated_at": now,
            "runtime_run_id": None,
            "approval": None,
            "final_decision": None,
            "error": None,
            "timeline": [],
        }
        self._event(manifest, "Requirement submitted", "completed", {"provider": provider})
        self._write_manifest(workflow_dir, manifest)

        gate = run_feasibility_gate(requirement_text)
        _write_json(workflow_dir / "feasibility_gate.json", gate)
        self._event(manifest, "Change Feasibility Gate", gate["decision"], {"reason": gate["reason"]})
        if gate["decision"] != "accepted":
            manifest["status"] = gate["decision"]
            self._write_manifest(workflow_dir, manifest)
            return self.get(workflow_id)

        try:
            committed_baseline = load_baseline_configs(self.baseline_contract)
            generation_baseline = deepcopy(committed_baseline)
            provider_requirement = None
            provider_evidence: dict[str, Any] = {"provider": provider, "mode": "deterministic_baseline"}
            if provider == "openai_compatible":
                load_dotenv(self.repository_root / ".env")
                provider_client = self.provider_factory(provider, timeout_seconds)
                real_run = run_real_sample(provider_client, requirement_text, sample_id=workflow_id)
                provider_evidence = real_run
                sample = real_run["results"][0]
                manifest["model"] = real_run.get("model")
                if not sample["final_validation"]["passed"]:
                    raise ProviderCandidateError("真实模型候选配置未通过现有静态校验。", real_run)
                generation_baseline.update(deepcopy(sample["repaired_configs"]))
                provider_requirement = deepcopy(sample["structured_requirement"])

            candidate, mapped_requirement, mapping_actions = apply_constraints(
                generation_baseline,
                gate["constraints"],
            )
            structured_requirement = provider_requirement or mapped_requirement
            structured_requirement.update(mapped_requirement)
            static_validation = validate_candidate(structured_requirement, candidate)
            config_diff = build_config_diff(committed_baseline, candidate)
            review = build_quality_review(gate["constraints"], candidate, config_diff, static_validation)

            _write_json(workflow_dir / "baseline_configs.json", committed_baseline)
            _write_json(workflow_dir / "candidate_configs.json", candidate)
            _write_json(workflow_dir / "structured_requirement.json", structured_requirement)
            _write_json(workflow_dir / "constraint_mapping.json", mapping_actions)
            _write_json(workflow_dir / "config_diff.json", config_diff)
            _write_json(workflow_dir / "static_validation.json", static_validation)
            _write_json(workflow_dir / "quality_review.json", review)
            _write_json(workflow_dir / "provider_evidence.json", provider_evidence)
            manifest["baseline_hash"] = _hash_json(committed_baseline)
            manifest["candidate_hash"] = _hash_json(candidate)
            manifest["change_count"] = len(config_diff)
            manifest["status"] = "proposed" if static_validation["passed"] and review["approval_recommended"] else "failed"
            self._event(manifest, "Game Change Agent", "completed", {"change_count": len(config_diff)})
            self._event(manifest, "Quality Review Agent", "completed", {"approval_recommended": review["approval_recommended"]})
            self._event(
                manifest,
                "Deterministic Validation",
                "completed" if static_validation["passed"] else "failed",
                {},
            )
        except ProviderCandidateError as exc:
            _write_json(workflow_dir / "provider_evidence.json", exc.evidence)
            manifest["status"] = "failed"
            manifest["error"] = {"type": type(exc).__name__, "message": str(exc)}
            self._event(manifest, "Game Change Agent", "failed", manifest["error"])
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = {"type": type(exc).__name__, "message": str(exc)}
            self._event(manifest, "Config proposal pipeline", "failed", manifest["error"])
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def approve(self, workflow_id: str, *, approver: str, note: str = "") -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        approver = approver.strip()
        if not approver:
            raise ValueError("approver must not be blank.")
        if manifest["status"] != "proposed":
            raise ValueError(f"Workflow cannot be approved from status {manifest['status']!r}.")
        review = _read_json(workflow_dir / "quality_review.json")
        validation = _read_json(workflow_dir / "static_validation.json")
        if not validation["passed"] or not review["approval_recommended"]:
            raise ValueError("Candidate must pass static validation and quality review before approval.")
        manifest["approval"] = {
            "approver": approver,
            "note": note.strip(),
            "approved_at": _utc_now(),
        }
        manifest["status"] = "approved"
        self._event(manifest, "Human approval", "completed", {"approver": approver})
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def prepare_runtime(self, workflow_id: str) -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        if manifest["status"] != "approved":
            raise ValueError(f"Runtime cannot be prepared from status {manifest['status']!r}.")
        run = self.runtime_runs.prepare_snapshot(
            case_id=manifest["case_id"],
            requirement_text=(workflow_dir / "requirement.txt").read_text(encoding="utf-8"),
            source_provider=manifest["provider"],
            structured_requirement=_read_json(workflow_dir / "structured_requirement.json"),
            final_configs=_read_json(workflow_dir / "candidate_configs.json"),
            model=manifest.get("model"),
            source_workflow_id=workflow_id,
        )
        manifest["runtime_run_id"] = run["run_id"]
        manifest["status"] = "runtime_prepared"
        self._event(manifest, "Isolated config apply", "completed", {"runtime_run_id": run["run_id"]})
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def launch_runtime(self, workflow_id: str, *, mode: str = "manual") -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        if manifest["status"] != "runtime_prepared":
            raise ValueError(f"Runtime cannot be launched from status {manifest['status']!r}.")
        run = self.runtime_runs.launch(manifest["runtime_run_id"], mode=mode)
        manifest["status"] = "runtime_launched"
        self._event(
            manifest,
            "Unity playtest",
            "in_progress",
            {"mode": mode, "process_id": run.get("process_id")},
        )
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def decide(self, workflow_id: str, *, decision: str, actor: str, note: str) -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        actor = actor.strip()
        note = note.strip()
        if not actor or not note:
            raise ValueError("actor and note must not be blank.")
        if decision not in {"accept", "revise", "rollback"}:
            raise ValueError("decision must be accept, revise, or rollback.")
        if decision in {"accept", "revise"} and manifest["status"] != "evidence_ready":
            raise ValueError("Accept or revise requires completed Unity evidence.")
        if decision == "rollback" and manifest["status"] not in {"approved", "runtime_prepared", "evidence_ready", "failed"}:
            raise ValueError(f"Workflow cannot be rolled back from status {manifest['status']!r}.")
        status = {"accept": "accepted", "revise": "revision_requested", "rollback": "rolled_back"}[decision]
        manifest["status"] = status
        manifest["final_decision"] = {
            "decision": decision,
            "actor": actor,
            "note": note,
            "decided_at": _utc_now(),
            "active_config_hash": manifest["candidate_hash"] if decision == "accept" else manifest["baseline_hash"],
        }
        self._event(manifest, "Human final decision", status, {"actor": actor, "note": note})
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def get(self, workflow_id: str) -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        runtime = None
        if manifest.get("runtime_run_id"):
            runtime = self.runtime_runs.get(manifest["runtime_run_id"])
            if manifest["status"] not in TERMINAL_STATUSES:
                if runtime["status"] == "evaluated" and manifest["status"] != "evidence_ready":
                    evidence_review = review_runtime_evidence(runtime)
                    _write_json(workflow_dir / "runtime_evidence_review.json", evidence_review)
                    manifest["status"] = "evidence_ready"
                    self._event(
                        manifest,
                        "Telemetry Evaluator",
                        "completed",
                        {"passed": runtime["evaluation"]["passed"]},
                    )
                    self._event(
                        manifest,
                        "Quality Review Agent evidence review",
                        "completed",
                        {"recommendation": evidence_review["recommendation"]},
                    )
                    self._write_manifest(workflow_dir, manifest)
                elif runtime["status"] == "failed" and manifest["status"] == "runtime_launched":
                    manifest["status"] = "failed"
                    manifest["error"] = runtime.get("error")
                    self._event(manifest, "Unity playtest", "failed", runtime.get("error") or {})
                    self._write_manifest(workflow_dir, manifest)
        response = deepcopy(manifest)
        response["feasibility_gate"] = _read_json_if_exists(workflow_dir / "feasibility_gate.json")
        response["config_diff"] = _read_json_if_exists(workflow_dir / "config_diff.json") or []
        response["static_validation"] = _read_json_if_exists(workflow_dir / "static_validation.json")
        response["quality_review"] = _read_json_if_exists(workflow_dir / "quality_review.json")
        response["runtime_evidence_review"] = _read_json_if_exists(workflow_dir / "runtime_evidence_review.json")
        response["runtime_run"] = runtime
        response["available_artifacts"] = [
            {"name": path.name, "size": path.stat().st_size}
            for path in sorted(workflow_dir.iterdir())
            if path.is_file()
        ]
        return response

    def artifact(self, workflow_id: str, name: str) -> Path:
        allowed = {
            "requirement.txt",
            "feasibility_gate.json",
            "baseline_configs.json",
            "candidate_configs.json",
            "structured_requirement.json",
            "constraint_mapping.json",
            "config_diff.json",
            "static_validation.json",
            "quality_review.json",
            "provider_evidence.json",
            "runtime_evidence_review.json",
            "workflow_manifest.json",
        }
        if name not in allowed:
            raise ValueError("Artifact name is not allowed.")
        workflow_dir, _ = self._load(workflow_id)
        path = workflow_dir / name
        if not path.is_file():
            raise FileNotFoundError(name)
        return path

    def _load(self, workflow_id: str) -> tuple[Path, dict[str, Any]]:
        if not workflow_id.startswith("change_") or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in workflow_id
        ):
            raise KeyError("Invalid change workflow id.")
        workflow_dir = self.workflows_dir / workflow_id
        manifest_path = workflow_dir / "workflow_manifest.json"
        if not manifest_path.is_file():
            raise KeyError(f"Unknown change workflow: {workflow_id}")
        return workflow_dir, _read_json(manifest_path)

    def _write_manifest(self, workflow_dir: Path, manifest: dict[str, Any]) -> None:
        manifest["updated_at"] = _utc_now()
        _write_json(workflow_dir / "workflow_manifest.json", manifest)

    def _event(self, manifest: dict[str, Any], step: str, status: str, detail: dict[str, Any]) -> None:
        manifest["timeline"].append(
            {"step": step, "status": status, "timestamp": _utc_now(), "detail": detail}
        )


class ProviderCandidateError(RuntimeError):
    def __init__(self, message: str, evidence: dict[str, Any]) -> None:
        super().__init__(message)
        self.evidence = evidence


def _provider_factory(provider: str, timeout_seconds: int) -> Any:
    if provider == "mock":
        return MockLLMProvider()
    return OpenAICompatibleProvider(timeout_seconds=timeout_seconds)


def _new_workflow_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"change_{timestamp}_{uuid.uuid4().hex[:8]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> Any:
    return _read_json(path) if path.is_file() else None
