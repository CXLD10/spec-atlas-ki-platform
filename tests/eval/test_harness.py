"""Tests for EvalHarness (F-016 T-016.2).

All offline — fake providers, no DB or network required.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from spec_atlas.eval.harness import EvalHarness, EvalReport, Question


def _make_session_factory(nodes=None):
    """Return a session factory that yields a mock analysis DB session."""
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = nodes or []
    mock_session.query.return_value.scalar.return_value = 0  # no embeddings

    def factory():
        return mock_session

    return factory


class TestEvalHarnessReportsMetrics:
    """Verify EvalHarness produces well-structured EvalReport objects."""

    def _make_harness(self):
        from spec_atlas.embed.fake import FakeEmbeddingProvider
        from spec_atlas.llm.fake import FakeLLMProvider

        return EvalHarness(
            analysis_session_factory=_make_session_factory(),
            spec_session_factory=_make_session_factory(),
            llm_provider=FakeLLMProvider(),
            embedding_provider=FakeEmbeddingProvider(),
            repo_id="test-repo",
        )

    def test_eval_harness_reports_metrics(self) -> None:
        """run_eval_suite on 3 fixture questions returns an EvalReport with metrics.

        This is the primary acceptance test for F-016 T-016.2.
        """
        harness = self._make_harness()

        questions = [
            Question(
                text="How does authentication work?",
                golden_answer="Authentication uses JWT tokens.",
                golden_spans=[{"file": "src/auth.py", "start_line": 1, "end_line": 50}],
            ),
            Question(
                text="What are the main dependencies?",
                golden_answer="The project uses FastAPI and SQLAlchemy.",
                golden_spans=[{"file": "requirements.txt", "start_line": 1, "end_line": 20}],
            ),
            Question(
                text="How is data persisted?",
                golden_answer="Data is stored in PostgreSQL via SQLAlchemy ORM.",
                golden_spans=[],
            ),
        ]

        report = harness.run_eval_suite(questions)

        assert isinstance(report, EvalReport)
        assert len(report.question_results) == 3

        # Verify required metric fields exist and are valid
        assert 0.0 <= report.avg_citation_accuracy_built <= 1.0
        assert 0.0 <= report.avg_citation_accuracy_baseline <= 1.0
        assert report.avg_context_tokens_built >= 0
        assert report.avg_context_tokens_baseline >= 0
        assert report.avg_latency_built >= 0.0
        assert report.avg_latency_baseline >= 0.0
        assert report.winner in ("built", "baseline", "tie")

    def test_run_question_returns_question_result(self) -> None:
        """run_question returns a QuestionResult with both pipeline results."""
        from spec_atlas.eval.harness import QuestionResult

        harness = self._make_harness()
        q = Question(
            text="ping",
            golden_answer="pong",
            golden_spans=[],
        )
        result = harness.run_question(q)
        assert isinstance(result, QuestionResult)
        assert result.question == "ping"
        assert isinstance(result.built.answer, str)
        assert isinstance(result.baseline.answer, str)
        assert result.built.latency_sec >= 0
        assert result.baseline.latency_sec >= 0

    def test_report_summary_is_readable_string(self) -> None:
        """EvalReport.summary() returns a non-empty human-readable string."""
        harness = self._make_harness()
        report = harness.run_eval_suite([
            Question(text="test?", golden_answer="yes", golden_spans=[])
        ])
        summary = report.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Citation accuracy" in summary or "citation" in summary.lower()

    def test_empty_question_set_returns_empty_report(self) -> None:
        """run_eval_suite on an empty list returns a valid empty EvalReport."""
        harness = self._make_harness()
        report = harness.run_eval_suite([])
        assert isinstance(report, EvalReport)
        assert report.question_results == []

    def test_citation_accuracy_one_when_no_golden_spans(self) -> None:
        """Questions with no golden spans get citation_accuracy=1.0 (undefined → pass)."""
        harness = self._make_harness()
        q = Question(text="any question?", golden_answer="answer", golden_spans=[])
        result = harness.run_question(q)
        assert result.citation_accuracy_built == 1.0
        assert result.citation_accuracy_baseline == 1.0
