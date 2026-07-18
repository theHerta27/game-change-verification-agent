from __future__ import annotations

import os

from agent_service.llm.base import LLMClient
from agent_service.llm.mock_llm import MockLLM
from agent_service.llm.openai_compatible import OpenAICompatibleLLM
from agent_service.schemas import ReviewRequest


def create_llm_client(request: ReviewRequest) -> LLMClient:
    if request.mode == "mock":
        return MockLLM()

    if request.llm_config is not None:
        config = request.llm_config
        provider = config.provider or "openai_compatible"
        base_url = config.base_url
        api_key = config.api_key
        model = config.model
        timeout_seconds = config.timeout_seconds
    else:
        provider = os.getenv("LLM_PROVIDER", "").strip()
        base_url = os.getenv("LLM_API_BASE")
        api_key = os.getenv("LLM_API_KEY")
        model = os.getenv("LLM_MODEL")
        timeout_seconds = 30

    if request.mode == "openai_compatible":
        provider = "openai_compatible"
    if not provider and not base_url and not api_key and not model:
        raise ValueError("real LLM config missing")
    if provider != "openai_compatible":
        raise ValueError(f"不支持的 LLM provider: {provider}")

    missing = []
    if not base_url:
        missing.append("base_url")
    if not model:
        missing.append("model")
    if missing:
        raise ValueError(f"real LLM config missing: {', '.join(missing)}")

    return OpenAICompatibleLLM(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
    )
