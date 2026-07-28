"""File-backed bounded workflow for Bullet Hell config verification."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock, Thread
from typing import Any, Callable
import hashlib
import json
import subprocess
import uuid

from gameconfig_agent.bullet_hell import (
    BulletHellContract,
    apply_repair,
    build_config_diff,
    choose_repair_action,
    evaluate_bullet_hell_telemetry,
    load_bullet_hell_contract,
    propose_mock_change,
    validate_bullet_hell_contract,
    write_json,
)
from gameconfig_agent.env_loader import load_dotenv
from gameconfig_agent.providers import OpenAICompatibleProvider


TelemetryRunner = Callable[[dict[str, Any], Path, int], dict[str, Any]]
ProviderFactory = Callable[[int], Any]
FINAL_STATUSES = {"evidence_ready", "budget_exhausted", "blocked", "failed", "accepted", "revision_requested", "rolled_back"}


class BulletHellWorkflowService:
    def __init__(
        self,
        *,
        repository_root: Path,
        workflows_dir: Path,
        unity_executable: Path | None = None,
        telemetry_runner: TelemetryRunner | None = None,
        provider_factory: ProviderFactory | None = None,
    ) -> None:
        self.repository_root = repository_root
        self.workflows_dir = workflows_dir
        self.unity_executable = unity_executable or (
            repository_root / "game-unity" / "Builds" / "BulletHellWindows" / "BulletHellDemo.exe"
        )
        self.baseline_path = repository_root / "configs" / "bullet-hell" / "baseline.json"
        self.telemetry_runner = telemetry_runner or self._run_unity
        self.provider_factory = provider_factory or self._provider
        self._lock = RLock()

    def capabilities(self) -> dict[str, Any]:
        return {
            "contract_version": "1.0",
            "patterns": ["ring", "aimed_fan", "spiral", "petal"],
            "max_phases": 3,
            "max_alive_bullets": 350,
            "max_unity_runs": 3,
            "max_model_calls": 4,
            "automation_boundary": "isolated_validation_with_final_human_decision",
            "repair_actions": [
                "REDUCE_BULLETS_PER_WAVE",
                "INCREASE_WAVE_INTERVAL",
                "REDUCE_BULLET_SPEED",
                "REDUCE_BULLET_LIFETIME",
                "REDUCE_PATTERN_LAYERS",
                "PRESERVE_VISUAL_STYLE",
                "REQUEST_HUMAN",
                "STOP",
            ],
            "evidence_scope": "固定种子与固定轨迹结果，不代表所有玩家体验或完整可玩性。",
        }

    def create(
        self,
        *,
        requirement_text: str,
        provider: str = "mock",
        timeout_seconds: int = 60,
    ) -> dict[str, Any]:
        if provider not in {"mock", "openai_compatible"}:
            raise ValueError(f"Unsupported provider: {provider}")
        requirement = requirement_text.strip()
        if not requirement:
            raise ValueError("requirement_text must not be blank")
        workflow_id = f"bullet_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        directory = self.workflows_dir / workflow_id
        directory.mkdir(parents=True, exist_ok=False)
        baseline = load_bullet_hell_contract(self.baseline_path)
        model_evidence: dict[str, Any] = {"provider": provider, "model": None, "latency_ms": 0, "usage": None}
        try:
            if provider == "mock":
                candidate, goal, gate = propose_mock_change(baseline, requirement)
            else:
                candidate, goal, gate, model_evidence = self._real_candidate(
                    baseline,
                    requirement,
                    timeout_seconds,
                )
        except Exception as exc:
            gate = {
                "gate": "bullet_hell_provider",
                "decision": "blocked",
                "reason": str(exc),
                "issues": [{"error_type": type(exc).__name__, "message": str(exc)}],
                "config_only": True,
                "requires_code_change": False,
            }
            candidate, goal = deepcopy(baseline), {}
            self._save(
                directory / "badcase.json",
                {
                    "workflow_id": workflow_id,
                    "stage": "candidate_generation",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "provider": provider,
                    "model": model_evidence.get("model"),
                },
            )

        static_validation = validate_bullet_hell_contract(candidate)
        if gate["decision"] == "accepted" and not static_validation["passed"]:
            gate = {
                **gate,
                "decision": "blocked",
                "reason": "候选配置未通过 Bullet Hell Schema 或确定性安全规则。",
                "issues": static_validation["schema_errors"] + static_validation["rule_errors"],
            }
        now = _utc_now()
        manifest = {
            "workflow_id": workflow_id,
            "provider": provider,
            "model": model_evidence.get("model"),
            "status": "awaiting_authorization" if gate["decision"] == "accepted" else gate["decision"],
            "created_at": now,
            "updated_at": now,
            "authorization": None,
            "budget": {"max_unity_runs": 3, "max_model_calls": 4, "unity_runs_used": 0, "model_calls_used": 1 if provider == "openai_compatible" else 0},
            "current_iteration": 0,
            "final_decision": None,
            "error": None,
            "timeline": [],
        }
        self._event(manifest, "Requirement structured", "completed", {"provider": provider})
        self._event(manifest, "Bullet Hell Feasibility Gate", gate["decision"], {"reason": gate["reason"]})
        self._save(directory / "requirement.json", {"requirement_text": requirement})
        self._save(directory / "structured_goal.json", goal)
        self._save(directory / "baseline_config.json", baseline)
        self._save(directory / "candidate_config.json", candidate)
        self._save(directory / "candidate_history.json", [{"iteration": 0, "source": "initial_proposal", "config": candidate}])
        self._save(directory / "config_diff.json", build_config_diff(baseline, candidate))
        self._save(directory / "validation_results.json", static_validation)
        self._save(directory / "feasibility_gate.json", gate)
        self._save(directory / "model_evidence.json", model_evidence)
        self._save(directory / "repair_history.json", [])
        self._write_manifest(directory, manifest)
        return self.get(workflow_id)

    def authorize(self, workflow_id: str, *, actor: str, note: str = "") -> dict[str, Any]:
        directory, manifest = self._load(workflow_id)
        if manifest["status"] != "awaiting_authorization":
            raise ValueError(f"Workflow cannot be authorized from status {manifest['status']!r}.")
        if not actor.strip():
            raise ValueError("actor must not be blank")
        manifest["authorization"] = {
            "actor": actor.strip(),
            "note": note.strip(),
            "authorized_at": _utc_now(),
            "scope": "candidate_json_only",
            "max_unity_runs": manifest["budget"]["max_unity_runs"],
        }
        manifest["status"] = "authorized"
        self._event(manifest, "Isolated test budget authorized", "completed", {"actor": actor.strip()})
        self._write_manifest(directory, manifest)
        return self.get(workflow_id)

    def start(self, workflow_id: str) -> dict[str, Any]:
        directory, manifest = self._load(workflow_id)
        if manifest["status"] != "authorized":
            raise ValueError(f"Workflow cannot run from status {manifest['status']!r}.")
        manifest["status"] = "running_baseline"
        self._event(manifest, "Baseline Unity run", "running", {})
        self._write_manifest(directory, manifest)
        Thread(target=self._execute, args=(workflow_id,), daemon=True).start()
        return self.get(workflow_id)

    def decide(self, workflow_id: str, *, decision: str, actor: str, note: str) -> dict[str, Any]:
        directory, manifest = self._load(workflow_id)
        if decision not in {"accept", "revise", "rollback"}:
            raise ValueError(f"Unsupported decision: {decision}")
        if not actor.strip() or not note.strip():
            raise ValueError("actor and note must not be blank")
        if decision == "accept" and manifest["status"] != "evidence_ready":
            raise ValueError("Only an evidence_ready workflow can be accepted.")
        if manifest["status"] not in FINAL_STATUSES | {"authorized"}:
            raise ValueError(f"Workflow cannot be decided from status {manifest['status']!r}.")
        status = {"accept": "accepted", "revise": "revision_requested", "rollback": "rolled_back"}[decision]
        manifest["status"] = status
        manifest["final_decision"] = {
            "decision": decision,
            "actor": actor.strip(),
            "note": note.strip(),
            "decided_at": _utc_now(),
            "baseline_overwritten": False,
        }
        self._event(manifest, "Final human decision", status, {"actor": actor.strip()})
        self._write_manifest(directory, manifest)
        return self.get(workflow_id)

    def launch_manual(self, workflow_id: str) -> dict[str, Any]:
        directory, manifest = self._load(workflow_id)
        if manifest["status"] not in {"authorized", "evidence_ready", "budget_exhausted"}:
            raise ValueError(f"Manual play cannot launch from status {manifest['status']!r}.")
        if not self.unity_executable.is_file():
            raise FileNotFoundError(f"Bullet Hell Unity player not found: {self.unity_executable}")
        config_path = directory / "candidate_config.json"
        telemetry_path = directory / "manual_telemetry.json"
        log_path = directory / "manual_player.log"
        command = [
            str(self.unity_executable),
            "--bullet-hell",
            "--seed",
            "20260727",
            "--config-input",
            str(config_path),
            "--telemetry-output",
            str(telemetry_path),
            "-logFile",
            str(log_path),
        ]
        process = subprocess.Popen(command, cwd=self.unity_executable.parent)
        self._event(manifest, "Manual Unity playtest", "launched", {"process_id": process.pid})
        self._write_manifest(directory, manifest)
        return {"workflow_id": workflow_id, "process_id": process.pid, "status": "launched"}

    def get(self, workflow_id: str) -> dict[str, Any]:
        with self._lock:
            directory, manifest = self._load(workflow_id)
            response = deepcopy(manifest)
            for filename, field in (
                ("structured_goal.json", "structured_goal"),
                ("feasibility_gate.json", "feasibility_gate"),
                ("validation_results.json", "static_validation"),
                ("config_diff.json", "config_diff"),
                ("candidate_history.json", "candidate_history"),
                ("repair_history.json", "repair_history"),
                ("baseline_telemetry.json", "baseline_telemetry"),
                ("candidate_telemetry.json", "candidate_telemetry"),
                ("comparison_report.json", "comparison_report"),
            ):
                response[field] = _read_json_if_exists(directory / filename)
            response["available_artifacts"] = [
                {"name": path.name, "size": path.stat().st_size}
                for path in sorted(directory.iterdir())
                if path.is_file() and not path.name.startswith(".")
            ]
            return response

    def latest(self) -> dict[str, Any]:
        manifests = sorted(
            self.workflows_dir.glob("*/workflow_manifest.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not manifests:
            raise FileNotFoundError("No Bullet Hell workflow evidence is available.")
        return self.get(manifests[0].parent.name)

    def artifact(self, workflow_id: str, name: str) -> Path:
        directory, _ = self._load(workflow_id)
        allowed = {
            "requirement.json", "structured_goal.json", "baseline_config.json", "candidate_config.json",
            "candidate_history.json", "config_diff.json", "validation_results.json", "baseline_telemetry.json",
            "candidate_telemetry.json", "comparison_report.json", "repair_history.json", "workflow_manifest.json",
            "feasibility_gate.json", "model_evidence.json", "badcase.json", "baseline_player.log",
            "candidate_player.log", "manual_telemetry.json", "manual_player.log",
        }
        if name not in allowed:
            raise ValueError(f"Unsupported artifact: {name}")
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def _execute(self, workflow_id: str) -> None:
        directory, manifest = self._load(workflow_id)
        try:
            baseline = _read_json(directory / "baseline_config.json")
            baseline_telemetry = self.telemetry_runner(baseline, directory / "baseline", 20260727)
            self._save(directory / "baseline_telemetry.json", baseline_telemetry)
            self._event(manifest, "Baseline Unity run", "completed", {"seed": 20260727})

            candidate = _read_json(directory / "candidate_config.json")
            history = _read_json(directory / "candidate_history.json")
            repairs = _read_json(directory / "repair_history.json")
            previous_score: tuple[int, float, float] | None = None
            stagnant_rounds = 0
            max_runs = manifest["budget"]["max_unity_runs"]
            for iteration in range(1, max_runs + 1):
                manifest["status"] = "running_candidate"
                manifest["current_iteration"] = iteration
                self._event(manifest, "Candidate Unity run", "running", {"iteration": iteration})
                self._write_manifest(directory, manifest)

                validation = validate_bullet_hell_contract(candidate)
                self._save(directory / "validation_results.json", validation)
                if not validation["passed"]:
                    manifest["status"] = "blocked"
                    manifest["error"] = {
                        "stage": "candidate_validation",
                        "type": "ValidationError",
                        "message": "Repaired candidate failed deterministic validation.",
                    }
                    break

                telemetry = self.telemetry_runner(candidate, directory / f"candidate_{iteration}", 20260727)
                manifest["budget"]["unity_runs_used"] = iteration
                self._save(directory / "candidate_telemetry.json", telemetry)
                evaluation = evaluate_bullet_hell_telemetry(candidate, telemetry)
                comparison = _comparison(baseline, candidate, baseline_telemetry, telemetry, evaluation, iteration)
                self._save(directory / "comparison_report.json", comparison)
                history.append({"iteration": iteration, "source": "unity_evidence", "config": deepcopy(candidate), "evaluation": evaluation})
                self._save(directory / "candidate_history.json", history)
                self._event(manifest, "Candidate Unity run", "completed", {"iteration": iteration, "passed": evaluation["passed"]})

                if evaluation["passed"]:
                    manifest["status"] = "evidence_ready"
                    self._event(manifest, "Evidence review", "passed", {"iteration": iteration})
                    break

                score = _score(evaluation)
                stagnant_rounds = stagnant_rounds + 1 if previous_score is not None and score >= previous_score else 0
                previous_score = score
                if iteration >= max_runs or stagnant_rounds >= 2:
                    manifest["status"] = "budget_exhausted"
                    self._event(manifest, "Repair budget", "exhausted", {"iteration": iteration})
                    break

                manifest["status"] = "repairing"
                action = choose_repair_action(evaluation)
                repaired, repair_evidence = apply_repair(candidate, action, evaluation)
                repairs.append({"iteration": iteration, **repair_evidence})
                self._save(directory / "repair_history.json", repairs)
                self._event(manifest, "Bounded repair policy", action, {"iteration": iteration, "applied": repair_evidence["applied"]})
                if not repair_evidence["applied"]:
                    manifest["status"] = "budget_exhausted"
                    break
                candidate = repaired
                self._save(directory / "candidate_config.json", candidate)
                self._save(directory / "config_diff.json", build_config_diff(baseline, candidate))
            self._write_manifest(directory, manifest)
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = {"stage": manifest["status"], "type": type(exc).__name__, "message": str(exc)}
            self._event(manifest, "Workflow execution", "failed", manifest["error"])
            self._save(
                directory / "badcase.json",
                {
                    "workflow_id": workflow_id,
                    "stage": "unity_or_evaluation",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "provider": manifest["provider"],
                    "model": manifest.get("model"),
                },
            )
            self._write_manifest(directory, manifest)

    def _run_unity(self, contract: dict[str, Any], run_dir: Path, seed: int) -> dict[str, Any]:
        if not self.unity_executable.is_file():
            raise FileNotFoundError(
                f"Bullet Hell Unity player not found: {self.unity_executable}. "
                "Run scripts/smoke-bullet-hell.ps1 first."
            )
        run_dir.mkdir(parents=True, exist_ok=True)
        config_path = run_dir / "config.json"
        telemetry_path = run_dir / "telemetry.json"
        log_path = run_dir / "player.log"
        self._save(config_path, contract)
        command = [
            str(self.unity_executable),
            "-batchmode",
            "-nographics",
            "--bullet-hell",
            "--auto-run",
            "--seed",
            str(seed),
            "--config-input",
            str(config_path),
            "--telemetry-output",
            str(telemetry_path),
            "-logFile",
            str(log_path),
        ]
        result = subprocess.run(command, cwd=self.unity_executable.parent, timeout=90, check=False)
        if not telemetry_path.is_file():
            raise RuntimeError(
                f"Bullet Hell Unity player exited with code {result.returncode} "
                f"without telemetry. See {log_path}"
            )
        telemetry = _read_json(telemetry_path)
        if result.returncode != 0 and telemetry.get("status") not in {"failed", "completed"}:
            raise RuntimeError(
                f"Bullet Hell Unity player exited with code {result.returncode} "
                f"and unusable telemetry status {telemetry.get('status')!r}. See {log_path}"
            )
        return telemetry

    def _real_candidate(
        self,
        baseline: dict[str, Any],
        requirement: str,
        timeout_seconds: int,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        load_dotenv(self.repository_root / ".env")
        provider = self.provider_factory(timeout_seconds)
        system = (
            "You propose a candidate for Bullet Hell contract 1.0. Return one JSON object with "
            "structured_goal and candidate_config. Preserve every unspecified field. Never add fields. "
            "Allowed patterns: ring, aimed_fan, spiral, petal. Hard limits: bullets_per_wave 1..64, "
            "wave_interval_ms 100..5000, bullet_speed 0.5..12, lifetime 0.5..12, max_alive_bullets <=350."
        )
        user = json.dumps({"requirement": requirement, "baseline": baseline}, ensure_ascii=False)
        response = provider.complete_json(
            prompt_name="bullet_hell_candidate",
            system_prompt=system,
            user_prompt=user,
        )
        payload = json.loads(response.content)
        candidate = BulletHellContract.model_validate(payload["candidate_config"]).model_dump(mode="json")
        goal = payload.get("structured_goal") or {"source_text": requirement}
        gate = {
            "gate": "bullet_hell_feasibility",
            "decision": "accepted",
            "reason": "真实 Provider 候选已解析，等待确定性校验。",
            "issues": [],
            "config_only": True,
            "requires_code_change": False,
        }
        evidence = {
            "provider": "openai_compatible",
            "model": getattr(provider, "model", None),
            "latency_ms": response.latency_ms,
            "usage": response.usage,
            "token_estimate": response.token_estimate,
        }
        return candidate, goal, gate, evidence

    def _provider(self, timeout_seconds: int) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(timeout_seconds=timeout_seconds)

    def _load(self, workflow_id: str) -> tuple[Path, dict[str, Any]]:
        with self._lock:
            directory = self.workflows_dir / workflow_id
            path = directory / "workflow_manifest.json"
            if not path.is_file():
                raise KeyError(f"Unknown Bullet Hell workflow: {workflow_id}")
            return directory, _read_json(path)

    def _write_manifest(self, directory: Path, manifest: dict[str, Any]) -> None:
        manifest["updated_at"] = _utc_now()
        self._save(directory / "workflow_manifest.json", manifest)

    def _save(self, path: Path, value: Any) -> None:
        with self._lock:
            write_json(path, value)

    @staticmethod
    def _event(manifest: dict[str, Any], step: str, status: str, detail: dict[str, Any]) -> None:
        manifest["timeline"].append({"step": step, "status": status, "timestamp": _utc_now(), "detail": detail})


def _comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    evaluation: dict[str, Any],
    iteration: int,
) -> dict[str, Any]:
    metrics = []
    targets = candidate["runtime_targets"]
    for metric, target in (
        ("peak_alive_bullets", f"<= {targets['max_alive_bullets']}"),
        ("player_hits", f"<= {targets['max_player_hits']}"),
        ("player_survival_seconds", f">= {targets['min_survival_seconds']}"),
        ("low_percentile_fps", f">= {targets['min_fps']}"),
    ):
        check_id = {
            "peak_alive_bullets": "peak_alive_bullets",
            "player_hits": "player_hits",
            "player_survival_seconds": "survival_time",
            "low_percentile_fps": "low_percentile_fps",
        }[metric]
        check = next(row for row in evaluation["checks"] if row["check_id"] == check_id)
        metrics.append(
            {
                "metric": metric,
                "baseline": before.get(metric),
                "candidate": after.get(metric),
                "target": target,
                "passed": check["passed"],
                "evidence": check["evidence"],
            }
        )
    return {
        "iteration": iteration,
        "passed": evaluation["passed"],
        "config_change_count": len(build_config_diff(baseline, candidate)),
        "metrics": metrics,
        "evaluation": evaluation,
        "evidence_scope": evaluation["evidence_scope"],
    }


def _score(evaluation: dict[str, Any]) -> tuple[int, float, float]:
    failed = [row for row in evaluation["checks"] if not row["passed"]]
    peak = next((float(row["actual"]) for row in failed if row["check_id"] == "peak_alive_bullets" and row["actual"] is not None), 0)
    hits = next((float(row["actual"]) for row in failed if row["check_id"] == "player_hits" and row["actual"] is not None), 0)
    return len(failed), peak, hits


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_json_if_exists(path: Path) -> Any:
    return _read_json(path) if path.is_file() else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
