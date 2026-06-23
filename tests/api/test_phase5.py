"""Phase 5 acceptance tests: drift detection, eval harness, TS tree-sitter, rate limiting."""


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimitEnforced:
    """Verify slowapi rate limiting enforces 429 when the limit is exceeded."""

    def test_rate_limit_enforced(self) -> None:
        """A rate-limited endpoint returns 429 after the limit is exceeded.

        Uses a standalone test app with a 1/minute limit so the test is
        self-contained and doesn't depend on the production rate limits.
        """
        pytest = __import__("pytest")
        slowapi = pytest.importorskip("slowapi")

        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address

        test_limiter = Limiter(key_func=get_remote_address)
        test_app = FastAPI()
        test_app.state.limiter = test_limiter
        test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        @test_app.get("/probe")
        @test_limiter.limit("1/minute")
        async def probe(request: Request):
            return {"ok": True}

        client = TestClient(test_app, raise_server_exceptions=False)

        resp1 = client.get("/probe")
        assert resp1.status_code == 200, f"First request should succeed: {resp1.text}"

        resp2 = client.get("/probe")
        assert resp2.status_code == 429, (
            f"Second request to 1/minute endpoint should return 429, got {resp2.status_code}"
        )

    def test_app_state_limiter_registered(self) -> None:
        """The production app registers the slowapi limiter on app.state."""
        pytest = __import__("pytest")
        pytest.importorskip("slowapi")

        from spec_atlas.api.app import create_app
        from spec_atlas.config import get_settings

        app = create_app(get_settings())
        assert hasattr(app.state, "limiter"), (
            "app.state.limiter not set — slowapi exception handler won't fire"
        )

    def test_ingest_endpoint_has_rate_limit_applied(self) -> None:
        """POST /api/ingest has a rate limit decorator (not a no-op)."""
        from spec_atlas.api.ingest import HAS_LIMITER, _apply_rate_limit

        assert HAS_LIMITER is True, "slowapi not available — cannot verify rate limiting"

        # _apply_rate_limit must return a wrapped function (not identity) when limiter available
        def dummy(request=None, **kwargs):
            return None

        wrapped = _apply_rate_limit(dummy)
        # slowapi-wrapped functions have __wrapped__ or a different __qualname__
        assert wrapped is not dummy, (
            "_apply_rate_limit returned the original function unchanged — rate limiting is still a no-op"
        )

    def test_answer_endpoint_has_rate_limit_applied(self) -> None:
        """POST /api/ask has a rate limit decorator (not a no-op)."""
        from spec_atlas.api.answer import HAS_LIMITER, _apply_rate_limit

        assert HAS_LIMITER is True

        def dummy(request=None, **kwargs):
            return None

        wrapped = _apply_rate_limit(dummy)
        assert wrapped is not dummy, (
            "answer._apply_rate_limit still a no-op — rate limiting not enforced"
        )


# ---------------------------------------------------------------------------
# Drift detection (end-to-end module smoke)
# ---------------------------------------------------------------------------

class TestDriftModuleSmoke:
    """Smoke tests for the drift detection module structure."""

    def test_drift_module_importable(self) -> None:
        """spec_atlas.drift.detector is importable and exposes expected symbols."""
        from spec_atlas.drift.detector import DriftDetector, DriftReport, compute_fingerprint

        assert callable(compute_fingerprint)
        assert callable(DriftDetector.detect_drift)
        assert callable(DriftDetector.mark_stale)

    def test_spec_model_has_staleness_detected_at(self) -> None:
        """Spec ORM model has the staleness_detected_at column added in migration 0005."""
        from spec_atlas.db.spec import Spec
        from sqlalchemy import inspect as sa_inspect

        mapper = sa_inspect(Spec)
        col_names = {col.key for col in mapper.columns}
        assert "staleness_detected_at" in col_names, (
            "Spec model missing staleness_detected_at — run migration 0005"
        )

    def test_migration_0005_exists(self) -> None:
        """Alembic migration 0005 file exists for the staleness_detected_at column."""
        from pathlib import Path

        migrations_dir = Path(__file__).parent.parent.parent / "migrations" / "versions"
        migration_files = list(migrations_dir.glob("0005_*.py"))
        assert migration_files, (
            f"No 0005_*.py migration found in {migrations_dir}"
        )


# ---------------------------------------------------------------------------
# Eval harness (module structure)
# ---------------------------------------------------------------------------

class TestEvalHarnessModuleSmoke:
    """Smoke tests for the eval harness module structure."""

    def test_eval_modules_importable(self) -> None:
        """spec_atlas.eval.baseline and harness are importable."""
        from spec_atlas.eval.baseline import BaselineRetriever
        from spec_atlas.eval.harness import EvalHarness, Question

        assert callable(BaselineRetriever)
        assert callable(EvalHarness)
        assert callable(Question)

    def test_baseline_retriever_interface(self) -> None:
        """BaselineRetriever has the required method signatures."""
        from spec_atlas.eval.baseline import BaselineRetriever
        import inspect

        assert hasattr(BaselineRetriever, "retrieve")
        assert hasattr(BaselineRetriever, "answer_from_nodes")
        assert hasattr(BaselineRetriever, "context_token_estimate")
