"""Read-only normalization for Unity runtime telemetry."""

from __future__ import annotations

from copy import deepcopy


class RuntimeTelemetryNormalizer:
    FIELD_ALIASES = {
        "completion_time_seconds": ("completion_time_seconds", "clear_time_seconds"),
        "enemies_defeated": ("enemies_defeated",),
        "normal_attacks": ("basic_attacks", "normal_attacks"),
        "skill_uses": ("skill_uses", "skills_used"),
        "gold_earned": ("gold_earned",),
        "gold_spent": ("gold_spent",),
        "upgrade_count": ("upgrade_count", "upgrades_completed"),
    }

    def normalize(self, raw: dict) -> dict:
        values: dict[str, object] = {}
        field_sources: dict[str, str | None] = {}
        for normalized_field, aliases in self.FIELD_ALIASES.items():
            source = next((alias for alias in aliases if alias in raw), None)
            values[normalized_field] = raw[source] if source is not None else "unavailable"
            field_sources[normalized_field] = source
        return {
            "values": values,
            "field_sources": field_sources,
            "raw": deepcopy(raw),
        }
