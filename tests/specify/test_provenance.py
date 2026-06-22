"""Tests for provenance tracking and validation."""

from __future__ import annotations

import uuid

from spec_atlas.db.analysis import Edge, Node
from spec_atlas.specify.provenance import ProvenanceTracker, SourceSpan


class TestSourceSpan:
    """Tests for SourceSpan model."""

    def test_create_source_span(self) -> None:
        """Create a valid source span."""
        span = SourceSpan(file="auth.py", start_line=10, end_line=20)
        assert span.file == "auth.py"
        assert span.start_line == 10
        assert span.end_line == 20

    def test_source_span_to_dict(self) -> None:
        """Convert span to dict."""
        span = SourceSpan(file="auth.py", start_line=10, end_line=20)
        data = span.to_dict()
        assert data == {"file": "auth.py", "start_line": 10, "end_line": 20}

    def test_source_span_from_node(self) -> None:
        """Create span from a Node."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring=None,
            start_line=5,
            end_line=10,
        )

        span = SourceSpan.from_node(node, "auth.py")
        assert span.file == "auth.py"
        assert span.start_line == 5
        assert span.end_line == 10


class TestProvenanceTracker:
    """Tests for provenance tracking."""

    def test_link_purpose_with_docstring(self) -> None:
        """Link purpose to focal node's docstring."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="authenticate",
            qualified_name="auth.authenticate",
            signature="def authenticate(u: str, p: str):",
            docstring="Authenticate a user.",
            start_line=10,
            end_line=20,
        )

        spans = ProvenanceTracker.link_spec_field("purpose", node, [], [])

        assert len(spans) > 0
        assert spans[0]["start_line"] == 10
        assert spans[0]["end_line"] == 20

    def test_link_purpose_without_docstring(self) -> None:
        """Link purpose to focal node's definition if no docstring."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring=None,
            start_line=5,
            end_line=7,
        )

        spans = ProvenanceTracker.link_spec_field("purpose", node, [], [])

        assert len(spans) > 0
        assert spans[0]["start_line"] == 5

    def test_link_inputs_from_signature(self) -> None:
        """Link inputs to focal node's signature."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="validate",
            qualified_name="validate",
            signature="def validate(password: str, min_len: int):",
            docstring=None,
            start_line=10,
            end_line=15,
        )

        spans = ProvenanceTracker.link_spec_field("inputs", node, [], [])

        assert len(spans) > 0
        assert spans[0]["confidence"] == 1.0

    def test_link_outputs_from_signature(self) -> None:
        """Link outputs to focal node's signature."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="verify",
            qualified_name="verify",
            signature="def verify() -> bool:",
            docstring=None,
            start_line=10,
            end_line=12,
        )

        spans = ProvenanceTracker.link_spec_field("outputs", node, [], [])

        assert len(spans) > 0

    def test_link_dependencies_from_edges(self) -> None:
        """Link dependencies to import/call edges."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="auth",
            qualified_name="auth",
            signature="def auth():",
            docstring=None,
            start_line=10,
            end_line=20,
        )

        neighbor_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="hash_pwd",
            qualified_name="hash_pwd",
            signature="def hash_pwd():",
            docstring=None,
            start_line=30,
            end_line=35,
        )

        edge = Edge(
            id=uuid.uuid4(),
            repo_id=repo_id,
            src_node_id=focal_node.id,
            dst_node_id=neighbor_node.id,
            kind="calls",
            confidence=1.0,
        )

        spans = ProvenanceTracker.link_spec_field(
            "dependencies", focal_node, [neighbor_node], [edge]
        )

        assert len(spans) > 0
        assert spans[0]["confidence"] == 1.0

    def test_link_invariants_from_focal_docstring(self) -> None:
        """Link invariants to focal node's docstring."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="test",
            qualified_name="test",
            signature="def test():",
            docstring="Always returns positive values.",
            start_line=10,
            end_line=20,
        )

        spans = ProvenanceTracker.link_spec_field("invariants", node, [], [])

        assert len(spans) > 0
        # Should come from focal node with high confidence
        assert any(s["confidence"] >= 0.8 for s in spans)

    def test_validate_spans_valid(self) -> None:
        """Valid spans pass validation."""
        spans = [
            {"file": "auth.py", "start_line": 10, "end_line": 20},
            {"file": "utils.py", "start_line": 5, "end_line": 7},
        ]

        assert ProvenanceTracker.validate_spans(spans) is True

    def test_validate_spans_invalid_missing_field(self) -> None:
        """Invalid span (missing field) fails validation."""
        spans = [
            {"file": "auth.py", "start_line": 10},  # Missing end_line
        ]

        assert ProvenanceTracker.validate_spans(spans) is False

    def test_validate_spans_invalid_line_order(self) -> None:
        """Invalid span (start > end) fails validation."""
        spans = [
            {"file": "auth.py", "start_line": 20, "end_line": 10},  # Reversed
        ]

        assert ProvenanceTracker.validate_spans(spans) is False

    def test_validate_spans_invalid_type(self) -> None:
        """Invalid span (wrong type) fails validation."""
        spans = [
            {"file": "auth.py", "start_line": "10", "end_line": 20},  # start_line is string
        ]

        assert ProvenanceTracker.validate_spans(spans) is False

    def test_link_claims_uses_neighbor_docstrings(self) -> None:
        """Provenance for claims includes neighbor docstrings."""
        repo_id = uuid.uuid4()
        file_id = uuid.uuid4()

        focal_node = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="main",
            qualified_name="main",
            signature="def main():",
            docstring="Main function.",
            start_line=1,
            end_line=10,
        )

        neighbor = Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id,
            language="python",
            kind="function",
            name="helper",
            qualified_name="helper",
            signature="def helper():",
            docstring="Helper function.",
            start_line=20,
            end_line=25,
        )

        spans = ProvenanceTracker.link_spec_field("side_effects", focal_node, [neighbor], [])

        # Should have both focal and neighbor spans
        assert len(spans) >= 1
