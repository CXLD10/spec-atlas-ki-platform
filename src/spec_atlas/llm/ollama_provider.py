"""Real (non-fake) LLM providers: local Ollama and free-tier Groq.

Both speak HTTP via :mod:`httpx` only — no vendor SDK (Groq's API is OpenAI-compatible
REST, so no ``groq`` package is needed; ARCHITECTURE.md cross-cutting contract: never
call a vendor SDK directly, and zero-cost/no-new-dependency per NFR).
"""

from __future__ import annotations

import json

import httpx

from .base import LLMProvider, Message


def _extract_json_block(text: str) -> str:
    """Pull a ```json ... ``` fenced block out of ``text`` if present, else return as-is."""
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    return text


class OllamaProvider(LLMProvider):
    """Local Ollama LLM provider. Requires `ollama serve` running on localhost:11434."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.provider_name = f"ollama-{model}"

    async def complete(
        self,
        messages: list[Message],
        schema: dict | None = None,
        temperature: float = 0.7,
    ) -> str | dict:
        """Generate a completion using Ollama."""
        prompt = self._format_messages(messages)

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": temperature,
                        "num_predict": 4096,
                    },
                )
            response.raise_for_status()
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure to run `ollama serve` first."
            ) from e
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama error: {e}") from e

        text = response.json().get("response", "").strip()

        if schema:
            try:
                return json.loads(_extract_json_block(text))
            except (json.JSONDecodeError, IndexError):
                return text

        return text

    def _format_messages(self, messages: list[Message]) -> str:
        """Convert chat messages to prompt format."""
        formatted = [f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages]
        return "\n".join(formatted) + "\nASSISTANT:"


class GroqProvider(LLMProvider):
    """Groq cloud LLM provider with in-memory multi-key rotation and 429 handling."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    COOLDOWN_SECONDS = 300  # 5 minutes per key after a 429

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        import os
        from datetime import datetime

        # Accept comma-separated keys in GROQ_API_KEYS, fall back to single GROQ_API_KEY
        multi = os.environ.get("GROQ_API_KEYS", "")
        self.keys: list[str] = [k.strip() for k in multi.split(",") if k.strip()]
        if not self.keys:
            single = os.environ.get("GROQ_API_KEY", "")
            if single:
                self.keys = [single]

        self.model = model
        self.provider_name = "groq"
        self._current_idx: int = 0
        # key_index → datetime when cooldown expires (or None)
        self._cooldowns: dict[int, datetime] = {}

    def _next_available_key(self) -> tuple[int, str] | None:
        """Return (index, key) for the next key not in cooldown, or None if all are cooling."""
        from datetime import datetime

        for offset in range(len(self.keys)):
            idx = (self._current_idx + offset) % len(self.keys)
            expires = self._cooldowns.get(idx)
            if expires is None or datetime.utcnow() >= expires:
                self._cooldowns.pop(idx, None)
                self._current_idx = idx
                return idx, self.keys[idx]
        return None

    def _mark_cooldown(self, idx: int) -> None:
        from datetime import datetime, timedelta
        import logging
        self._cooldowns[idx] = datetime.utcnow() + timedelta(seconds=self.COOLDOWN_SECONDS)
        self._current_idx = (idx + 1) % len(self.keys)
        logging.getLogger(__name__).warning(
            f"Groq key [{idx}] rate-limited — cooling down for {self.COOLDOWN_SECONDS}s. "
            f"Rotating to key [{self._current_idx}]."
        )

    async def complete(
        self,
        messages: list[Message],
        schema: dict | None = None,
        temperature: float = 0.7,
    ) -> str | dict:
        """Generate completion, rotating keys automatically on 429."""
        import asyncio
        import logging

        log = logging.getLogger(__name__)

        if not self.keys:
            raise RuntimeError("No Groq API keys configured. Set GROQ_API_KEYS or GROQ_API_KEY in .env.")

        payload = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if schema:
            payload["response_format"] = {"type": "json_object"}

        # Try each key up to len(keys) times; after all are exhausted, raise.
        max_attempts = len(self.keys) * 2
        for attempt in range(max_attempts):
            result = self._next_available_key()
            if result is None:
                raise RuntimeError("All Groq API keys are rate-limited. Try again in a few minutes.")

            key_idx, api_key = result

            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        self.API_URL,
                        headers={"Authorization": f"Bearer {api_key}"},
                        json=payload,
                    )

                if response.status_code == 401:
                    error_msg = response.json().get("error", {}).get("message", "Unauthorized")
                    raise RuntimeError(f"Groq key [{key_idx}] auth failed (401): {error_msg}")

                if response.status_code == 429:
                    self._mark_cooldown(key_idx)
                    wait = min(2 ** attempt, 16)
                    log.warning(f"Groq 429 on key [{key_idx}]. Waiting {wait}s before retry.")
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()

            except httpx.HTTPError as e:
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 ** min(attempt, 4))
                    continue
                raise RuntimeError(f"Groq HTTP error: {e}") from e

            text = response.json()["choices"][0]["message"]["content"]
            if schema:
                try:
                    return json.loads(_extract_json_block(text))
                except (json.JSONDecodeError, IndexError):
                    return text
            return text

        raise RuntimeError("Groq: exceeded max retry attempts across all keys.")
