"""Unit tests for the transient retry/backoff helper (offline, fast)."""

from __future__ import annotations

import pytest

from spec_atlas.llm.base import TransientLLMError, transient_retry

# Tiny delays so the backoff is exercised without slowing the suite.
_fast_retry = transient_retry(attempts=3, base_delay=0.001, max_delay=0.01)


def test_retries_then_succeeds() -> None:
    calls = {"n": 0}

    @_fast_retry
    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientLLMError("429")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_gives_up_after_attempts_and_reraises() -> None:
    calls = {"n": 0}

    @_fast_retry
    def always_429() -> str:
        calls["n"] += 1
        raise TransientLLMError("429")

    with pytest.raises(TransientLLMError):
        always_429()
    assert calls["n"] == 3  # exactly `attempts` tries, then reraise


def test_non_transient_error_not_retried() -> None:
    calls = {"n": 0}

    @_fast_retry
    def boom() -> str:
        calls["n"] += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError):
        boom()
    assert calls["n"] == 1  # not retried
