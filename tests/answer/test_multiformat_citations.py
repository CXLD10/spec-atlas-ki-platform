"""Tests for multi-format (code + PDF) citations in answer pipeline."""

from __future__ import annotations

from spec_atlas.answer.engine import Answer, Claim
from spec_atlas.answer.provenance import AnswerProvenanceExtractor
from spec_atlas.db.analysis import Group
from spec_atlas.retrieve.descent import Context


def create_mock_context_with_code_sources() -> Context:
    """Create mock context with code source spans."""
    mock_group = Group(
        id="00000000-0000-0000-0000-000000000001",
        repo_id="00000000-0000-0000-0000-000000000001",
        path="root",
        title="Root",
        level=0,
    )

    return Context(
        matched_group=mock_group,
        child_groups=[],
        specs=[],
        source_spans=[
            {"file": "src/main.py", "start_line": 10, "end_line": 15},
            {"file": "src/utils.py", "start_line": 42, "end_line": 50},
        ],
        tree_path=[mock_group],
    )


def test_answer_with_code_citation():
    """Test answer with code source citation."""
    answer = Answer(
        text="The main function processes data",
        claims=[
            Claim(
                claim="The main function is defined in src/main.py",
                source="src/main.py:10",
            ),
        ],
        strategy_used="vector_search",
    )

    context = create_mock_context_with_code_sources()
    text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(answer, context)

    assert len(provenance) == 1
    assert provenance[0].file == "src/main.py"
    assert provenance[0].start_line == 10
    assert provenance[0].confidence == 1.0


def test_answer_with_pdf_citation():
    """Test answer with PDF source citation."""
    answer = Answer(
        text="The documentation states that validation is required",
        claims=[
            Claim(
                claim="Input validation is required for security",
                source="manual.pdf:p.5",
            ),
        ],
        strategy_used="vector_search",
    )

    context = create_mock_context_with_code_sources()
    text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(answer, context)

    # PDF citation is ungrounded (not in code spans), so confidence = 0.7
    assert len(provenance) == 1
    assert provenance[0].file == "manual.pdf:p.5"
    assert provenance[0].confidence == 0.7


def test_answer_with_mixed_citations():
    """Test answer with both code and PDF citations."""
    answer = Answer(
        text="The implementation validates input as documented",
        claims=[
            Claim(
                claim="The utils module validates input",
                source="src/utils.py:42",
            ),
            Claim(
                claim="Input validation is a security best practice",
                source="security_guide.pdf:p.12",
            ),
        ],
        strategy_used="vector_search",
    )

    context = create_mock_context_with_code_sources()
    text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(answer, context)

    # Should have both citations
    assert len(provenance) == 2

    # Code citation should be grounded (confidence=1.0)
    code_prov = [p for p in provenance if "src/utils.py" in p.file][0]
    assert code_prov.confidence == 1.0
    assert code_prov.start_line == 42

    # PDF citation should be ungrounded (confidence=0.7)
    pdf_prov = [p for p in provenance if ".pdf" in p.file][0]
    assert pdf_prov.confidence == 0.7


def test_confidence_calculation_mixed_sources():
    """Test overall confidence score with mixed grounded/ungrounded claims."""
    answer = Answer(
        text="Implementation and docs agree",
        claims=[
            Claim(claim="Code does validation", source="src/main.py:10"),  # grounded
            Claim(claim="Docs recommend validation", source="guide.pdf:p.5"),  # ungrounded
        ],
        strategy_used="vector_search",
    )

    context = create_mock_context_with_code_sources()
    text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(answer, context)

    # 1 grounded + 1 ungrounded = 50% confidence
    assert confidence == 0.5


def test_ungrounded_code_citation():
    """Test code citation that doesn't match any source span."""
    answer = Answer(
        text="There is a missing function",
        claims=[
            Claim(
                claim="Function is defined elsewhere",
                source="src/missing.py:99",
            ),
        ],
        strategy_used="vector_search",
    )

    context = create_mock_context_with_code_sources()
    text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(answer, context)

    # Ungrounded code citation
    assert len(provenance) == 1
    assert provenance[0].confidence == 0.7


def test_empty_answer():
    """Test answer with no claims."""
    answer = Answer(
        text="I don't know",
        claims=[],
        strategy_used="vector_search",
    )

    context = create_mock_context_with_code_sources()
    text, provenance, confidence = AnswerProvenanceExtractor.extract_and_validate(answer, context)

    assert len(provenance) == 0
    assert confidence == 1.0
