"""Base provider contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMResponse:
    content: str
    latency_ms: int
    usage: dict | None = None
    token_estimate: int | None = None
    raw: dict | None = None


class LLMProvider(Protocol):
    name: str

    def complete_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a JSON string from the provider."""
