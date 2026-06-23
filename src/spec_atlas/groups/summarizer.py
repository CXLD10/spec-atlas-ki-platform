"""Generate LLM-based summaries for groups with provenance tracking."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Edge, Group, Node
from spec_atlas.db.spec import Spec
from spec_atlas.llm.base import LLMProvider

if TYPE_CHECKING:
    pass


class GroupSummarizer:
    """Generate human-readable group summaries with provenance."""

    @staticmethod
    def summarize(
        group: Group,
        member_nodes: list[Node],
        member_edges: list[Edge],
        related_specs: list[Spec],
        llm_provider: LLMProvider,
        session: Session | None = None,
    ) -> tuple[str, dict]:
        """Generate a markdown summary for a group.

        Args:
            group: The Group object to summarize.
            member_nodes: All nodes that belong to this group.
            member_edges: All edges within this group (not crossing groups).
            related_specs: Specs linked to this group.
            llm_provider: LLM provider to generate the summary.
            session: Analysis DB session, used to resolve member nodes' file
                paths for provenance. If omitted, provenance falls back to
                the raw file_id (e.g. in unit tests with mocked nodes).

        Returns:
            Tuple of (summary_markdown, provenance_dict).
            - summary_markdown: Human-readable markdown string
            - provenance_dict: {section_name: [{file, start_line, end_line}, ...]}
        """
        # Build the prompt
        prompt = GroupSummarizer._build_prompt(group, member_nodes, member_edges, related_specs)

        # Call LLM. LLMProvider.complete() is sync in the ABC, but Groq/Ollama
        # implement it as async — bridge with asyncio.run() when needed (safe:
        # always called from a sync context, never inside a running loop).
        messages = [{"role": "user", "content": prompt}]
        maybe_response = llm_provider.complete(messages)
        response = (
            asyncio.run(maybe_response) if inspect.isawaitable(maybe_response) else maybe_response
        )

        # Ensure response is a string
        if isinstance(response, dict):
            summary_md = response.get("summary", "")
        else:
            summary_md = str(response)

        # Build provenance
        provenance = GroupSummarizer._build_provenance(group, member_nodes, session)

        return summary_md, provenance

    @staticmethod
    def _build_prompt(
        group: Group,
        member_nodes: list[Node],
        member_edges: list[Edge],
        related_specs: list[Spec],
    ) -> str:
        """Build a prompt for the LLM to summarize the group.

        Args:
            group: The group to summarize.
            member_nodes: Member nodes.
            member_edges: Edges within the group.
            related_specs: Related specs.

        Returns:
            A prompt string.
        """
        lines = [
            "Generate a human-readable group summary (100–300 words, markdown format).\n",
            f"# Group: {group.path or 'root'}",
            f"Title: {group.title}",
            f"Level: {group.level}",
            f"Member count: {len(member_nodes)}",
        ]

        # List member nodes
        if member_nodes:
            lines.append("\n## Member Components:")
            for node in member_nodes[:20]:  # Limit context
                lines.append(f"  - {node.qualified_name} ({node.kind}, {node.language})")
                if node.docstring:
                    lines.append(f"    Doc: {node.docstring[:100]}")

        # List edges within the group
        if member_edges:
            lines.append("\n## Internal Relationships:")
            for edge in member_edges[:10]:  # Limit context
                lines.append(f"  - {edge.kind} (confidence {edge.confidence})")

        # List related specs
        if related_specs:
            lines.append("\n## Related Specs:")
            for spec in related_specs[:5]:
                lines.append(f"  - {spec.component_ref} (v{spec.version})")

        # Task
        lines.extend(
            [
                "\n## Task:",
                "Write a markdown summary with sections like:",
                "- **Purpose**: What this group does collectively",
                "- **Key Components**: Main items in the group",
                "- **Dependencies**: What it depends on",
                "- **Invariants**: Key properties that hold",
                "\nBe grounded in the code. Each claim should be defensible from the "
                "component list.",
                "Return only the markdown, no preamble.",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _file_paths_for_nodes(member_nodes: list[Node], session: Session | None) -> dict:
        """Resolve member nodes' file_id -> File.path, via one batched query.

        Falls back to ``str(file_id)`` per node when no session is given
        (e.g. unit tests with mocked nodes) or a file_id has no matching row.
        """
        if not session or not member_nodes:
            return {}

        from spec_atlas.db.analysis import File

        file_ids = {node.file_id for node in member_nodes}
        rows = session.query(File).filter(File.id.in_(file_ids)).all()
        return {row.id: row.path for row in rows}

    @staticmethod
    def _build_provenance(
        group: Group, member_nodes: list[Node], session: Session | None = None
    ) -> dict:
        """Build provenance mapping for the group summary.

        Args:
            group: The group.
            member_nodes: Member nodes (source of spans).
            session: Analysis DB session, used to resolve real file paths.

        Returns:
            Provenance dict: {section: [{file, start_line, end_line}, ...]}
        """
        provenance = {}
        file_paths = GroupSummarizer._file_paths_for_nodes(member_nodes, session)

        # For each section, map to the spans of member nodes
        if member_nodes:
            # "Key Components" comes from the member nodes themselves
            key_components_spans = [
                {
                    "file": file_paths.get(node.file_id, str(node.file_id)),
                    "start_line": node.start_line,
                    "end_line": node.end_line,
                }
                for node in member_nodes
            ]
            provenance["Key Components"] = key_components_spans

            # "Purpose" comes from the first documented node
            for node in member_nodes:
                if node.docstring:
                    provenance["Purpose"] = [
                        {
                            "file": file_paths.get(node.file_id, str(node.file_id)),
                            "start_line": node.start_line,
                            "end_line": node.end_line,
                        }
                    ]
                    break

        return provenance

    @staticmethod
    def compute_fingerprint(member_nodes: list[Node]) -> str:
        """Compute a fingerprint of the group's source content.

        Args:
            member_nodes: Member nodes.

        Returns:
            A hex string (SHA256 hash of concatenated spans).
        """
        span_strs = [
            f"{node.file_id}:{node.start_line}:{node.end_line}"
            for node in sorted(member_nodes, key=lambda n: (str(n.file_id), n.start_line))
        ]
        content = "".join(span_strs)
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def persist_group_summary(
        group: Group,
        summary_md: str,
        member_nodes: list[Node],
        session: Session,
    ) -> Group:
        """Update and persist the group with its summary.

        Args:
            group: The group to update (mutated).
            summary_md: The summary markdown.
            member_nodes: Member nodes (for fingerprint).
            session: Analysis DB session.

        Returns:
            The updated group.
        """
        group.summary_md = summary_md
        group.source_fingerprint = GroupSummarizer.compute_fingerprint(member_nodes)

        session.merge(group)
        session.commit()

        return group
