"""Unity 6 implementation of the engine runner contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import subprocess

from gameconfig_agent.bullet_hell import write_json
from workflow.engines.base import EngineRunResult, EngineRunner
from workflow.engines.telemetry import normalize_engine_telemetry


class UnityEngineRunner(EngineRunner):
    name = "unity"

    def __init__(
        self,
        *,
        repository_root: Path,
        executable: Path,
        editor_executable: Path | None = None,
    ) -> None:
        self.repository_root = repository_root
        self.executable = executable
        self.editor_executable = editor_executable or Path(r"E:\Unity6\6000.3.19f1\Editor\Unity.exe")
        self.project_path = repository_root / "game-unity"
        self.build_script = repository_root / "scripts" / "smoke-bullet-hell.ps1"

    def capabilities(self) -> dict[str, Any]:
        environment = self.validate_environment()
        return {
            "engine": self.name,
            "display_name": "Unity 6",
            "status": environment["status"],
            "reason": environment["reason"],
            "contract_version": "1.0",
            "patterns": ["ring", "aimed_fan", "spiral", "petal"],
            "automated_run": True,
            "manual_play": True,
            "screenshots": [10, 20, 30],
        }

    def validate_environment(self) -> dict[str, Any]:
        if not self.project_path.is_dir():
            return {"status": "unavailable", "reason": f"Unity project not found: {self.project_path}"}
        if self.executable.is_file():
            return {
                "status": "available",
                "reason": "Committed project and fixed Bullet Hell Player path are available.",
                "executable": str(self.executable),
            }
        if self.editor_executable.is_file():
            return {
                "status": "build_required",
                "reason": "Unity project exists, but BulletHellDemo.exe must be rebuilt.",
                "editor": str(self.editor_executable),
            }
        return {
            "status": "unavailable",
            "reason": "Unity Editor and Bullet Hell Player were not found at registered paths.",
        }

    def build(self) -> dict[str, Any]:
        if not self.editor_executable.is_file():
            raise FileNotFoundError(f"Unity Editor not found: {self.editor_executable}")
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.build_script),
                "-UnityEditor",
                str(self.editor_executable),
            ],
            cwd=self.repository_root,
            timeout=420,
            check=False,
        )
        if result.returncode != 0 or not self.executable.is_file():
            raise RuntimeError(
                f"Unity fixed build script failed with exit code {result.returncode}; "
                f"expected player: {self.executable}"
            )
        return {"status": "available", "exit_code": result.returncode, "executable": str(self.executable)}

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
        if not self.executable.is_file():
            raise FileNotFoundError(
                f"Bullet Hell Unity player not found: {self.executable}. "
                "Run scripts/smoke-bullet-hell.ps1 first."
            )
        run_dir.mkdir(parents=True, exist_ok=True)
        config_path = run_dir / "config.json"
        telemetry_path = run_dir / "telemetry.json"
        log_path = run_dir / "player.log"
        write_json(config_path, contract)
        if capture_times:
            command = [
                str(self.executable),
                "-force-d3d11",
                "-screen-fullscreen", "0",
                "-screen-width", "960",
                "-screen-height", "540",
                "--bullet-hell",
                "--auto-run",
                "--seed", str(seed),
                "--config-input", str(config_path),
                "--telemetry-output", str(telemetry_path),
                "--screenshot-output-dir", str(run_dir),
                "-logFile", str(log_path),
            ]
        else:
            command = [
                str(self.executable),
                "-batchmode",
                "-nographics",
                "--bullet-hell",
                "--auto-run",
                "--seed", str(seed),
                "--config-input", str(config_path),
                "--telemetry-output", str(telemetry_path),
                "-logFile", str(log_path),
            ]
        result = subprocess.run(command, cwd=self.executable.parent, timeout=90, check=False)
        if not telemetry_path.is_file():
            raise RuntimeError(
                f"Bullet Hell Unity player exited with code {result.returncode} "
                f"without telemetry. See {log_path}"
            )
        telemetry = json.loads(telemetry_path.read_text(encoding="utf-8-sig"))
        if result.returncode != 0 and telemetry.get("status") not in {"failed", "completed"}:
            raise RuntimeError(
                f"Bullet Hell Unity player exited with code {result.returncode} "
                f"and unusable telemetry status {telemetry.get('status')!r}. See {log_path}"
            )
        if capture_times:
            manifest_path = run_dir / "capture_manifest.json"
            expected = [run_dir / f"capture_{second:02d}s.png" for second in capture_times]
            missing = [path.name for path in expected if not path.is_file()]
            if missing or not manifest_path.is_file():
                raise RuntimeError(
                    f"{variant} visual capture exited with code {result.returncode}; "
                    f"missing artifacts: {missing or ['capture_manifest.json']}. See {log_path}"
                )
        normalized = normalize_engine_telemetry(
            engine_name=self.name,
            engine_version="6000.3.19f1",
            build_id=self.executable.stat().st_mtime_ns.__str__(),
            run_id=run_id,
            contract=contract,
            seed=seed,
            raw=telemetry,
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
        if not self.executable.is_file():
            raise FileNotFoundError(f"Bullet Hell Unity player not found: {self.executable}")
        command = [
            str(self.executable),
            "--bullet-hell",
            "--seed", str(seed),
            "--config-input", str(config_path),
            "--telemetry-output", str(telemetry_path),
            "-logFile", str(log_path),
        ]
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
        return {name: str(run_dir / name) for name in allowed if (run_dir / name).is_file()}
