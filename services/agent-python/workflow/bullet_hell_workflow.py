"""File-backed bounded workflow for Bullet Hell config verification."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock, Thread
from typing import Any, Callable
import hashlib
import json
import uuid

from gameconfig_agent.bullet_hell import (
    apply_repair,
    build_config_diff,
    evaluate_bullet_hell_telemetry,
    load_bullet_hell_contract,
    validate_bullet_hell_contract,
    validate_bullet_hell_proposal,
    write_json,
)
from gameconfig_agent.agents.bullet_hell_agents import (
    BulletHellAgentError,
    QualityReviewAgent,
    RequirementAgent,
)
from gameconfig_agent.providers import OpenAICompatibleProvider
from workflow.engines import EngineRunner, UnityEngineRunner, UnrealEngineRunner


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
        engine_runners: dict[str, EngineRunner] | None = None,
    ) -> None:
        self.repository_root = repository_root
        self.workflows_dir = workflows_dir
        self.unity_executable = unity_executable or (
            repository_root / "game-unity" / "Builds" / "BulletHellWindows" / "BulletHellDemo.exe"
        )
        self.baseline_path = repository_root / "configs" / "bullet-hell" / "baseline.json"
        self.telemetry_runner = telemetry_runner
        self.provider_factory = provider_factory or self._provider
        self.engine_runners = engine_runners or {
            "unity": UnityEngineRunner(
                repository_root=repository_root,
                executable=self.unity_executable,
            ),
            "unreal": UnrealEngineRunner(repository_root=repository_root),
        }
        self.requirement_agent = RequirementAgent(repository_root, self.provider_factory)
        self.quality_review_agent = QualityReviewAgent(repository_root, self.provider_factory)
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
            "default_engine": "unity",
            "engines": {
                name: runner.capabilities()
                for name, runner in self.engine_runners.items()
            },
        }

    def create(
        self,
        *,
        requirement_text: str,
        provider: str = "mock",
        timeout_seconds: int = 60,
        engine: str = "unity",
    ) -> dict[str, Any]:
        if provider not in {"mock", "openai_compatible"}:
            raise ValueError(f"Unsupported provider: {provider}")
        if engine not in self.engine_runners:
            raise ValueError(f"Unsupported engine: {engine}")
        requirement = requirement_text.strip()
        if not requirement:
            raise ValueError("requirement_text must not be blank")
        workflow_id = f"bullet_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        directory = self.workflows_dir / workflow_id
        directory.mkdir(parents=True, exist_ok=False)
        baseline = load_bullet_hell_contract(self.baseline_path)
        model_evidence: dict[str, Any] = {"provider": provider, "model": None, "latency_ms": 0, "usage": None}
        agent_runs: list[dict[str, Any]] = []
        badcases: list[dict[str, Any]] = []
        try:
            candidate, goal, gate, requirement_run = self.requirement_agent.run(
                baseline=baseline,
                requirement=requirement,
                provider_name=provider,
                timeout_seconds=timeout_seconds,
            )
            agent_runs.append(requirement_run)
            model_evidence = _legacy_model_evidence(requirement_run)
        except BulletHellAgentError as exc:
            agent_runs.append(exc.evidence)
            model_evidence = _legacy_model_evidence(exc.evidence)
            badcase = {
                "workflow_id": workflow_id,
                "stage": exc.stage,
                "error_type": exc.evidence.get("error_type", type(exc).__name__),
                "error_message": str(exc),
                "raw_model_output": exc.raw_output,
                "provider": provider,
                "model": exc.evidence.get("model"),
            }
            badcases.append(badcase)
            gate = {
                "gate": "bullet_hell_provider",
                "decision": "blocked",
                "reason": str(exc),
                "issues": [{"error_type": badcase["error_type"], "message": str(exc)}],
                "config_only": True,
                "requires_code_change": False,
            }
            candidate, goal = deepcopy(baseline), {}
            self._save(directory / "badcase.json", badcase)
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
            badcase = {
                "workflow_id": workflow_id,
                "stage": "requirement_agent",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "raw_model_output": None,
                "provider": provider,
                "model": model_evidence.get("model"),
            }
            badcases.append(badcase)
            self._save(directory / "badcase.json", badcase)

        static_validation = (
            validate_bullet_hell_proposal(
                baseline=baseline,
                candidate=candidate,
                structured_goal=goal,
            )
            if gate["decision"] == "accepted"
            else validate_bullet_hell_contract(candidate)
        )
        if gate["decision"] == "accepted" and not static_validation["passed"]:
            gate = {
                **gate,
                "decision": "blocked",
                "reason": "候选配置未通过 Schema、引用、规则引擎或安全门。",
                "issues": (
                    static_validation["schema_errors"]
                    + static_validation.get("reference_errors", [])
                    + static_validation["rule_errors"]
                    + static_validation.get("safety_errors", [])
                ),
            }
        now = _utc_now()
        manifest = {
            "workflow_id": workflow_id,
            "provider": provider,
            "model": model_evidence.get("model"),
            "engine": engine,
            "timeout_seconds": timeout_seconds,
            "status": "awaiting_authorization" if gate["decision"] == "accepted" else gate["decision"],
            "created_at": now,
            "updated_at": now,
            "authorization": None,
            "budget": {
                "max_unity_runs": 3,
                "max_model_calls": 4,
                "unity_runs_used": 0,
                "model_calls_used": sum(1 for run in agent_runs if run.get("model_call")),
            },
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
        self._save(directory / "agent_runs.json", agent_runs)
        self._save(directory / "quality_reviews.json", [])
        self._save(directory / "badcases.json", badcases)
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
        if self.telemetry_runner is None:
            environment = self.engine_runners[manifest.get("engine", "unity")].validate_environment()
            if environment["status"] not in {"available", "verified"}:
                raise ValueError(
                    f"Engine {manifest.get('engine', 'unity')!r} cannot run: {environment['reason']}"
                )
        manifest["status"] = "running_baseline"
        self._event(manifest, "Baseline engine run", "running", {"engine": manifest.get("engine", "unity")})
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

    def generate_visual_comparison(self, workflow_id: str) -> dict[str, Any]:
        directory, manifest = self._load(workflow_id)
        allowed_statuses = {"evidence_ready", "budget_exhausted", "accepted", "revision_requested", "rolled_back"}
        if manifest["status"] not in allowed_statuses:
            raise ValueError(f"Visual comparison cannot run from status {manifest['status']!r}.")
        runner = self.engine_runners[manifest.get("engine", "unity")]
        environment = runner.validate_environment()
        if environment["status"] not in {"available", "verified"}:
            raise FileNotFoundError(environment["reason"])
        status_path = directory / "visual_comparison.json"
        current = _read_json_if_exists(status_path)
        if current and current.get("status") == "running":
            return self.get(workflow_id)
        self._save(
            status_path,
            {
                "status": "running",
                "random_seed": 20260727,
                "fixed_trajectory": True,
                "capture_times_seconds": [10, 20, 30],
                "started_at": _utc_now(),
                "variants": {},
                "error": None,
            },
        )
        Thread(target=self._execute_visual_comparison, args=(workflow_id,), daemon=True).start()
        return self.get(workflow_id)

    def launch_manual(self, workflow_id: str, *, variant: str = "candidate") -> dict[str, Any]:
        directory, manifest = self._load(workflow_id)
        allowed_statuses = {
            "authorized", "evidence_ready", "budget_exhausted",
            "accepted", "revision_requested", "rolled_back",
        }
        if manifest["status"] not in allowed_statuses:
            raise ValueError(f"Manual play cannot launch from status {manifest['status']!r}.")
        if variant not in {"baseline", "candidate"}:
            raise ValueError(f"Unsupported manual play variant: {variant!r}.")
        runner = self.engine_runners[manifest.get("engine", "unity")]
        environment = runner.validate_environment()
        if environment["status"] not in {"available", "verified"}:
            raise FileNotFoundError(environment["reason"])
        config_path = directory / f"{variant}_config.json"
        telemetry_path = directory / f"manual_{variant}_telemetry.json"
        log_path = directory / f"manual_{variant}_player.log"
        launch = runner.manual_play(
            config_path=config_path,
            telemetry_path=telemetry_path,
            log_path=log_path,
            seed=20260727,
            run_id=workflow_id,
            variant=variant,
        )
        self._event(
            manifest,
            "Manual engine playtest",
            "launched",
            {
                "process_id": launch["process_id"],
                "variant": variant,
                "engine": manifest.get("engine", "unity"),
            },
        )
        self._write_manifest(directory, manifest)
        return launch

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
                ("agent_runs.json", "agent_runs"),
                ("quality_reviews.json", "quality_reviews"),
                ("badcases.json", "badcases"),
                ("baseline_telemetry.json", "baseline_telemetry"),
                ("candidate_telemetry.json", "candidate_telemetry"),
                ("baseline_engine_evidence.json", "baseline_engine_evidence"),
                ("candidate_engine_evidence.json", "candidate_engine_evidence"),
                ("comparison_report.json", "comparison_report"),
                ("visual_comparison.json", "visual_comparison"),
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
            "baseline_engine_evidence.json", "candidate_engine_evidence.json",
            "feasibility_gate.json", "model_evidence.json", "badcase.json", "baseline_player.log",
            "agent_runs.json", "quality_reviews.json", "badcases.json",
            "candidate_player.log", "manual_telemetry.json", "manual_player.log",
            "manual_baseline_telemetry.json", "manual_candidate_telemetry.json",
            "manual_baseline_player.log", "manual_candidate_player.log", "visual_comparison.json",
        }
        if name not in allowed:
            raise ValueError(f"Unsupported artifact: {name}")
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def visual_artifact(self, workflow_id: str, variant: str, name: str) -> Path:
        directory, _ = self._load(workflow_id)
        if variant not in {"baseline", "candidate"}:
            raise ValueError(f"Unsupported visual variant: {variant!r}.")
        if name not in {"capture_10s.png", "capture_20s.png", "capture_30s.png"}:
            raise ValueError(f"Unsupported visual artifact: {name!r}.")
        path = directory / "visual-comparison" / variant / name
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def _execute(self, workflow_id: str) -> None:
        directory, manifest = self._load(workflow_id)
        try:
            baseline = _read_json(directory / "baseline_config.json")
            engine = manifest.get("engine", "unity")
            baseline_telemetry = self._run_automated(
                baseline,
                directory / "baseline",
                20260727,
                workflow_id=workflow_id,
                variant="baseline",
                engine=engine,
            )
            self._save(directory / "baseline_telemetry.json", baseline_telemetry)
            self._event(manifest, "Baseline engine run", "completed", {"seed": 20260727, "engine": engine})

            candidate = _read_json(directory / "candidate_config.json")
            history = _read_json(directory / "candidate_history.json")
            repairs = _read_json(directory / "repair_history.json")
            agent_runs = _read_json(directory / "agent_runs.json")
            quality_reviews = _read_json(directory / "quality_reviews.json")
            badcases = _read_json(directory / "badcases.json")
            requirement = _read_json(directory / "requirement.json")["requirement_text"]
            structured_goal = _read_json(directory / "structured_goal.json")
            previous_score: tuple[int, float, float] | None = None
            stagnant_rounds = 0
            max_runs = manifest["budget"]["max_unity_runs"]
            for iteration in range(1, max_runs + 1):
                manifest["status"] = "running_candidate"
                manifest["current_iteration"] = iteration
                self._event(manifest, "Candidate engine run", "running", {"iteration": iteration, "engine": engine})
                self._write_manifest(directory, manifest)

                validation = validate_bullet_hell_proposal(
                    baseline=baseline,
                    candidate=candidate,
                    structured_goal=structured_goal,
                )
                self._save(directory / "validation_results.json", validation)
                if not validation["passed"]:
                    manifest["status"] = "blocked"
                    manifest["error"] = {
                        "stage": "candidate_validation",
                        "type": "ValidationError",
                        "message": "Repaired candidate failed deterministic validation.",
                    }
                    break

                telemetry = self._run_automated(
                    candidate,
                    directory / f"candidate_{iteration}",
                    20260727,
                    workflow_id=workflow_id,
                    variant=f"candidate_{iteration}",
                    engine=engine,
                )
                manifest["budget"]["unity_runs_used"] = iteration
                self._save(directory / "candidate_telemetry.json", telemetry)
                evaluation = evaluate_bullet_hell_telemetry(candidate, telemetry)
                comparison = _comparison(baseline, candidate, baseline_telemetry, telemetry, evaluation, iteration)
                self._save(directory / "comparison_report.json", comparison)
                history.append({"iteration": iteration, "source": "unity_evidence", "config": deepcopy(candidate), "evaluation": evaluation})
                self._save(directory / "candidate_history.json", history)
                self._event(
                    manifest,
                    "Candidate engine run",
                    "completed",
                    {"iteration": iteration, "passed": evaluation["passed"], "engine": engine},
                )

                try:
                    review, review_run = self.quality_review_agent.review(
                        requirement=requirement,
                        structured_goal=structured_goal,
                        config_diff=build_config_diff(baseline, candidate),
                        evaluation=evaluation,
                        repair_history=repairs,
                        provider_name=manifest["provider"],
                        timeout_seconds=int(manifest.get("timeout_seconds", 60)),
                        iteration=iteration,
                    )
                    agent_runs.append(review_run)
                    quality_reviews.append(review)
                    if review_run.get("model_call"):
                        manifest["budget"]["model_calls_used"] += 1
                    self._save(directory / "agent_runs.json", agent_runs)
                    self._save(directory / "quality_reviews.json", quality_reviews)
                except BulletHellAgentError as exc:
                    agent_runs.append(exc.evidence)
                    if exc.evidence.get("model_call"):
                        manifest["budget"]["model_calls_used"] += 1
                    badcase = {
                        "workflow_id": workflow_id,
                        "stage": exc.stage,
                        "iteration": iteration,
                        "error_type": exc.evidence.get("error_type", type(exc).__name__),
                        "error_message": str(exc),
                        "raw_model_output": exc.raw_output,
                        "provider": manifest["provider"],
                        "model": exc.evidence.get("model"),
                    }
                    badcases.append(badcase)
                    self._save(directory / "agent_runs.json", agent_runs)
                    self._save(directory / "badcases.json", badcases)
                    self._save(directory / "badcase.json", badcase)
                    manifest["status"] = "blocked"
                    manifest["error"] = {
                        "stage": exc.stage,
                        "type": badcase["error_type"],
                        "message": str(exc),
                    }
                    self._event(manifest, "Quality Review Agent", "failed", {"iteration": iteration})
                    break

                policy = review["policy_gate"]
                self._event(
                    manifest,
                    "Quality Review Agent",
                    policy["effective_decision"],
                    {
                        "iteration": iteration,
                        "recommended_action": review["agent_output"]["repair_action"],
                        "policy_gate_passed": policy["passed"],
                    },
                )
                if policy["effective_decision"] == "accept":
                    manifest["status"] = "evidence_ready"
                    break
                if policy["effective_decision"] == "human_review":
                    manifest["status"] = "blocked"
                    manifest["error"] = {
                        "stage": "quality_review_policy_gate",
                        "type": "HumanReviewRequired",
                        "message": policy["reason"],
                    }
                    break

                score = _score(evaluation)
                stagnant_rounds = stagnant_rounds + 1 if previous_score is not None and score >= previous_score else 0
                previous_score = score
                if iteration >= max_runs or stagnant_rounds >= 2:
                    manifest["status"] = "budget_exhausted"
                    self._event(manifest, "Repair budget", "exhausted", {"iteration": iteration})
                    break

                manifest["status"] = "repairing"
                action = policy["effective_action"]
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

    def _execute_visual_comparison(self, workflow_id: str) -> None:
        directory, manifest = self._load(workflow_id)
        status_path = directory / "visual_comparison.json"
        try:
            variants: dict[str, Any] = {}
            for variant in ("baseline", "candidate"):
                config_path = directory / f"{variant}_config.json"
                output_dir = directory / "visual-comparison" / variant
                result = self._run_visual_capture(
                    config_path,
                    output_dir,
                    variant,
                    20260727,
                    engine=manifest.get("engine", "unity"),
                    workflow_id=workflow_id,
                )
                result["config_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
                variants[variant] = result
            self._save(
                status_path,
                {
                    "status": "completed",
                    "random_seed": 20260727,
                    "fixed_trajectory": True,
                    "duration_seconds": variants["baseline"]["duration_seconds"],
                    "capture_times_seconds": [10, 20, 30],
                    "camera": "orthographic_fixed",
                    "generated_at": _utc_now(),
                    "variants": variants,
                    "error": None,
                },
            )
        except Exception as exc:
            self._save(
                status_path,
                {
                    "status": "failed",
                    "random_seed": 20260727,
                    "fixed_trajectory": True,
                    "capture_times_seconds": [10, 20, 30],
                    "finished_at": _utc_now(),
                    "variants": {},
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
            )

    def _run_visual_capture(
        self,
        config_path: Path,
        output_dir: Path,
        variant: str,
        seed: int,
        *,
        engine: str = "unity",
        workflow_id: str = "visual",
    ) -> dict[str, Any]:
        contract = _read_json(config_path)
        result = self.engine_runners[engine].automated_run(
            contract=contract,
            run_dir=output_dir,
            seed=seed,
            run_id=workflow_id,
            variant=variant,
            capture_times=(10, 20, 30),
        )
        telemetry_path = output_dir / "telemetry.json"
        log_path = output_dir / "player.log"
        manifest_path = output_dir / "capture_manifest.json"
        expected = [output_dir / f"capture_{second:02d}s.png" for second in (10, 20, 30)]
        missing = [path.name for path in expected if not path.is_file()]
        if missing or not manifest_path.is_file() or not telemetry_path.is_file():
            raise RuntimeError(
                f"{variant} visual capture exited with code {result.exit_code}; "
                f"missing artifacts: {missing or ['capture_manifest.json or telemetry.json']}. See {log_path}"
            )
        capture_manifest = _read_json(manifest_path)
        return {
            "variant": variant,
            "duration_seconds": capture_manifest["duration_seconds"],
            "random_seed": capture_manifest["random_seed"],
            "run_mode": capture_manifest["run_mode"],
            "fixed_trajectory": capture_manifest["fixed_trajectory"],
            "captures": capture_manifest["captures"],
            "telemetry_file": str(telemetry_path.relative_to(self.workflows_dir / config_path.parent.name)).replace("\\", "/"),
            "player_exit_code": result.exit_code,
            "engine": engine,
        }

    def _run_unity(self, contract: dict[str, Any], run_dir: Path, seed: int) -> dict[str, Any]:
        result = self.engine_runners["unity"].automated_run(
            contract=contract,
            run_dir=run_dir,
            seed=seed,
            run_id=run_dir.parent.name,
            variant=run_dir.name,
        )
        return result.telemetry

    def _run_automated(
        self,
        contract: dict[str, Any],
        run_dir: Path,
        seed: int,
        *,
        workflow_id: str,
        variant: str,
        engine: str,
    ) -> dict[str, Any]:
        if self.telemetry_runner is not None:
            telemetry = self.telemetry_runner(contract, run_dir, seed)
            normalized = {
                "engine_name": engine,
                "run_id": workflow_id,
                "seed": seed,
                "completed": telemetry.get("status") == "completed",
                "evidence_source": "injected_test_runner",
            }
        else:
            result = self.engine_runners[engine].automated_run(
                contract=contract,
                run_dir=run_dir,
                seed=seed,
                run_id=workflow_id,
                variant=variant,
            )
            telemetry = result.telemetry
            normalized = result.normalized_evidence
        evidence_name = "baseline_engine_evidence.json" if variant == "baseline" else "candidate_engine_evidence.json"
        self._save(run_dir.parent / evidence_name, normalized)
        return telemetry

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


def _legacy_model_evidence(agent_run: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": agent_run.get("provider"),
        "model": agent_run.get("model"),
        "latency_ms": agent_run.get("latency_ms", 0),
        "usage": agent_run.get("usage"),
        "token_estimate": agent_run.get("token_estimate"),
    }
