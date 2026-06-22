"""Tests for tree descent and context assembly."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from spec_atlas.retrieve.descent import TreeDescent


class TestTreeDescent:
    """Tests for bounded context assembly via tree descent."""

    def test_descend_group_not_found(self) -> None:
        """Descending from non-existent group raises error."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        try:
            TreeDescent.descend(uuid.uuid4(), mock_session)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "not found" in str(e)

    def test_descend_single_group(self) -> None:
        """Descending from a single group returns context."""
        group_id = uuid.uuid4()
        group = MagicMock()
        group.id = group_id
        group.parent_id = None
        group.path = "root"
        group.member_spec_refs = []

        mock_session = MagicMock()

        # Mock the query chain
        def mock_query_factory():
            mock_q = MagicMock()
            mock_q.filter.return_value = mock_q
            mock_q.order_by.return_value = mock_q
            mock_q.first.return_value = group
            mock_q.all.return_value = []
            return mock_q

        mock_session.query.side_effect = lambda x: mock_query_factory()

        result = TreeDescent.descend(group_id, mock_session)

        assert result.matched_group == group
        assert result.child_groups == []
        assert result.specs == []
        assert result.source_spans == []

    def test_descend_with_children(self) -> None:
        """Descending includes immediate child groups."""
        group_id = uuid.uuid4()
        parent_group = MagicMock()
        parent_group.id = group_id
        parent_group.parent_id = None
        parent_group.path = "root"
        parent_group.member_spec_refs = []

        child1 = MagicMock()
        child1.path = "root/auth"

        child2 = MagicMock()
        child2.path = "root/api"

        mock_session = MagicMock()

        # Track query calls to return different values
        call_count = [0]

        def mock_query_factory():
            mock_q = MagicMock()

            def filter_mock(*args, **kwargs):
                call_count[0] += 1
                inner_q = MagicMock()
                inner_q.filter.return_value = inner_q
                inner_q.order_by.return_value = inner_q

                if call_count[0] == 1:
                    # First call: get matched group
                    inner_q.first.return_value = parent_group
                    inner_q.all.return_value = []
                else:
                    # Second call: get children
                    inner_q.first.return_value = None
                    inner_q.all.return_value = [child1, child2]

                return inner_q

            mock_q.filter.side_effect = filter_mock
            return mock_q

        mock_session.query.side_effect = lambda x: mock_query_factory()

        result = TreeDescent.descend(group_id, mock_session)

        assert result.matched_group == parent_group
        assert len(result.child_groups) == 2

    def test_descend_with_specs(self) -> None:
        """Descending collects specs from matched group."""
        group_id = uuid.uuid4()
        group = MagicMock()
        group.id = group_id
        group.parent_id = None
        group.path = "root"
        group.member_spec_refs = ["Service@1", "Handler@1"]

        spec1 = MagicMock()
        spec1.component_ref = "Service"
        spec1.provenance = [{"file": "service.py", "start_line": 1, "end_line": 50}]

        spec2 = MagicMock()
        spec2.component_ref = "Handler"
        spec2.provenance = [{"file": "handler.py", "start_line": 1, "end_line": 30}]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        # Setup returns
        first_calls = [group, spec1, spec2]
        all_calls = [[]]

        def get_first():
            if first_calls:
                return first_calls.pop(0)
            return None

        mock_query.filter.return_value.first.side_effect = get_first
        mock_query.filter.return_value.all.side_effect = all_calls

        result = TreeDescent.descend(group_id, mock_session)

        assert result.matched_group == group
        assert len(result.specs) == 2
        assert len(result.source_spans) == 2

    def test_descend_respects_max_specs(self) -> None:
        """Descending respects max_specs limit."""
        group_id = uuid.uuid4()
        group = MagicMock()
        group.id = group_id
        group.parent_id = None
        group.path = "root"
        # More specs than max_specs
        group.member_spec_refs = ["Spec1", "Spec2", "Spec3", "Spec4", "Spec5"]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        mock_query.filter.return_value.first.return_value = group
        mock_query.filter.return_value.all.return_value = []

        result = TreeDescent.descend(group_id, mock_session, max_specs=3)

        # Should only attempt to fetch up to max_specs
        assert len(result.specs) <= 3

    def test_descend_respects_max_spans(self) -> None:
        """Descending respects max_spans limit."""
        group_id = uuid.uuid4()
        group = MagicMock()
        group.id = group_id
        group.parent_id = None
        group.path = "root"
        group.member_spec_refs = ["Spec1"]

        spec = MagicMock()
        spec.component_ref = "Spec1"
        spec.provenance = [
            {"file": f"file{i}.py", "start_line": i, "end_line": i + 10}
            for i in range(150)  # More than max_spans
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        first_calls = [group, spec]

        def get_first():
            if first_calls:
                return first_calls.pop(0)
            return None

        mock_query.filter.return_value.first.side_effect = get_first
        mock_query.filter.return_value.all.return_value = []

        result = TreeDescent.descend(group_id, mock_session, max_specs=10, max_spans=50)

        # Should respect max_spans
        assert len(result.source_spans) <= 50

    def test_build_tree_path_root_group(self) -> None:
        """Building tree path for root group returns just root."""
        group = MagicMock()
        group.id = uuid.uuid4()
        group.parent_id = None
        group.path = "root"

        mock_session = MagicMock()

        path = TreeDescent._build_tree_path(group, mock_session)

        assert len(path) == 1
        assert path[0] == group

    def test_build_tree_path_with_parents(self) -> None:
        """Building tree path walks up to root."""
        leaf_id = uuid.uuid4()
        mid_id = uuid.uuid4()
        root_id = uuid.uuid4()

        leaf = MagicMock()
        leaf.id = leaf_id
        leaf.parent_id = mid_id
        leaf.path = "root/auth/tokens"

        mid = MagicMock()
        mid.id = mid_id
        mid.parent_id = root_id
        mid.path = "root/auth"

        root = MagicMock()
        root.id = root_id
        root.parent_id = None
        root.path = "root"

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        # Return parents in order
        parents = [mid, root]

        def get_parent():
            if parents:
                return parents.pop(0)
            return None

        mock_query.filter.return_value.first.side_effect = get_parent

        path = TreeDescent._build_tree_path(leaf, mock_session)

        assert len(path) == 3
        assert path[0] == root
        assert path[1] == mid
        assert path[2] == leaf
