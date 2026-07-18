"""File-backed guided Unity validation runs for the local Web Console."""

from __future__ import annotations

import json
import os
import hashlib
import subprocess
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from gameconfig_agent.cli import run_phase0_demo
from gameconfig_agent.data.classic_cases import load_classic_case
from gameconfig_agent.runtime_contract import DEFAULT_RUNTIME_SCENARIO, build_runtime_contract, has_starter_trial_runtime_configs
from gameconfig_agent.runtime_evaluation import evaluate_runtime_files
from gameconfig_agent.tools.reference_checker import ReferenceCheckerTool
from gameconfig_agent.tools.rule_engine import RuleEngineTool
from gameconfig_agent.tools.schema_validator import SchemaValidatorTool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_RUNS_DIR = PROJECT_ROOT / "outputs" / "runtime_runs"
UNITY_EXECUTABLE = PROJECT_ROOT / "unity" / "GameConfigRuntimeDemo" / "Builds" / "Windows" / "GameConfigRuntimeDemo.exe"
GUIDED_RUNTIME_MARKER = "guided-runtime-v1"
STATIC_ONLY_CASES = {"case_04_missing_reference"}

Launcher = Callable[[list[str], Path], int]
ProcessChecker = Callable[[int], bool]


class RuntimeRunService:
    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        runs_dir: Path | None = None,
        unity_executable: Path | None = None,
        launcher: Launcher | None = None,
        process_checker: ProcessChecker | None = None,
    ) -> None:
        self.project_root = project_root
        self.runs_dir = runs_dir or project_root / "outputs" / "runtime_runs"
        self.unity_executable = unity_executable or project_root / "unity" / "GameConfigRuntimeDemo" / "Builds" / "Windows" / "GameConfigRuntimeDemo.exe"
        self.launcher = launcher or _launch_process
        self.process_checker = process_checker or _process_is_running

    def prepare(
        self,
        *,
        case_id: str,
        requirement_text: str,
        provider: str = "mock",
        structured_requirement: dict[str, Any] | None = None,
        final_configs: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        case = load_classic_case(case_id)
        if provider not in {"mock", "openai_compatible"}:
            raise ValueError(f"Unsupported provider: {provider}")
        if case_id in STATIC_ONLY_CASES:
            raise ValueError("This classic case uses static validation evidence and does not launch Unity.")

        static_validation: dict[str, Any] | None = None
        validated_configs: dict[str, Any] | None = None
        if provider == "openai_compatible":
            if not isinstance(structured_requirement, dict) or not isinstance(final_configs, dict):
                raise ValueError("Real provider runtime handoff requires structured_requirement and final_configs.")
            schema_errors = SchemaValidatorTool().validate(structured_requirement, final_configs)
            reference_errors = ReferenceCheckerTool().check(final_configs) if not schema_errors else []
            rule_errors = RuleEngineTool().evaluate(structured_requirement, final_configs)["violations"] if not schema_errors else []
            static_validation = {
                "passed": not (schema_errors or reference_errors or rule_errors),
                "schema_errors": schema_errors,
                "reference_errors": reference_errors,
                "rule_errors": rule_errors,
            }
            validated_configs = deepcopy(final_configs)
            if not static_validation["passed"]:
                error_count = sum(len(static_validation.get(key, [])) for key in ("schema_errors", "reference_errors", "rule_errors"))
                raise ValueError(f"Final static validation failed with {error_count} errors; Unity contract was not prepared.")

        run_id = _new_run_id()
        run_dir = self.runs_dir / run_id
        pipeline_dir = run_dir / "pipeline"
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "requirement.txt").write_text(requirement_text.strip(), encoding="utf-8")

        if provider == "mock":
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
                handle.write(requirement_text)
                input_path = Path(handle.name)
            try:
                blackboard = run_phase0_demo(input_path, pipeline_dir)
            finally:
                input_path.unlink(missing_ok=True)
            static_validation = blackboard["final_validation"]
            validated_configs = deepcopy(blackboard["repaired_configs"])

        if static_validation is None or validated_configs is None:
            raise ValueError("Static validation did not produce a usable config snapshot.")
        if not static_validation["passed"]:
            error_count = sum(len(static_validation.get(key, [])) for key in ("schema_errors", "reference_errors", "rule_errors"))
            raise ValueError(f"Final static validation failed with {error_count} errors; Unity contract was not prepared.")

        _write_json(run_dir / "final_configs.json", validated_configs)
        scenario = None if has_starter_trial_runtime_configs(validated_configs) else _scenario_for_case(case)
        contract = build_runtime_contract(validated_configs, scenario)
        _write_json(run_dir / "unity_contract.json", contract)

        now = _utc_now()
        manifest = {
            "run_id": run_id,
            "case_id": case_id,
            "case_title": case["title"],
            "provider": provider,
            "model": model,
            "config_hash": hashlib.sha256(
                json.dumps(validated_configs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "status": "prepared",
            "mode": None,
            "process_id": None,
            "created_at": now,
            "updated_at": now,
            "steps": {
                "requirement": "completed",
                "static_validation": "completed",
                "unity_play": "ready",
                "runtime_evaluation": "pending",
                "improvement_suggestions": "pending",
            },
            "artifacts": _artifact_paths(run_id),
            "static_validation": static_validation,
            "error": None,
        }
        self._write_manifest(run_dir, manifest)
        return self.get(run_id)

    def launch(self, run_id: str, *, mode: str = "manual") -> dict[str, Any]:
        if mode not in {"manual", "auto"}:
            raise ValueError("mode must be 'manual' or 'auto'.")
        run_dir, manifest = self._load(run_id)
        if manifest["status"] not in {"prepared", "failed"}:
            raise ValueError(f"Run cannot be launched from status {manifest['status']!r}.")
        if not self.unity_executable.is_file():
            raise FileNotFoundError(f"Unity Runtime Demo executable was not found: {self.unity_executable}")
        marker = self.unity_executable.parent / "guided_runtime_version.txt"
        if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != GUIDED_RUNTIME_MARKER:
            raise FileNotFoundError("Unity Runtime Demo must be rebuilt with guided runtime support before launch.")

        telemetry_path = run_dir / "telemetry.json"
        telemetry_path.unlink(missing_ok=True)
        command = [
            str(self.unity_executable),
            "--config-input",
            str(run_dir / "unity_contract.json"),
            "--telemetry-output",
            str(telemetry_path),
        ]
        if mode == "auto":
            command.append("--auto-run")
        try:
            process_id = self.launcher(command, self.unity_executable.parent)
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["error"] = {"type": type(exc).__name__, "message": str(exc)}
            manifest["updated_at"] = _utc_now()
            self._write_manifest(run_dir, manifest)
            raise

        manifest.update(
            {
                "status": "launched",
                "mode": mode,
                "process_id": process_id,
                "launched_at": _utc_now(),
                "updated_at": _utc_now(),
                "error": None,
            }
        )
        manifest["steps"]["unity_play"] = "in_progress"
        self._write_manifest(run_dir, manifest)
        return self.get(run_id)

    def get(self, run_id: str) -> dict[str, Any]:
        run_dir, manifest = self._load(run_id)
        telemetry_path = run_dir / "telemetry.json"
        evaluation_path = run_dir / "runtime_evaluation.json"
        if telemetry_path.is_file() and not evaluation_path.is_file():
            self.evaluate(run_id)
            run_dir, manifest = self._load(run_id)
        elif manifest["status"] == "launched" and manifest.get("process_id") and not self.process_checker(manifest["process_id"]):
            manifest["status"] = "failed"
            manifest["error"] = {
                "type": "UnityProcessExited",
                "message": "Unity exited before telemetry was written. Run the playtest again and finish the scenario.",
            }
            manifest["updated_at"] = _utc_now()
            manifest["steps"]["unity_play"] = "failed"
            self._write_manifest(run_dir, manifest)
        return self._response(run_dir, manifest)

    def evaluate(self, run_id: str) -> dict[str, Any]:
        run_dir, manifest = self._load(run_id)
        telemetry_path = run_dir / "telemetry.json"
        if not telemetry_path.is_file():
            raise FileNotFoundError("Telemetry is not available for this run.")
        result = evaluate_runtime_files(run_dir / "unity_contract.json", telemetry_path, run_dir)
        suggestions = _improvement_suggestions(result)
        _write_json(run_dir / "improvement_suggestions.json", suggestions)
        manifest["status"] = "evaluated"
        manifest["updated_at"] = _utc_now()
        manifest["completed_at"] = _utc_now()
        manifest["steps"]["unity_play"] = "completed"
        manifest["steps"]["runtime_evaluation"] = "completed"
        manifest["steps"]["improvement_suggestions"] = "completed"
        self._write_manifest(run_dir, manifest)
        return self._response(run_dir, manifest)

    def artifact(self, run_id: str, name: str) -> Path:
        allowed = {
            "requirement.txt",
            "final_configs.json",
            "unity_contract.json",
            "telemetry.json",
            "runtime_evaluation.json",
            "runtime_evaluation_report.md",
            "improvement_suggestions.json",
            "run_manifest.json",
        }
        if name not in allowed:
            raise ValueError("Artifact name is not allowed.")
        run_dir, _ = self._load(run_id)
        path = run_dir / name
        if not path.is_file():
            raise FileNotFoundError(name)
        return path

    def _load(self, run_id: str) -> tuple[Path, dict[str, Any]]:
        if not run_id.startswith("run_") or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in run_id):
            raise KeyError("Invalid runtime run id.")
        run_dir = self.runs_dir / run_id
        manifest_path = run_dir / "run_manifest.json"
        if not manifest_path.is_file():
            raise KeyError(f"Unknown runtime run: {run_id}")
        return run_dir, json.loads(manifest_path.read_text(encoding="utf-8"))

    def _write_manifest(self, run_dir: Path, manifest: dict[str, Any]) -> None:
        _write_json(run_dir / "run_manifest.json", manifest)

    def _response(self, run_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
        response = deepcopy(manifest)
        response["telemetry"] = _read_json_if_exists(run_dir / "telemetry.json")
        response["evaluation"] = _read_json_if_exists(run_dir / "runtime_evaluation.json")
        response["improvement_suggestions"] = _read_json_if_exists(run_dir / "improvement_suggestions.json") or []
        response["available_artifacts"] = [
            {"name": path.name, "size": path.stat().st_size}
            for path in sorted(run_dir.iterdir())
            if path.is_file()
        ]
        return response


def _scenario_for_case(case: dict[str, Any]) -> dict[str, Any]:
    scenario = deepcopy(DEFAULT_RUNTIME_SCENARIO)
    time_target = case["expected_runtime_targets"].get("completion_time_seconds")
    if isinstance(time_target, dict):
        scenario["targets"]["completion_time_seconds_min"] = time_target["min"]
        scenario["targets"]["completion_time_seconds_max"] = time_target["max"]
    return scenario


def _artifact_paths(run_id: str) -> dict[str, str]:
    prefix = f"runtime_runs/{run_id}"
    return {
        "requirement": f"{prefix}/requirement.txt",
        "final_configs": f"{prefix}/final_configs.json",
        "unity_contract": f"{prefix}/unity_contract.json",
        "telemetry": f"{prefix}/telemetry.json",
        "runtime_evaluation": f"{prefix}/runtime_evaluation.json",
        "runtime_report": f"{prefix}/runtime_evaluation_report.md",
        "improvement_suggestions": f"{prefix}/improvement_suggestions.json",
    }


def _improvement_suggestions(result: dict[str, Any]) -> list[dict[str, str]]:
    suggestions = {
        "run_completed": "检查失败原因、玩家生存能力和关卡完成条件后重新运行。",
        "completion_time_in_target": "调整敌人耐久、波次数量或玩家输出，使通关时间回到策划目标区间。",
        "normal_enemy_hits_to_kill_in_target": "调整武器攻击力或普通敌人生命值，使击杀次数符合手感目标。",
        "first_upgrade_affordable": "调整首通奖励或第一次升级成本，确保首通后可以完成一次升级。",
        "second_upgrade_affordable": "降低首通奖励或提高第二次升级成本，避免首通后连续完成两次升级。",
    }
    return [
        {
            "check_id": check["check_id"],
            "reason": f"实际结果 {check['actual']}，策划目标 {check['expected']}。",
            "suggestion": suggestions.get(check["check_id"], "检查对应配置与运行数据后重新验证。"),
        }
        for check in result["failed_checks"]
    ]


def _launch_process(command: list[str], working_directory: Path) -> int:
    process = subprocess.Popen(command, cwd=working_directory)
    return process.pid


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


def _new_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"run_{timestamp}_{uuid.uuid4().hex[:8]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
