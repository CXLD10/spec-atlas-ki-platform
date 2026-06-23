# Spec-Atlas developer commands.
# Offline & zero-cost by default: `test`/`lint` need no network or credentials.

VENV ?= .venv
PY   := $(VENV)/bin/python
BIN  := $(VENV)/bin

.DEFAULT_GOAL := help

.PHONY: help setup install test test-real lint format clean \
	restart-full restart-backend db-up db-down db-migrate dev-backend dev-frontend dev

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Create the 3.12 venv and install the package (editable, with dev extras)
	uv venv --python 3.12 $(VENV)
	uv pip install --python $(PY) -e ".[dev]"

install: ## (Re)install the package into the existing venv
	uv pip install --python $(PY) -e ".[dev]"

# ============================================================================
# MAIN COMMANDS: Use these for development
# ============================================================================

restart-full: db-down db-up db-migrate dev-backend ## 🔄 Full restart: Drop containers, recreate, start backend
	@echo ""
	@echo "╔════════════════════════════════════════════╗"
	@echo "║  Backend ready on http://localhost:8000   ║"
	@echo "║  Run in another terminal:  make dev-frontend"
	@echo "╚════════════════════════════════════════════╝"

restart-backend: db-migrate dev-backend ## 🔄 Quick backend restart: Migrate & start (keeps all data)

# ============================================================================
# DOCKER DATABASE (PostgreSQL + pgvector in containers)
# ============================================================================

db-up: ## Start PostgreSQL in Docker (creates databases automatically)
	@echo "Starting PostgreSQL container..."
	docker-compose up -d postgres
	@echo "Waiting for database to be ready..."
	@docker-compose exec -T postgres pg_isready -U spec_atlas -d spec_atlas_analysis >/dev/null 2>&1 || sleep 3
	@echo "✓ Database ready on localhost:5432"

db-down: ## Stop and remove PostgreSQL container (keeps data volume)
	@echo "Stopping PostgreSQL..."
	docker-compose down postgres || true
	@echo "✓ Database stopped"

db-drop: ## ⚠️  Delete database volume (LOSES ALL DATA)
	@echo "WARNING: This will delete ALL indexed data"
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	docker volume rm spec-atlas-postgres_data || true
	@echo "✓ Data volume deleted"

db-migrate: ## Apply Alembic migrations to running database
	@echo "Running migrations..."
	export ANALYSIS_DB_URL="postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_analysis" && \
	export SPEC_DB_URL="postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_spec" && \
	$(BIN)/alembic upgrade head
	@echo "✓ Migrations applied"

# ============================================================================
# SERVICE STARTUP (Local development - backend & frontend as host processes)
# ============================================================================

dev-backend: ## Start backend with auto-reload (port 8000) - requires db-up running
	@echo "Starting backend on http://localhost:8000..."
	export PYTHONPATH=/home/cxld/projects/spec-atlas-ki-platform/src && \
	export ANALYSIS_DB_URL="postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_analysis" && \
	export SPEC_DB_URL="postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_spec" && \
	$(BIN)/uvicorn spec_atlas.api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend dev server (port 5173) - run in another terminal
	@echo "Starting frontend on http://localhost:5173..."
	cd frontend && npm run dev

dev: ## Legacy alias: run the API locally with reload
	make dev-backend

# ============================================================================
# TESTING & LINTING
# ============================================================================

# Tests run with fake providers so they never touch the network or cost money.
test: export LLM_PROVIDER=fake
test: export EMBED_PROVIDER=fake
test: export ANALYSIS_DB_URL=postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_analysis
test: export SPEC_DB_URL=postgresql+psycopg://spec_atlas:spec_atlas_dev@localhost:5432/spec_atlas_spec
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

# ============================================================================
# CLEANUP
# ============================================================================

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__ *.egg-info dist build
