"""UE5 runner environment contract; runtime implementation follows the real UE build."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from workflow.engines.base import EngineRunResult, EngineRunner


class UnrealEngineRunner(EngineRunner):
    name = "unreal"

    def __init__(
        self,
        *,
        repository_root: Path,
        editor_executable: Path | None = None,
    ) -> None:
        self.repository_root = repository_root
        self.project_path = repository_root / "game-unreal" / "BulletHellUE" / "BulletHellUE.uproject"
        self.executable = (
            repository_root
            / "game-unreal"
            / "BulletHellUE"
            / "Builds"
            / "Windows"
            / "BulletHellUE.exe"
        )
        self.editor_executable = editor_executable

    def capabilities(self) -> dict[str, Any]:
        environment = self.validate_environment()
        return {
            "engine": self.name,
            "display_name": "Unreal Engine 5",
            "status": environment["status"],
            "reason": environment["reason"],
            "contract_version": "1.0",
            "patterns": ["spiral"],
            "unsupported_patterns": ["ring", "aimed_fan", "petal"],
            "automated_run": environment["status"] in {"available", "verified"},
            "manual_play": environment["status"] in {"available", "verified"},
            "screenshots": [10, 20, 30],
        }

    def validate_environment(self) -> dict[str, Any]:
        if not self.project_path.is_file():
            return {
                "status": "unavailable",
                "reason": "UE5 project has not been created and no UE evidence exists.",
            }
        if self.executable.is_file():
            return {
                "status": "available",
                "reason": "UE5 project and registered packaged Player are available but not yet verified.",
                "executable": str(self.executable),
            }
        return {
            "status": "build_required",
            "reason": "UE5 project exists, but the registered Windows Player has not been built.",
            "project": str(self.project_path),
        }

    def build(self) -> dict[str, Any]:
        raise RuntimeError("UE5 build is unavailable until the real engine path and project are installed.")

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
        raise RuntimeError("UE5 automated_run is not implemented or verified yet.")

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
        raise RuntimeError("UE5 manual_play is not implemented or verified yet.")

    def discover_artifacts(self, run_dir: Path) -> dict[str, str]:
        return {}
