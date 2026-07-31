"""Engine-independent runner contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EngineRunResult:
    engine_name: str
    telemetry: dict[str, Any]
    normalized_evidence: dict[str, Any]
    artifacts: dict[str, str]
    exit_code: int


class EngineRunner(ABC):
    name: str

    @abstractmethod
    def capabilities(self) -> dict[str, Any]:
        """Describe supported contract and runtime features."""

    @abstractmethod
    def validate_environment(self) -> dict[str, Any]:
        """Return unavailable, build_required, available, verified, or failed."""

    @abstractmethod
    def build(self) -> dict[str, Any]:
        """Build the fixed project target without accepting user commands."""

    @abstractmethod
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
        """Run one fixed-seed engine test and validate its evidence."""

    @abstractmethod
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
        """Launch the fixed player for subjective manual experience."""

    @abstractmethod
    def discover_artifacts(self, run_dir: Path) -> dict[str, str]:
        """Return only known evidence files under the supplied run directory."""
