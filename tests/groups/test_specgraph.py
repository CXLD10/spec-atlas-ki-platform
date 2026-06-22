"""Tests for spec graph building from L1 edges."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from spec_atlas.groups.specgraph import SpecGraphBuilder


class TestSpecGraphBuilder:
    """Tests for spec graph edge creation from L1 edges."""

    def test_build_edges_empty_edges(self) -> None:
        """Building edges with no L1 edges returns empty list."""
        groups = []
        specs = []
        edges = []

        result = SpecGraphBuilder.build_edges(
            repo_id=uuid.uuid4(),
            user_id="test_user",
            repo_name="test_repo",
            groups=groups,
            specs=specs,
            edges=edges,
            session=MagicMock(),
        )

        assert result == []

    def test_build_edges_single_cross_group_edge(self) -> None:
        """Single L1 edge crossing groups creates a spec edge."""
        group1_id = uuid.uuid4()
        group2_id = uuid.uuid4()
        node1_id = uuid.uuid4()
        node2_id = uuid.uuid4()

        # Create groups with specs
        group1 = MagicMock()
        group1.id = group1_id
        group1.member_node_ids = [node1_id]
        group1.member_spec_refs = ["auth"]

        group2 = MagicMock()
        group2.id = group2_id
        group2.member_node_ids = [node2_id]
        group2.member_spec_refs = ["token-service"]

        # Create L1 edge
        edge = MagicMock()
        edge.src_node_id = node1_id
        edge.dst_node_id = node2_id
        edge.kind = "imports"

        mock_session = MagicMock()

        result = SpecGraphBuilder.build_edges(
            repo_id=uuid.uuid4(),
            user_id="test_user",
            repo_name="test_repo",
            groups=[group1, group2],
            specs=[],
            edges=[edge],
            session=mock_session,
        )

        assert len(result) == 1
        assert result[0].src_component_ref == "auth"
        assert result[0].dst_component_ref == "token-service"
        assert result[0].kind == "depends-on"
        assert result[0].derived_from == "imports"

    def test_build_edges_same_group_skipped(self) -> None:
        """L1 edge within same group is skipped."""
        group_id = uuid.uuid4()
        node1_id = uuid.uuid4()
        node2_id = uuid.uuid4()

        group = MagicMock()
        group.id = group_id
        group.member_node_ids = [node1_id, node2_id]
        group.member_spec_refs = ["auth"]

        edge = MagicMock()
        edge.src_node_id = node1_id
        edge.dst_node_id = node2_id
        edge.kind = "calls"

        result = SpecGraphBuilder.build_edges(
            repo_id=uuid.uuid4(),
            user_id="test_user",
            repo_name="test_repo",
            groups=[group],
            specs=[],
            edges=[edge],
            session=MagicMock(),
        )

        assert len(result) == 0

    def test_build_edges_kind_mapping(self) -> None:
        """L1 edge kinds are correctly mapped to L3 kinds."""
        group1_id = uuid.uuid4()
        group2_id = uuid.uuid4()
        node1_id = uuid.uuid4()
        node2_id = uuid.uuid4()

        group1 = MagicMock()
        group1.id = group1_id
        group1.member_node_ids = [node1_id]
        group1.member_spec_refs = ["src"]

        group2 = MagicMock()
        group2.id = group2_id
        group2.member_node_ids = [node2_id]
        group2.member_spec_refs = ["dst"]

        test_cases = [
            ("imports", "depends-on"),
            ("calls", "depends-on"),
            ("inherits", "depends-on"),
            ("defines", "part-of"),
        ]

        for l1_kind, expected_l3_kind in test_cases:
            edge = MagicMock()
            edge.src_node_id = node1_id
            edge.dst_node_id = node2_id
            edge.kind = l1_kind

            result = SpecGraphBuilder.build_edges(
                repo_id=uuid.uuid4(),
                user_id="test_user",
                repo_name="test_repo",
                groups=[group1, group2],
                specs=[],
                edges=[edge],
                session=MagicMock(),
            )

            assert len(result) == 1
            assert result[0].kind == expected_l3_kind

    def test_build_edges_deduplicates(self) -> None:
        """Duplicate edges (same src/dst/kind) are not created."""
        group1_id = uuid.uuid4()
        group2_id = uuid.uuid4()
        node1_id = uuid.uuid4()
        node2_id = uuid.uuid4()
        node3_id = uuid.uuid4()

        group1 = MagicMock()
        group1.id = group1_id
        group1.member_node_ids = [node1_id, node3_id]
        group1.member_spec_refs = ["src"]

        group2 = MagicMock()
        group2.id = group2_id
        group2.member_node_ids = [node2_id]
        group2.member_spec_refs = ["dst"]

        # Two L1 edges both go from group1 to group2
        edge1 = MagicMock()
        edge1.src_node_id = node1_id
        edge1.dst_node_id = node2_id
        edge1.kind = "imports"

        edge2 = MagicMock()
        edge2.src_node_id = node3_id
        edge2.dst_node_id = node2_id
        edge2.kind = "imports"

        result = SpecGraphBuilder.build_edges(
            repo_id=uuid.uuid4(),
            user_id="test_user",
            repo_name="test_repo",
            groups=[group1, group2],
            specs=[],
            edges=[edge1, edge2],
            session=MagicMock(),
        )

        # Should be 1 edge, not 2 (deduped)
        assert len(result) == 1

    def test_build_edges_multiple_specs_per_group(self) -> None:
        """Group with multiple specs creates cartesian product of edges."""
        group1_id = uuid.uuid4()
        group2_id = uuid.uuid4()
        node1_id = uuid.uuid4()
        node2_id = uuid.uuid4()

        group1 = MagicMock()
        group1.id = group1_id
        group1.member_node_ids = [node1_id]
        group1.member_spec_refs = ["auth", "crypto"]

        group2 = MagicMock()
        group2.id = group2_id
        group2.member_node_ids = [node2_id]
        group2.member_spec_refs = ["storage"]

        edge = MagicMock()
        edge.src_node_id = node1_id
        edge.dst_node_id = node2_id
        edge.kind = "calls"

        result = SpecGraphBuilder.build_edges(
            repo_id=uuid.uuid4(),
            user_id="test_user",
            repo_name="test_repo",
            groups=[group1, group2],
            specs=[],
            edges=[edge],
            session=MagicMock(),
        )

        # Should have 2 edges: auth→storage, crypto→storage
        assert len(result) == 2
        refs = {(e.src_component_ref, e.dst_component_ref) for e in result}
        assert ("auth", "storage") in refs
        assert ("crypto", "storage") in refs

    def test_persist_edges(self) -> None:
        """Persisting edges adds and commits them to session."""
        edge = MagicMock()
        edge.kind = "depends-on"

        mock_session = MagicMock()

        SpecGraphBuilder.persist_edges([edge], mock_session)

        mock_session.add.assert_called_once_with(edge)
        mock_session.commit.assert_called_once()
