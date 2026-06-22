"""Provenance tracking and validation for generated specs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spec_atlas.db.analysis import Edge, Node


@dataclass
class SourceSpan:
    """A source code span with file and line information."""

    file: str
    start_line: int
    end_line: int

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "file": self.file,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }

    @classmethod
    def from_node(cls, node: Node, file_path: str = "") -> SourceSpan:
        """Create a span from a Node."""
        return cls(
            file=file_path or str(node.file_id),
            start_line=node.start_line,
            end_line=node.end_line,
        )


class ProvenanceTracker:
    """Track and validate provenance (source spans) for spec fields."""

    @staticmethod
    def link_spec_field(
        field_name: str,
        focal_node: Node,
        neighbors: list[Node],
        edges: list[Edge],
    ) -> list[dict]:
        """Link a spec field to its source spans.

        Args:
            field_name: Name of the spec field (e.g., "purpose", "dependencies")
            focal_node: The focal node being specified.
            neighbors: Adjacent nodes.
            edges: Relationships from/to focal node.

        Returns:
            List of source span dicts: [{file, start_line, end_line}, ...]
        """
        if field_name == "purpose":
            return _link_purpose(focal_node)
        elif field_name == "inputs":
            return _link_inputs(focal_node)
        elif field_name == "outputs":
            return _link_outputs(focal_node)
        elif field_name == "dependencies":
            return _link_dependencies(focal_node, neighbors, edges)
        elif field_name in ("invariants", "side_effects", "failure_modes"):
            return _link_claims(focal_node, neighbors)
        else:
            return []

    @staticmethod
    def validate_spans(spans: list[dict]) -> bool:
        """Validate that spans have the required structure.

        Args:
            spans: List of {file, start_line, end_line} dicts.

        Returns:
            True if all spans are valid.
        """
        for span in spans:
            if not isinstance(span, dict):
                return False
            if "file" not in span or "start_line" not in span or "end_line" not in span:
                return False
            if not isinstance(span["start_line"], int) or not isinstance(span["end_line"], int):
                return False
            if span["start_line"] > span["end_line"]:
                return False
        return True


def _link_purpose(focal_node: Node) -> list[dict]:
    """Link purpose to focal node's docstring or definition."""
    spans = []
    if focal_node.docstring:
        # Docstring is part of the node's span
        spans.append(
            {
                "file": str(focal_node.file_id),
                "start_line": focal_node.start_line,
                "end_line": focal_node.end_line,
                "confidence": 1.0,
            }
        )
    else:
        # Fall back to the definition span
        spans.append(
            {
                "file": str(focal_node.file_id),
                "start_line": focal_node.start_line,
                "end_line": focal_node.start_line + 1,
                "confidence": 0.8,
            }
        )
    return spans


def _link_inputs(focal_node: Node) -> list[dict]:
    """Link inputs to focal node's signature."""
    if focal_node.signature:
        return [
            {
                "file": str(focal_node.file_id),
                "start_line": focal_node.start_line,
                "end_line": focal_node.start_line + 1,
                "confidence": 1.0,
            }
        ]
    return []


def _link_outputs(focal_node: Node) -> list[dict]:
    """Link outputs to focal node's signature or docstring."""
    spans = []
    if focal_node.signature:
        spans.append(
            {
                "file": str(focal_node.file_id),
                "start_line": focal_node.start_line,
                "end_line": focal_node.start_line + 1,
                "confidence": 1.0,
            }
        )
    elif focal_node.docstring:
        spans.append(
            {
                "file": str(focal_node.file_id),
                "start_line": focal_node.start_line,
                "end_line": focal_node.end_line,
                "confidence": 0.7,
            }
        )
    return spans


def _link_dependencies(
    focal_node: Node,
    neighbors: list[Node],
    edges: list[Edge],
) -> list[dict]:
    """Link dependencies to import/call edges."""
    spans = []
    # For each edge from focal node
    for edge in edges:
        if edge.src_node_id == focal_node.id:
            # Edge goes from focal node to something it imports/calls
            # The span is the focal node's region where the import/call likely is
            if edge.kind in ("imports", "calls"):
                spans.append(
                    {
                        "file": str(focal_node.file_id),
                        "start_line": focal_node.start_line,
                        "end_line": focal_node.end_line,
                        "confidence": edge.confidence,
                    }
                )
    return spans


def _link_claims(
    focal_node: Node,
    neighbors: list[Node],
) -> list[dict]:
    """Link invariants/side_effects/failure_modes to focal or neighbor docstrings."""
    spans = []

    # Primary: focal node's docstring
    if focal_node.docstring:
        spans.append(
            {
                "file": str(focal_node.file_id),
                "start_line": focal_node.start_line,
                "end_line": focal_node.end_line,
                "confidence": 0.9,
            }
        )

    # Secondary: neighbor docstrings (lower confidence)
    for neighbor in neighbors[:5]:  # Limit to top 5
        if neighbor.docstring:
            spans.append(
                {
                    "file": str(neighbor.file_id),
                    "start_line": neighbor.start_line,
                    "end_line": neighbor.end_line,
                    "confidence": 0.5,
                }
            )

    return spans
