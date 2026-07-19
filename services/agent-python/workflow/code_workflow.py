"""File-backed workflow for reviewing and validating human-authored Unity C# diffs."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import json
import os
import subprocess
import uuid

from agent_service.agents.dual_agent import run_dual_agent
from agent_service.schemas import LLMConfig, ReviewRequest
from gameconfig_agent.env_loader import load_dotenv
from workflow.code_patch import apply_csharp_patch, copy_unity_source, hash_files, inspect_csharp_patch


ValidationLauncher = Callable[[Path, Path], int]
ProcessChecker = Callable[[int], bool]
TERMINAL_STATUSES = {"accepted", "revision_requested", "rolled_back", "rejected"}


class CodeWorkflowService:
    def __init__(
        self,
        *,
        repository_root: Path,
        workflows_dir: Path,
        validation_launcher: ValidationLauncher | None = None,
        process_checker: ProcessChecker | None = None,
    ) -> None:
        self.repository_root = repository_root
        self.workflows_dir = workflows_dir
        self.validation_launcher = validation_launcher or self._launch_validation
        self.process_checker = process_checker or _process_is_running

    def create(
        self,
        *,
        title: str,
        change_reason: str,
        diff_text: str,
        provider: str = "mock",
        timeout_seconds: int = 60,
    ) -> dict[str, Any]:
        title = title.strip()
        change_reason = change_reason.strip()
        if not title or not change_reason or not diff_text.strip():
            raise ValueError("title, change_reason, and diff_text must not be blank.")
        if provider not in {"mock", "openai_compatible"}:
            raise ValueError(f"Unsupported provider: {provider}")

        workflow_id = _new_workflow_id()
        workflow_dir = self.workflows_dir / workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=False)
        (workflow_dir / "candidate.patch").write_text(diff_text, encoding="utf-8")
        (workflow_dir / "change_reason.txt").write_text(change_reason, encoding="utf-8")
        now = _utc_now()
        manifest: dict[str, Any] = {
            "workflow_id": workflow_id,
            "title": title,
            "provider": provider,
            "model": None,
            "status": "reviewing",
            "created_at": now,
            "updated_at": now,
            "approval": None,
            "validation_process_id": None,
            "final_decision": None,
            "error": None,
            "timeline": [],
        }
        self._event(manifest, "Human C# diff submitted", "completed", {"provider": provider})
        self._write_manifest(workflow_dir, manifest)

        gate = inspect_csharp_patch(diff_text, self.repository_root)
        _write_json(workflow_dir / "patch_safety_gate.json", gate)
        manifest["patch_sha256"] = gate["patch_sha256"]
        self._event(
            manifest,
            "Patch Safety Gate",
            "completed" if gate["passed"] else "rejected",
            {"error_count": len(gate["errors"]), "changed_line_count": gate["changed_line_count"]},
        )
        if not gate["passed"]:
            manifest["status"] = "rejected"
            self._write_manifest(workflow_dir, manifest)
            return self.get(workflow_id)

        try:
            request = self._review_request(diff_text, provider, timeout_seconds)
            review = run_dual_agent(request)
            review_payload = review.model_dump()
            _write_json(workflow_dir / "quality_review.json", review_payload)
            (workflow_dir / "quality_review_report.md").write_text(
                review.report_markdown,
                encoding="utf-8",
            )
            manifest["model"] = next(
                (run.model for run in review.agent_runs if run.model),
                None,
            )
            critical_count = sum(1 for finding in review.findings if finding.severity == "critical")
            high_count = sum(1 for finding in review.findings if finding.severity == "high")
            review_passed = not review.validation_errors and critical_count == 0
            manifest["status"] = "proposed" if review_passed else "rejected"
            self._event(
                manifest,
                "Quality Review Agent",
                "completed" if review_passed else "rejected",
                {
                    "finding_count": len(review.findings),
                    "high_count": high_count,
                    "critical_count": critical_count,
                    "validation_error_count": len(review.validation_errors),
                },
            )
        except Exception as exc:  # noqa: BLE001 - workflow failures are persisted as evidence
            manifest["status"] = "failed"
            manifest["error"] = {"type": type(exc).__name__, "message": str(exc)}
            self._event(manifest, "C# quality review", "failed", manifest["error"])
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def approve(self, workflow_id: str, *, approver: str, note: str = "") -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        approver = approver.strip()
        note = note.strip()
        if not approver:
            raise ValueError("approver must not be blank.")
        if manifest["status"] != "proposed":
            raise ValueError(f"Code workflow cannot be approved from status {manifest['status']!r}.")
        review = _read_json(workflow_dir / "quality_review.json")
        high_findings = [item for item in review["findings"] if item["severity"] == "high"]
        if high_findings and not note:
            raise ValueError("Approval note is required when high-severity findings remain.")
        manifest["approval"] = {
            "approver": approver,
            "note": note,
            "approved_at": _utc_now(),
        }
        manifest["status"] = "approved"
        self._event(manifest, "Human approval", "completed", {"approver": approver})
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def prepare_workspace(self, workflow_id: str) -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        if manifest["status"] != "approved":
            raise ValueError(f"Workspace cannot be prepared from status {manifest['status']!r}.")
        diff_text = (workflow_dir / "candidate.patch").read_text(encoding="utf-8")
        gate = inspect_csharp_patch(diff_text, self.repository_root)
        if not gate["passed"] or gate["patch_sha256"] != manifest["patch_sha256"]:
            raise ValueError("Patch changed after review or no longer passes the safety gate.")

        workspace_root = workflow_dir / "workspace"
        changed_paths = [file["new_path"] for file in gate["parsed_diff"]["files"]]
        baseline_hashes = hash_files(self.repository_root, changed_paths)
        copy_unity_source(self.repository_root, workspace_root)
        applied_paths = apply_csharp_patch(diff_text, workspace_root)
        patched_hashes = hash_files(workspace_root, applied_paths)
        evidence = {
            "workspace": str(workspace_root),
            "changed_paths": applied_paths,
            "baseline_hashes": baseline_hashes,
            "patched_hashes": patched_hashes,
            "baseline_unchanged": hash_files(self.repository_root, applied_paths) == baseline_hashes,
        }
        _write_json(workflow_dir / "isolated_apply.json", evidence)
        manifest["status"] = "workspace_prepared"
        self._event(
            manifest,
            "Isolated patch apply",
            "completed",
            {"changed_paths": applied_paths, "baseline_unchanged": evidence["baseline_unchanged"]},
        )
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def start_validation(self, workflow_id: str) -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        if manifest["status"] != "workspace_prepared":
            raise ValueError(f"Validation cannot start from status {manifest['status']!r}.")
        process_id = self.validation_launcher(workflow_dir, workflow_dir / "workspace")
        manifest["validation_process_id"] = process_id
        manifest["status"] = "validation_running"
        self._event(manifest, "Unity isolated validation", "in_progress", {"process_id": process_id})
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
            raise ValueError("Accept or revise requires completed Unity validation evidence.")
        if decision == "rollback" and manifest["status"] not in {
            "approved", "workspace_prepared", "evidence_ready", "failed"
        }:
            raise ValueError(f"Code workflow cannot be rolled back from status {manifest['status']!r}.")
        status = {"accept": "accepted", "revise": "revision_requested", "rollback": "rolled_back"}[decision]
        manifest["status"] = status
        manifest["final_decision"] = {
            "decision": decision,
            "actor": actor,
            "note": note,
            "decided_at": _utc_now(),
            "patch_applied_to_repository": False,
        }
        self._event(manifest, "Human final decision", status, {"actor": actor, "note": note})
        self._write_manifest(workflow_dir, manifest)
        return self.get(workflow_id)

    def get(self, workflow_id: str) -> dict[str, Any]:
        workflow_dir, manifest = self._load(workflow_id)
        validation_result = _read_json_if_exists(workflow_dir / "validation_result.json")
        if (
            validation_result is None
            and manifest["status"] == "validation_running"
            and manifest.get("validation_process_id")
            and not self.process_checker(manifest["validation_process_id"])
        ):
            validation_result = {
                "passed": False,
                "compilation_passed": False,
                "editor_smoke_passed": False,
                "player_runs_passed": False,
                "repeatability_passed": False,
                "repeatability_rate": None,
                "runtime_target_pass_rate": None,
                "error": {
                    "type": "ValidationProcessError",
                    "message": "Unity validation process exited without writing validation_result.json.",
                },
                "completed_at": _utc_now(),
            }
            _write_json(workflow_dir / "validation_result.json", validation_result)
        if validation_result and manifest["status"] == "validation_running":
            if validation_result.get("passed"):
                manifest["status"] = "evidence_ready"
                self._event(
                    manifest,
                    "Unity validation evidence",
                    "completed",
                    {"runtime_target_pass_rate": validation_result.get("runtime_target_pass_rate")},
                )
            else:
                manifest["status"] = "failed"
                manifest["error"] = validation_result.get("error")
                self._event(manifest, "Unity validation evidence", "failed", manifest["error"] or {})
            self._write_manifest(workflow_dir, manifest)

        response = deepcopy(manifest)
        response["patch_safety_gate"] = _read_json_if_exists(workflow_dir / "patch_safety_gate.json")
        response["quality_review"] = _read_json_if_exists(workflow_dir / "quality_review.json")
        response["isolated_apply"] = _read_json_if_exists(workflow_dir / "isolated_apply.json")
        response["validation_result"] = validation_result
        response["available_artifacts"] = [
            {"name": path.name, "size": path.stat().st_size}
            for path in sorted(workflow_dir.iterdir())
            if path.is_file()
        ]
        return response

    def artifact(self, workflow_id: str, name: str) -> Path:
        allowed = {
            "candidate.patch",
            "change_reason.txt",
            "patch_safety_gate.json",
            "quality_review.json",
            "quality_review_report.md",
            "isolated_apply.json",
            "validation_result.json",
            "validation_console.log",
            "build.log",
            "player.log",
            "player_repeat.log",
            "telemetry.json",
            "telemetry_repeat.json",
            "testbed_evaluation.json",
            "testbed_evaluation_report.md",
            "code_workflow_manifest.json",
        }
        if name not in allowed:
            raise ValueError("Artifact name is not allowed.")
        workflow_dir, _ = self._load(workflow_id)
        path = workflow_dir / name
        if not path.is_file():
            raise FileNotFoundError(name)
        return path

    def _review_request(self, diff_text: str, provider: str, timeout_seconds: int) -> ReviewRequest:
        if provider == "mock":
            return ReviewRequest(diff=diff_text, language="csharp", mode="mock", workflow="dual_agent")
        load_dotenv(self.repository_root / ".env")
        config = LLMConfig(
            provider="openai_compatible",
            base_url=os.getenv("GAMECONFIG_LLM_BASE_URL"),
            api_key=os.getenv("GAMECONFIG_LLM_API_KEY"),
            model=os.getenv("GAMECONFIG_LLM_MODEL"),
            timeout_seconds=timeout_seconds,
        )
        return ReviewRequest(
            diff=diff_text,
            language="csharp",
            mode="openai_compatible",
            workflow="dual_agent",
            llm_config=config,
        )

    def _launch_validation(self, workflow_dir: Path, workspace_root: Path) -> int:
        script = self.repository_root / "scripts" / "validate-code-workflow.ps1"
        log = (workflow_dir / "validation_console.log").open("w", encoding="utf-8")
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-RepositoryRoot",
            str(self.repository_root),
            "-WorkspaceRoot",
            str(workspace_root),
            "-ArtifactDir",
            str(workflow_dir),
        ]
        process = subprocess.Popen(  # noqa: S603 - fixed local script and validated paths
            command,
            cwd=self.repository_root,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        log.close()
        return process.pid

    def _load(self, workflow_id: str) -> tuple[Path, dict[str, Any]]:
        if not workflow_id.startswith("code_") or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in workflow_id
        ):
            raise KeyError("Invalid code workflow id.")
        workflow_dir = self.workflows_dir / workflow_id
        manifest_path = workflow_dir / "code_workflow_manifest.json"
        if not manifest_path.is_file():
            raise KeyError(f"Unknown code workflow: {workflow_id}")
        return workflow_dir, _read_json(manifest_path)

    def _write_manifest(self, workflow_dir: Path, manifest: dict[str, Any]) -> None:
        manifest["updated_at"] = _utc_now()
        _write_json(workflow_dir / "code_workflow_manifest.json", manifest)

    def _event(self, manifest: dict[str, Any], step: str, status: str, detail: dict[str, Any]) -> None:
        manifest["timeline"].append(
            {"step": step, "status": status, "timestamp": _utc_now(), "detail": detail}
        )


def _new_workflow_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"code_{timestamp}_{uuid.uuid4().hex[:8]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_json_if_exists(path: Path) -> Any:
    return _read_json(path) if path.is_file() else None


def _process_is_running(process_id: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(process_id, 0)
            return True
        except OSError:
            return False
    import ctypes

    process_query_limited_information = 0x1000
    still_active = 259
    handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, process_id)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        return bool(ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and exit_code.value == still_active
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
