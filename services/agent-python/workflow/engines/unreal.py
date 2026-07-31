"""Restricted UE5 Windows Player implementation of the EngineRunner contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import os
import subprocess

from gameconfig_agent.bullet_hell import write_json
from workflow.engines.base import EngineRunResult, EngineRunner
from workflow.engines.telemetry import config_sha256, normalize_engine_telemetry


class UnrealEngineRunner(EngineRunner):
    name = "unreal"

    def __init__(
        self,
        *,
        repository_root: Path,
        editor_executable: Path | None = None,
        process_timeout_seconds: int = 120,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.project_path = (
            self.repository_root / "game-unreal" / "BulletHellUE" / "BulletHellUE.uproject"
        )
        self.executable = (
            self.repository_root
            / "game-unreal"
            / "BulletHellUE"
            / "Builds"
            / "Windows"
            / "BulletHellUE.exe"
        )
        configured_editor = os.environ.get("GAMECHANGE_UE_EDITOR")
        self.editor_executable = editor_executable or Path(
            configured_editor
            or r"D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
        )
        self.build_script = self.repository_root / "scripts" / "build-unreal.ps1"
        self.runtime_root = self.repository_root / "runtime-artifacts"
        self.verification_state_path = (
            self.runtime_root / "ue5-verification" / "runner_verification.json"
        )
        self.process_timeout_seconds = process_timeout_seconds

    def capabilities(self) -> dict[str, Any]:
        environment = self.validate_environment()
        return {
            "engine": self.name,
            "display_name": "Unreal Engine 5.8.1",
            "status": environment["status"],
            "reason": environment["reason"],
            "contract_version": "1.0",
            "patterns": ["ring", "aimed_fan", "spiral", "petal"],
            "unsupported_patterns": [],
            "automated_run": environment["status"] in {"available", "verified"},
            "manual_play": environment["status"] in {"available", "verified"},
            "screenshots": [10, 20, 30],
        }

    def validate_environment(self) -> dict[str, Any]:
        if not self.project_path.is_file():
            return {
                "status": "unavailable",
                "reason": f"UE5 project was not found: {self.project_path}",
            }
        if not self.executable.is_file():
            if self.editor_executable.is_file():
                return {
                    "status": "build_required",
                    "reason": "UE5 project exists, but the registered Windows Player has not been built.",
                    "project": str(self.project_path),
                    "editor": str(self.editor_executable),
                }
            return {
                "status": "unavailable",
                "reason": "UE5 project exists, but neither the Editor nor packaged Player is available.",
            }

        verification = _read_json_if_exists(self.verification_state_path)
        if verification and self._verification_files_exist(verification):
            return {
                "status": "verified",
                "reason": "UE5 packaged Player completed real baseline/candidate runs with telemetry and screenshots.",
                "executable": str(self.executable),
                "verification": str(self.verification_state_path),
            }
        return {
            "status": "available",
            "reason": "UE5 packaged Player is available; complete baseline/candidate evidence is not recorded yet.",
            "executable": str(self.executable),
        }

    def build(self) -> dict[str, Any]:
        if not self.editor_executable.is_file():
            raise FileNotFoundError(f"Unreal Editor not found: {self.editor_executable}")
        if not self.build_script.is_file():
            raise FileNotFoundError(f"Fixed UE build script not found: {self.build_script}")
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.build_script),
                "-UnrealEditor",
                str(self.editor_executable),
            ],
            cwd=self.repository_root,
            timeout=900,
            check=False,
        )
        if result.returncode != 0 or not self.executable.is_file():
            raise RuntimeError(
                f"UE5 fixed build failed with exit code {result.returncode}; "
                f"expected Player: {self.executable}"
            )
        return {
            "status": "available",
            "exit_code": result.returncode,
            "executable": str(self.executable),
        }

    def automated_run(
        self,
        *,
        contract: dict[str, Any],
        run_dir: Path,
        seed: int,
        run_id: str,
        variant: str,
        capture_times: tuple[int, ...] = (),
    ) -> EngineRunResult:
        self._require_player()
        self._require_variant(variant)
        run_dir = self._require_runtime_path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        config_path = run_dir / "config.json"
        telemetry_path = run_dir / "telemetry.json"
        log_path = run_dir / "player.log"
        write_json(config_path, contract)
        canonical_hash = config_sha256(contract)
        file_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
        requested_captures = capture_times or (10, 20, 30)
        command = self._command(
            config_path=config_path,
            telemetry_path=telemetry_path,
            log_path=log_path,
            seed=seed,
            run_id=run_id,
            variant=variant,
            canonical_hash=canonical_hash,
            file_hash=file_hash,
            automated=True,
            screenshot_dir=run_dir,
        )
        try:
            result = subprocess.run(
                command,
                cwd=self.executable.parent,
                timeout=self.process_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"UE5 {variant} run timed out after {self.process_timeout_seconds}s. "
                f"See {log_path}"
            ) from exc

        telemetry = self._validate_run_evidence(
            telemetry_path=telemetry_path,
            log_path=log_path,
            canonical_hash=canonical_hash,
            requested_captures=requested_captures,
            run_dir=run_dir,
            exit_code=result.returncode,
        )
        normalized = normalize_engine_telemetry(
            engine_name=self.name,
            engine_version=str(telemetry.get("engine_version") or "5.8.1"),
            build_id=str(telemetry.get("build_id") or self.executable.stat().st_mtime_ns),
            run_id=run_id,
            contract=contract,
            seed=seed,
            raw=telemetry,
        )
        self._record_verification(
            run_id=run_id,
            variant=variant,
            run_dir=run_dir,
            canonical_hash=canonical_hash,
            seed=seed,
        )
        return EngineRunResult(
            engine_name=self.name,
            telemetry=telemetry,
            normalized_evidence=normalized,
            artifacts=self.discover_artifacts(run_dir),
            exit_code=result.returncode,
        )

    def manual_play(
        self,
        *,
        config_path: Path,
        telemetry_path: Path,
        log_path: Path,
        seed: int,
        run_id: str,
        variant: str,
    ) -> dict[str, Any]:
        self._require_player()
        self._require_variant(variant)
        config_path = self._require_runtime_path(config_path)
        telemetry_path = self._require_runtime_path(telemetry_path)
        log_path = self._require_runtime_path(log_path)
        if not config_path.is_file():
            raise FileNotFoundError(f"Workflow config was not found: {config_path}")
        contract = json.loads(config_path.read_text(encoding="utf-8-sig"))
        command = self._command(
            config_path=config_path,
            telemetry_path=telemetry_path,
            log_path=log_path,
            seed=seed,
            run_id=run_id,
            variant=variant,
            canonical_hash=config_sha256(contract),
            file_hash=hashlib.sha256(config_path.read_bytes()).hexdigest(),
            automated=False,
            screenshot_dir=None,
        )
        process = subprocess.Popen(command, cwd=self.executable.parent)
        return {
            "engine": self.name,
            "workflow_id": run_id,
            "process_id": process.pid,
            "status": "launched",
            "variant": variant,
            "config_artifact": config_path.name,
        }

    def discover_artifacts(self, run_dir: Path) -> dict[str, str]:
        allowed = (
            "config.json",
            "telemetry.json",
            "player.log",
            "capture_manifest.json",
            "capture_10s.png",
            "capture_20s.png",
            "capture_30s.png",
        )
        return {
            name: str(run_dir / name)
            for name in allowed
            if (run_dir / name).is_file()
        }

    def _command(
        self,
        *,
        config_path: Path,
        telemetry_path: Path,
        log_path: Path,
        seed: int,
        run_id: str,
        variant: str,
        canonical_hash: str,
        file_hash: str,
        automated: bool,
        screenshot_dir: Path | None,
    ) -> list[str]:
        command = [
            str(self.executable),
            "-RenderOffscreen",
            "-Windowed",
            "-ResX=960",
            "-ResY=540",
            "-NoSplash",
            "-NoSound",
            "-BulletHell",
            f"-Seed={seed}",
            f"-RunId={run_id}",
            f"-Variant={variant}",
            f"-ConfigInput={config_path}",
            f"-TelemetryOutput={telemetry_path}",
            f"-ConfigHash={canonical_hash}",
            f"-ConfigFileHash={file_hash}",
            f"-abslog={log_path}",
        ]
        if automated:
            if screenshot_dir is None:
                raise ValueError("screenshot_dir is required for an automated UE5 run")
            command.extend(["-Unattended", "-Automated", f"-ScreenshotDir={screenshot_dir}"])
        return command

    def _validate_run_evidence(
        self,
        *,
        telemetry_path: Path,
        log_path: Path,
        canonical_hash: str,
        requested_captures: tuple[int, ...],
        run_dir: Path,
        exit_code: int,
    ) -> dict[str, Any]:
        if not telemetry_path.is_file():
            raise RuntimeError(
                f"UE5 Player exited with code {exit_code} without telemetry. See {log_path}"
            )
        try:
            telemetry = json.loads(telemetry_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"UE5 telemetry is not valid JSON: {telemetry_path}") from exc
        if telemetry.get("config_hash") != canonical_hash:
            raise RuntimeError(
                f"UE5 telemetry config_hash mismatch: {telemetry.get('config_hash')!r} "
                f"!= {canonical_hash!r}"
            )
        if telemetry.get("completed") is not True:
            raise RuntimeError(
                f"UE5 run did not complete: status={telemetry.get('status')!r}. See {log_path}"
            )
        if int(telemetry.get("runtime_error_count", 0)) != 0:
            raise RuntimeError(
                f"UE5 run reported runtime errors: {telemetry.get('runtime_error_count')}. "
                f"See {log_path}"
            )
        manifest_path = run_dir / "capture_manifest.json"
        missing = [
            f"capture_{second:02d}s.png"
            for second in requested_captures
            if not (run_dir / f"capture_{second:02d}s.png").is_file()
        ]
        if missing or not manifest_path.is_file():
            raise RuntimeError(
                f"UE5 run is missing automatic visual evidence: "
                f"{missing or ['capture_manifest.json']}. See {log_path}"
            )
        manifest = _read_json_if_exists(manifest_path)
        if not manifest or manifest.get("config_hash") != canonical_hash:
            raise RuntimeError("UE5 capture manifest is missing or references the wrong config.")
        return telemetry

    def _record_verification(
        self,
        *,
        run_id: str,
        variant: str,
        run_dir: Path,
        canonical_hash: str,
        seed: int,
    ) -> None:
        verification_variant = "candidate" if variant != "baseline" else "baseline"
        state = _read_json_if_exists(self.verification_state_path) or {
            "status": "collecting",
            "engine": "unreal",
            "engine_version": "5.8.1",
            "run_id": run_id,
            "seed": seed,
            "variants": {},
        }
        if state.get("run_id") != run_id or state.get("seed") != seed:
            state = {
                "status": "collecting",
                "engine": "unreal",
                "engine_version": "5.8.1",
                "run_id": run_id,
                "seed": seed,
                "variants": {},
            }
        state["variants"][verification_variant] = {
            "config_hash": canonical_hash,
            "run_dir": str(run_dir),
            "telemetry": str(run_dir / "telemetry.json"),
            "capture_manifest": str(run_dir / "capture_manifest.json"),
            "screenshots": [
                str(run_dir / f"capture_{second:02d}s.png")
                for second in (10, 20, 30)
            ],
        }
        if {"baseline", "candidate"} <= set(state["variants"]):
            state["status"] = "verified"
        write_json(self.verification_state_path, state)

    def _verification_files_exist(self, verification: dict[str, Any]) -> bool:
        if verification.get("status") != "verified":
            return False
        variants = verification.get("variants", {})
        for variant in ("baseline", "candidate"):
            row = variants.get(variant, {})
            required = [row.get("telemetry"), row.get("capture_manifest")]
            required.extend(row.get("screenshots", []))
            if len(required) != 5 or any(
                not value or not Path(value).is_file()
                for value in required
            ):
                return False
        return True

    def _require_player(self) -> None:
        if not self.executable.is_file():
            raise FileNotFoundError(
                f"Registered UE5 Player was not found: {self.executable}. "
                "Run scripts/build-unreal.ps1 first."
            )

    @staticmethod
    def _require_variant(variant: str) -> None:
        if variant != "baseline" and not variant.startswith("candidate"):
            raise ValueError(f"Unsupported UE5 variant: {variant!r}")

    def _require_runtime_path(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.runtime_root):
            raise ValueError(
                f"UE5 runtime path must remain under {self.runtime_root}: {resolved}"
            )
        return resolved


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None
