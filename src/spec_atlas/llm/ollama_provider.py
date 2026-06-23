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
    """Groq cloud LLM provider (OpenAI-compatible REST API). Free tier available."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model
        self.provider_name = "groq"

    async def complete(
        self,
        messages: list[Message],
        schema: dict | None = None,
        temperature: float = 0.7,
    ) -> str | dict:
        """Generate a completion using Groq's chat completions endpoint."""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                payload = {
                    "model": self.model,
                    "messages": list(messages),
                    "temperature": temperature,
                    "max_tokens": 4096,
                }
                # Groq supports response_format for JSON output (OpenAI-compatible)
                if schema:
                    payload["response_format"] = {"type": "json_object"}

                response = await client.post(
                    self.API_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Groq error: {e}") from e

        text = response.json()["choices"][0]["message"]["content"]

        if schema:
            try:
                return json.loads(_extract_json_block(text))
            except (json.JSONDecodeError, IndexError):
                return text

        return text
