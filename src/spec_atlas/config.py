"""Central, env-validated configuration for Spec-Atlas.

All configuration comes from the environment (or a local, gitignored ``.env``);
see ``.env.example`` for the full list. Defaults are **offline and zero-cost**:
both providers default to ``fake`` so the app boots and tests run with no network,
no credentials, and no cost (NFR: $0; testing-standard: offline fakes).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProviderName = Literal["fake", "gemini", "groq", "ollama"]
EmbedProviderName = Literal["fake", "fastembed"]


class Settings(BaseSettings):
    """Validated application settings, loaded from the environment / ``.env``.

    Unknown env vars are ignored so the same environment can host other tools.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Databases (two separate logical DBs; DATA-MODEL.md) -----------------
    # Optional so the app boots without a DB; migrations/health require them.
    analysis_db_url: str | None = Field(default=None, alias="ANALYSIS_DB_URL")
    spec_db_url: str | None = Field(default=None, alias="SPEC_DB_URL")

    # --- Providers (reached only via LLMProvider / EmbeddingProvider) --------
    llm_provider: LLMProviderName = Field(default="fake", alias="LLM_PROVIDER")
    embed_provider: EmbedProviderName = Field(default="fake", alias="EMBED_PROVIDER")

    # Model names (provider-specific; safe defaults).
    llm_model: str = Field(default="gemini-1.5-flash", alias="LLM_MODEL")
    embed_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBED_MODEL")

    # Embedding dimension — must match embeddings.vector(N) in the schema.
    embed_dim: int = Field(default=384, alias="EMBED_DIM")

    # --- API security --------------------------------------------------------
    # CORS allowed origins (comma-separated); defaults to localhost for dev
    allowed_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000,http://localhost:8080",
        alias="ALLOWED_ORIGINS",
    )

    # --- Provider credentials (never committed; only for real providers) -----
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="mistral", alias="OLLAMA_MODEL")

    @property
    def offline(self) -> bool:
        """True when both providers are fakes — no network/credentials needed."""
        return self.llm_provider == "fake" and self.embed_provider == "fake"


@lru_cache
def get_settings() -> Settings:
    """Return cached, validated settings (instantiate once per process)."""
    return Settings()
