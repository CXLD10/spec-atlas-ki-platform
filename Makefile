# Spec-Atlas developer commands.
# Offline & zero-cost by default: `test`/`lint` need no network or credentials.

VENV ?= .venv
PY   := $(VENV)/bin/python
BIN  := $(VENV)/bin

.DEFAULT_GOAL := help

.PHONY: help setup install dev test test-real lint format migrate clean

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Create the 3.12 venv and install the package (editable, with dev extras)
	uv venv --python 3.12 $(VENV)
	uv pip install --python $(PY) -e ".[dev]"

install: ## (Re)install the package into the existing venv
	uv pip install --python $(PY) -e ".[dev]"

dev: ## Run the API locally with reload (GET /health)
	$(BIN)/uvicorn spec_atlas.api.app:app --reload --host 127.0.0.1 --port 8000

# Tests run with fake providers so they never touch the network or cost money.
test: export LLM_PROVIDER=fake
test: export EMBED_PROVIDER=fake
test: ## Run unit + contract + db tests with fake providers (what CI runs)
	$(BIN)/pytest

test-real: ## Optional: run tests against real providers (local only, needs creds)
	$(BIN)/pytest -m real_provider

lint: ## Lint + format check (no changes)
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

format: ## Auto-format and apply safe lint fixes
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

migrate: ## Apply Alembic migrations to both DBs (requires DB URLs)
	$(BIN)/alembic upgrade head

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__ *.egg-info dist build
