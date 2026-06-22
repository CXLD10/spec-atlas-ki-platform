# Multi-stage build: deps → app
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations

# Install dependencies
RUN pip install --no-cache-dir -e .

# Final stage: runtime
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies: psql (migrations/debug), curl (HEALTHCHECK),
# git (RepoResolver clones repos to ingest via `git clone`)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app files
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run migrations on startup, then start uvicorn
CMD alembic upgrade head && \
    uvicorn spec_atlas.api.app:app --host 0.0.0.0 --port 8000
