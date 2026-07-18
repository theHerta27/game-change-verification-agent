from __future__ import annotations

from abc import ABC, abstractmethod

from agent_service.schemas import ReviewRequest, StaticHint


class LLMClient(ABC):
    provider_name = "unknown"
    model_name: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    output_label = "llm"
    repair_attempted = False
    validation_error_details: list[dict[str, str]] = []

    @abstractmethod
    def generate(self, request: ReviewRequest, static_hints: list[StaticHint]) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_findings(self, request: ReviewRequest, static_hints: list[StaticHint]) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_tests(self, request: ReviewRequest, findings: list[dict]) -> str:
        raise NotImplementedError

    def repair_findings(
        self,
        request: ReviewRequest,
        findings: list[dict],
        validation_errors: list[dict[str, str]],
        static_hints: list[StaticHint],
    ) -> str | None:
        return None
