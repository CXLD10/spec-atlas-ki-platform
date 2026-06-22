# ADR-0002: Toolchain (Python 3.12 via uv) and offline-fake provider defaults

Status: accepted
Context: F-000 (T-000.1) needs a reproducible Python 3.12 toolchain and a default
configuration that boots and tests with **no network, no credentials, no cost**
(NFR: $0; testing-standard: offline fakes). ARCHITECTURE.md pins Python 3.12 and
names Gemini/Groq + local fastembed as the *real* provider defaults. The dev/CI
machine here had only Python 3.10 and no Docker/Postgres.

## Decision

1. **Python 3.12 via `uv`.** The interpreter is a prebuilt standalone CPython 3.12
   managed by `uv` (`uv python install 3.12`); the project venv is created with
   `uv venv --python 3.12` and the package installed editable (`make setup`).
   `requires-python = ">=3.12"` per spec. Rationale: no `sudo`/system changes, no
   source compile, reproducible across machines.

2. **Providers default to `fake`.** `config.Settings` defaults `LLM_PROVIDER=fake`
   and `EMBED_PROVIDER=fake` so the app boots and the full test suite runs offline
   with zero credentials. Real providers (Gemini/Groq/Ollama, fastembed) are
   **opt-in via env**. This refines — does not contradict — ARCHITECTURE.md:63:
   the *real* defaults remain Gemini/Groq + fastembed when a user selects them.

3. **DB URLs are optional.** `ANALYSIS_DB_URL`/`SPEC_DB_URL` default to unset so the
   app constructs without a database; migrations and DB-backed tests require them
   and are skipped offline (see the `db` pytest marker).

## Alternatives considered
- System Python / deadsnakes apt: needs `sudo` (unavailable non-interactively here).
- pyenv: compiles from source, needs build deps; slower and less hermetic than uv.
- Defaulting to real providers: would require credentials/network just to boot — breaks
  the offline-first, zero-cost guarantee and CI.

## Consequences
- `make setup` depends on `uv` being installed (it is; documented in the README/Makefile).
- New contributors get a working offline build with no secrets; real providers and a
  Postgres are explicitly opt-in via `.env` (documented in `.env.example`).
- Cost-neutral; no paid dependency introduced.
