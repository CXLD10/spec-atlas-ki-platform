"""Tests for group summary generation."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from spec_atlas.groups.summarizer import GroupSummarizer


class TestGroupSummarizer:
    """Tests for group summarization and provenance."""

    def test_summarize_calls_llm(self) -> None:
        """Summarize calls the LLM provider with a prompt."""
        group = MagicMock()
        group.path = "auth"
        group.title = "Authentication"
        group.level = 1

        node = MagicMock()
        node.qualified_name = "login"
        node.kind = "function"
        node.language = "python"
        node.docstring = "Login handler"
        node.file_id = uuid.uuid4()
        node.start_line = 10
        node.end_line = 25

        llm_provider = MagicMock()
        llm_provider.complete.return_value = "# Authentication\nHandles user login."

        summary, provenance = GroupSummarizer.summarize(
            group,
            [node],
            [],
            [],
            llm_provider,
        )

        assert "Authentication" in summary
        llm_provider.complete.assert_called_once()

    def test_summarize_with_dict_response(self) -> None:
        """Summarize handles dict responses from LLM."""
        group = MagicMock()
        group.path = "api"
        group.title = "API"
        group.level = 1

        llm_provider = MagicMock()
        llm_provider.complete.return_value = {"summary": "API layer"}

        summary, _ = GroupSummarizer.summarize(
            group,
            [],
            [],
            [],
            llm_provider,
        )

        assert summary == "API layer"

    def test_build_prompt_includes_group_info(self) -> None:
        """Prompt includes group path, title, and member count."""
        group = MagicMock()
        group.path = "db/migrations"
        group.title = "Migrations"
        group.level = 2

        node = MagicMock()
        node.qualified_name = "migrate_v1"
        node.kind = "function"
        node.language = "python"
        node.docstring = None

        prompt = GroupSummarizer._build_prompt(group, [node], [], [])

        assert "db/migrations" in prompt
        assert "Migrations" in prompt
        assert "Member count: 1" in prompt
        assert "migrate_v1" in prompt

    def test_build_prompt_limits_nodes(self) -> None:
        """Prompt limits member nodes to 20."""
        group = MagicMock()
        group.path = ""
        group.title = "root"
        group.level = 0

        nodes = [
            MagicMock(
                qualified_name=f"node{i}",
                kind="function",
                language="python",
                docstring=None,
            )
            for i in range(30)
        ]

        prompt = GroupSummarizer._build_prompt(group, nodes, [], [])

        # First 20 should be included
        assert "node0" in prompt
        assert "node19" in prompt
        # 20-29 should not be mentioned in the prompt
        assert "node20" not in prompt

    def test_build_provenance_from_member_nodes(self) -> None:
        """Provenance maps to member node spans."""
        group = MagicMock()

        node1_id = uuid.uuid4()
        node1 = MagicMock()
        node1.file_id = node1_id
        node1.start_line = 10
        node1.end_line = 20
        node1.docstring = "Handler"

        node2_id = uuid.uuid4()
        node2 = MagicMock()
        node2.file_id = node2_id
        node2.start_line = 30
        node2.end_line = 40
        node2.docstring = None

        provenance = GroupSummarizer._build_provenance(group, [node1, node2])

        assert "Key Components" in provenance
        assert len(provenance["Key Components"]) == 2
        assert "Purpose" in provenance

    def test_compute_fingerprint_deterministic(self) -> None:
        """Fingerprint is deterministic for same nodes."""
        node = MagicMock()
        node.file_id = uuid.uuid4()
        node.start_line = 10
        node.end_line = 20

        fp1 = GroupSummarizer.compute_fingerprint([node])
        fp2 = GroupSummarizer.compute_fingerprint([node])

        assert fp1 == fp2

    def test_compute_fingerprint_differs_by_span(self) -> None:
        """Fingerprint differs for different node spans."""
        node1 = MagicMock()
        node1.file_id = uuid.uuid4()
        node1.start_line = 10
        node1.end_line = 20

        node2 = MagicMock()
        node2.file_id = uuid.uuid4()
        node2.start_line = 30
        node2.end_line = 40

        fp1 = GroupSummarizer.compute_fingerprint([node1])
        fp2 = GroupSummarizer.compute_fingerprint([node2])

        assert fp1 != fp2

    def test_persist_group_summary(self) -> None:
        """Persisting updates summary_md and fingerprint."""
        group = MagicMock()
        node = MagicMock()
        node.file_id = uuid.uuid4()
        node.start_line = 1
        node.end_line = 10

        mock_session = MagicMock()

        result = GroupSummarizer.persist_group_summary(
            group,
            "# Summary\nContent",
            [node],
            mock_session,
        )

        assert result.summary_md == "# Summary\nContent"
        assert result.source_fingerprint is not None
        mock_session.merge.assert_called_once_with(group)
        mock_session.commit.assert_called_once()

    def test_summarize_empty_group(self) -> None:
        """Summarize handles empty group (no member nodes)."""
        group = MagicMock()
        group.path = "empty"
        group.title = "Empty"
        group.level = 1

        llm_provider = MagicMock()
        llm_provider.complete.return_value = "Empty group"

        summary, provenance = GroupSummarizer.summarize(
            group,
            [],
            [],
            [],
            llm_provider,
        )

        assert summary == "Empty group"
        assert provenance == {}
