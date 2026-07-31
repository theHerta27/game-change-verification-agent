"""Normalized cross-engine evidence without changing raw engine telemetry."""

from __future__ import annotations

from typing import Any
import hashlib
import json


def config_sha256(contract: dict[str, Any]) -> str:
    payload = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_engine_telemetry(
    *,
    engine_name: str,
    engine_version: str | None,
    build_id: str | None,
    run_id: str,
    contract: dict[str, Any],
    seed: int,
    raw: dict[str, Any],
) -> dict[str, Any]:
    status = raw.get("status")
    runtime_errors = raw.get("runtime_error_count", raw.get("exception_log_count"))
    return {
        "contract_version": contract["bullet_hell_contract_version"],
        "engine_name": engine_name,
        "engine_version": engine_version,
        "build_id": build_id,
        "run_id": run_id,
        "config_hash": config_sha256(contract),
        "seed": seed,
        "duration_seconds": raw.get("duration_seconds"),
        "total_bullets_spawned": raw.get("total_bullets_spawned"),
        "peak_alive_bullets": raw.get("peak_alive_bullets"),
        "player_hits": raw.get("player_hits"),
        "player_survival_seconds": raw.get("player_survival_seconds"),
        "phase_results": raw.get("phase_results"),
        "average_fps": raw.get("average_fps"),
        "low_percentile_fps": raw.get("low_percentile_fps"),
        "minimum_fps": raw.get("minimum_fps"),
        "runtime_error_count": runtime_errors,
        "completed": status in {"completed", "failed"} or raw.get("completed") is True,
        "raw_status": status,
        "validation_outcome": "passed" if status == "completed" else "failed" if status == "failed" else "unknown",
    }
