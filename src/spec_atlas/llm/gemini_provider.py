"""Default real LLM provider — Google Gemini free tier over raw HTTP.

Uses ``httpx`` against the Generative Language REST API — **no vendor SDK** (cross-cutting
contract). Requires ``GEMINI_API_KEY``; never exercised in CI (the fake is). Transient
failures (429 / timeout) are retried with backoff; structured output is validated against
the caller's JSON Schema (INTEGRATIONS.md §3)."""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from .base import LLMProvider, Message, TransientLLMError, transient_retry, validate_json

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLMProvider(LLMProvider):
    def __init__(
        self, api_key: str, model: str = "gemini-1.5-flash", timeout: float = 30.0
    ) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for the Gemini provider.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    @staticmethod
    def _to_payload(messages: Sequence[Message], schema: dict | None) -> dict:
        contents: list[dict] = []
        system_parts: list[dict] = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append({"text": m["content"]})
                continue
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        payload: dict = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        if schema is not None:
            payload["generationConfig"] = {
                "responseMimeType": "application/json",
                "responseSchema": schema,
            }
        return payload

    @staticmethod
    def _extract_text(data: dict) -> str:
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:  # pragma: no cover - network-shaped
            raise TransientLLMError(f"Unexpected Gemini response shape: {data}") from exc

    @transient_retry()
    def _post(self, payload: dict) -> dict:
        url = f"{_BASE_URL}/{self._model}:generateContent"
        try:
            resp = httpx.post(
                url,
                params={"key": self._api_key},
                json=payload,
                timeout=self._timeout,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise TransientLLMError(f"Gemini request failed: {exc}") from exc

        if resp.status_code == 429 or resp.status_code >= 500:
            raise TransientLLMError(f"Gemini transient HTTP {resp.status_code}")
        resp.raise_for_status()
        return resp.json()

    def complete(self, messages: Sequence[Message], schema: dict | None = None) -> str | dict:
        data = self._post(self._to_payload(messages, schema))
        text = self._extract_text(data)
        return validate_json(text, schema) if schema is not None else text
