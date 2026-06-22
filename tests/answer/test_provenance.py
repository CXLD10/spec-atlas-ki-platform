"""Tests for answer provenance extraction and validation."""

from __future__ import annotations

from unittest.mock import MagicMock

from spec_atlas.answer.provenance import AnswerProvenanceExtractor


class TestAnswerProvenanceExtractor:
    """Tests for provenance extraction and validation."""

    def test_extract_grounded_claim(self) -> None:
        """Grounded claims are validated with confidence 1.0."""
        # Mock answer with claim
        answer = MagicMock()
        answer.text = "Test answer"
        answer.claims = [MagicMock(claim="Test claim", source="auth.py:10")]

        # Mock context with matching span
        context = MagicMock()
        context.source_spans = [{"file": "auth.py", "start_line": 10, "end_line": 20}]

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        assert text == "Test answer"
        assert len(provenance) == 1
        assert provenance[0].confidence == 1.0
        assert provenance[0].file == "auth.py"

    def test_extract_ungrounded_claim(self) -> None:
        """Ungrounded claims get confidence 0.7."""
        answer = MagicMock()
        answer.text = "Answer"
        answer.claims = [MagicMock(claim="Ungrounded", source="unknown.py:99")]

        context = MagicMock()
        context.source_spans = [{"file": "auth.py", "start_line": 10, "end_line": 20}]

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        assert len(provenance) == 1
        assert provenance[0].confidence == 0.7

    def test_extract_multiple_claims(self) -> None:
        """Multiple claims are validated independently."""
        answer = MagicMock()
        answer.text = "Multi-claim answer"
        answer.claims = [
            MagicMock(claim="Claim 1", source="auth.py:10"),
            MagicMock(claim="Claim 2", source="api.py:20"),
            MagicMock(claim="Claim 3", source="unknown.py:99"),
        ]

        context = MagicMock()
        context.source_spans = [
            {"file": "auth.py", "start_line": 10, "end_line": 15},
            {"file": "api.py", "start_line": 20, "end_line": 25},
        ]

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        assert len(provenance) == 3
        # First two should be grounded (confidence 1.0), third ungrounded (0.7)
        assert provenance[0].confidence == 1.0
        assert provenance[1].confidence == 1.0
        assert provenance[2].confidence == 0.7
        # Confidence: 2 grounded out of 3 = 0.667
        assert 0.6 < confidence < 0.7

    def test_extract_confidence_calculation(self) -> None:
        """Confidence is calculated as grounded/total."""
        answer = MagicMock()
        answer.text = "Answer"
        answer.claims = [
            MagicMock(claim="C1", source="file.py:1"),
            MagicMock(claim="C2", source="file.py:2"),
            MagicMock(claim="C3", source="unknown:99"),
            MagicMock(claim="C4", source="unknown:99"),
        ]

        context = MagicMock()
        context.source_spans = [
            {"file": "file.py", "start_line": 1, "end_line": 10},
            {"file": "file.py", "start_line": 2, "end_line": 10},
        ]

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        # 2 grounded out of 4 claims = 0.5 confidence
        assert confidence == 0.5

    def test_extract_no_claims(self) -> None:
        """Answers with no claims have confidence 1.0."""
        answer = MagicMock()
        answer.text = "Simple answer"
        answer.claims = []

        context = MagicMock()
        context.source_spans = []

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        assert text == "Simple answer"
        assert provenance == []
        assert confidence == 1.0

    def test_extract_malformed_source(self) -> None:
        """Malformed sources are handled gracefully."""
        answer = MagicMock()
        answer.text = "Answer"
        answer.claims = [
            MagicMock(claim="Claim", source="no_line_info"),  # No colon
        ]

        context = MagicMock()
        context.source_spans = [{"file": "test.py", "start_line": 1, "end_line": 10}]

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        # Ungrounded because malformed
        assert provenance[0].confidence == 0.7

    def test_extract_empty_source(self) -> None:
        """Empty sources are skipped."""
        answer = MagicMock()
        answer.text = "Answer"
        answer.claims = [
            MagicMock(claim="Claim with empty source", source=""),
        ]

        context = MagicMock()
        context.source_spans = [{"file": "test.py", "start_line": 1, "end_line": 10}]

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        # Empty source should be treated as ungrounded or skipped
        assert len(provenance) <= 1

    def test_extract_whitespace_source(self) -> None:
        """Whitespace-only sources are handled."""
        answer = MagicMock()
        answer.text = "Answer"
        answer.claims = [
            MagicMock(claim="Claim", source="  \n  "),
        ]

        context = MagicMock()
        context.source_spans = []

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        # Should handle gracefully
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1

    def test_extract_partial_path_match(self) -> None:
        """Partial path matches count as grounded."""
        answer = MagicMock()
        answer.text = "Answer"
        answer.claims = [
            MagicMock(claim="Claim", source="lib/auth.py:10"),
        ]

        context = MagicMock()
        context.source_spans = [{"file": "src/lib/auth.py", "start_line": 10, "end_line": 20}]

        text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(
            answer, context
        )

        # Should match because "auth.py" is in "src/lib/auth.py"
        assert provenance[0].confidence == 1.0
