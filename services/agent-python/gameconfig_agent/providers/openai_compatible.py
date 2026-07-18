"""OpenAI-compatible Chat Completions provider."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from gameconfig_agent.providers.base import LLMResponse


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.base_url = (base_url or os.environ.get("GAMECONFIG_LLM_BASE_URL") or "").rstrip("/")
        self.api_key = api_key or os.environ.get("GAMECONFIG_LLM_API_KEY")
        self.model = model or os.environ.get("GAMECONFIG_LLM_MODEL")
        self.timeout_seconds = timeout_seconds
        missing = [
            name
            for name, value in (
                ("GAMECONFIG_LLM_BASE_URL", self.base_url),
                ("GAMECONFIG_LLM_API_KEY", self.api_key),
                ("GAMECONFIG_LLM_MODEL", self.model),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    def complete_json(self, *, prompt_name: str, system_prompt: str, user_prompt: str) -> LLMResponse:
        started = time.perf_counter()
        request_body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self._chat_completions_url(),
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Provider HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Provider connection error: {exc.reason}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        content = raw["choices"][0]["message"]["content"]
        usage = raw.get("usage")
        token_estimate = None if usage else max(1, len(system_prompt.split()) + len(user_prompt.split()) + len(content.split()))
        return LLMResponse(content=content, latency_ms=latency_ms, usage=usage, token_estimate=token_estimate, raw=raw)

    def _chat_completions_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"
