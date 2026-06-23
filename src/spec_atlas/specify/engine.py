"""Specify engine: generate specs from code graph regions via LLM."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from spec_atlas.specify.schema import spec_json_schema, validate_spec

if TYPE_CHECKING:
    from spec_atlas.db.analysis import Edge, Node
    from spec_atlas.llm import LLMProvider


class SpecifyEngine:
    """Generate structured specs for code regions using LLM."""

    @staticmethod
    def generate(
        focal_node: Node,
        neighbors: list[Node],
        edges: list[Edge],
        llm_provider: LLMProvider,
        focal_file_path: str | None = None,
    ) -> tuple[dict, dict]:
        """Generate a spec for a focal node and its neighbors.

        Args:
            focal_node: The main node (function, class, module) to spec.
            neighbors: Adjacent nodes (callers, callees, base classes, etc.)
            edges: Edges connecting focal node to neighbors.
            llm_provider: LLM provider for generation.
            focal_file_path: Real path of focal_node's file (e.g. "auth/session.py"),
                used for provenance. Falls back to str(focal_node.file_id) if omitted.

        Returns:
            Tuple of (spec_dict, provenance_dict).
                - spec_dict: validated spec content (purpose, inputs, outputs, etc.)
                - provenance_dict: mapping of field names to source spans

        Raises:
            ValueError: If LLM response is invalid or doesn't match schema.
        """
        # Build the prompt
        prompt = _build_prompt(focal_node, neighbors, edges)

        # Call LLM with structured output
        schema_dict = spec_json_schema()
        messages = [{"role": "user", "content": prompt}]

        response = llm_provider.complete(messages, schema=schema_dict)

        # Parse response (can be dict or JSON string)
        if isinstance(response, str):
            spec_content = json.loads(response)
        else:
            spec_content = response

        # Validate against schema
        validated_spec = validate_spec(spec_content)

        # Analyze interconnections
        interconnections = _extract_interconnections(focal_node, neighbors, edges)
        validated_spec["interconnections"] = interconnections

        # Build provenance (map each field to source spans)
        provenance = _build_provenance(focal_node, neighbors, edges, validated_spec, focal_file_path)

        return validated_spec, provenance


def _build_prompt(focal_node: Node, neighbors: list[Node], edges: list[Edge]) -> str:
    """Build a prompt describing the focal node and its context.

    Args:
        focal_node: The node to specify.
        neighbors: Adjacent nodes.
        edges: Relationships.

    Returns:
        A detailed prompt for the LLM.
    """
    lines = [
        "Generate a structured specification for the following code component:\n",
        f"# Focal Component: {focal_node.qualified_name}",
        f"Kind: {focal_node.kind}",
        f"Language: {focal_node.language}",
        f"File: {focal_node.id}  # line {focal_node.start_line}–{focal_node.end_line}",
        f"Signature: {focal_node.signature}",
    ]

    if focal_node.docstring:
        lines.append(f"Docstring: {focal_node.docstring}")

    # Add neighbors
    if neighbors:
        lines.append("\n## Related Components:")
        for neighbor in neighbors[:20]:  # Limit to 20 for context budget
            lines.append(f"  - {neighbor.qualified_name} ({neighbor.kind}, {neighbor.language})")
            if neighbor.docstring:
                lines.append(f"    Doc: {neighbor.docstring[:100]}")

    # Add edges
    if edges:
        lines.append("\n## Relationships:")
        for edge in edges[:10]:  # Limit edges for clarity
            lines.append(f"  - {edge.kind}: (confidence {edge.confidence})")

    lines.extend(
        [
            "\n## Task:",
            "Analyze the component and generate a JSON spec with these fields:",
            "- purpose (string): What does this component do?",
            "- inputs (array): Parameters/inputs it takes (name, type, description)",
            "- outputs (array): Return values/outputs (name, type, description)",
            "- dependencies (array): Component references it depends on",
            "- invariants (array): Guarantees/properties that must hold",
            "- side_effects (array): Effects beyond the main purpose",
            "- failure_modes (array): Possible failures or error conditions",
            "\nBe precise and grounded in the code. If unsure, be conservative.",
            "Return valid JSON matching the schema.",
        ]
    )

    return "\n".join(lines)


def _build_provenance(
    focal_node: Node,
    neighbors: list[Node],
    edges: list[Edge],
    spec: dict,
    focal_file_path: str | None = None,
) -> dict:
    """Build provenance mapping spec fields to source spans.

    Args:
        focal_node: The focal node.
        neighbors: Adjacent nodes.
        edges: Relationships.
        spec: The generated spec.
        focal_file_path: Real path of focal_node's file. Falls back to
            str(focal_node.file_id) when not provided (e.g. no DB lookup
            available), so callers without a session still get a valid,
            if less readable, provenance.

    Returns:
        Provenance dict: {field_name: [{file, start_line, end_line}, ...]}
    """
    provenance = {}
    file_ref = focal_file_path or str(focal_node.file_id)

    # purpose comes from focal node's docstring or definition
    if focal_node.docstring:
        # Docstring spans are roughly the node's start to end
        provenance["purpose"] = [
            {
                "file": file_ref,
                "start_line": focal_node.start_line,
                "end_line": focal_node.end_line,
            }
        ]
    else:
        provenance["purpose"] = [
            {
                "file": file_ref,
                "start_line": focal_node.start_line,
                "end_line": focal_node.start_line,
            }
        ]

    # inputs comes from focal node's signature
    if spec.get("inputs"):
        provenance["inputs"] = [
            {
                "file": file_ref,
                "start_line": focal_node.start_line,
                "end_line": focal_node.start_line + 1,  # Rough span for signature
            }
        ]

    # outputs comes from focal node's signature or docstring
    if spec.get("outputs"):
        provenance["outputs"] = [
            {
                "file": file_ref,
                "start_line": focal_node.start_line,
                "end_line": focal_node.end_line,
            }
        ]

    # dependencies comes from edges
    if spec.get("dependencies"):
        dep_spans = []
        for edge in edges:
            if edge.kind in ("imports", "calls"):
                dep_spans.append(
                    {
                        "file": file_ref,
                        "start_line": focal_node.start_line,
                        "end_line": focal_node.end_line,
                    }
                )
        if dep_spans:
            provenance["dependencies"] = dep_spans

    # invariants/side_effects/failure_modes: best-effort from docstring
    for field in ("invariants", "side_effects", "failure_modes"):
        if spec.get(field):
            provenance[field] = [
                {
                    "file": file_ref,
                    "start_line": focal_node.start_line,
                    "end_line": focal_node.end_line,
                }
            ]

    return provenance


def _extract_interconnections(
    focal_node: Node,
    neighbors: list[Node],
    edges: list[Edge],
) -> list[str]:
    """Extract function/module names called by focal node.

    Args:
        focal_node: The focal node.
        neighbors: Adjacent nodes.
        edges: Relationships.

    Returns:
        List of interconnected function/module names.
    """
    interconnections = set()

    # Extract from edges where focal_node is the source
    for edge in edges:
        if edge.kind in ("calls", "imports", "inherits"):
            for neighbor in neighbors:
                if neighbor.id == edge.dst_node_id:
                    interconnections.add(neighbor.qualified_name or neighbor.name or "unknown")

    return sorted(list(interconnections))[:10]  # Limit to top 10
