"""Tests for ModuleAnalyzer: hierarchical module detection."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, Mock

import pytest

from spec_atlas.db.analysis import Node, Repo
from spec_atlas.ingest.strategies.module_analyzer import ModuleAnalyzer, ModuleEntity


@pytest.fixture
def mock_session() -> Mock:
    """Create a mock session for testing."""
    return MagicMock()


@pytest.fixture
def sample_nodes() -> list[Node]:
    """Create sample nodes for testing."""
    repo_id = uuid.uuid4()
    file_id_1 = uuid.uuid4()
    file_id_2 = uuid.uuid4()
    file_id_3 = uuid.uuid4()

    return [
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_1,
            language="python",
            kind="class",
            name="SessionManager",
            qualified_name="auth.session.SessionManager",
            signature="class SessionManager:",
            docstring="Manages user sessions",
            start_line=1,
            end_line=100,
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_1,
            language="python",
            kind="function",
            name="create_session",
            qualified_name="auth.session.create_session",
            signature=None,
            docstring=None,
            start_line=110,
            end_line=130,
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_2,
            language="python",
            kind="function",
            name="validate_email",
            qualified_name="utils.validators.validate_email",
            signature=None,
            docstring="Validates email format",
            start_line=1,
            end_line=20,
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_2,
            language="python",
            kind="class",
            name="EmailValidator",
            qualified_name="utils.validators.EmailValidator",
            signature="class EmailValidator:",
            docstring="Validates emails",
            start_line=25,
            end_line=50,
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_3,
            language="python",
            kind="function",
            name="main",
            qualified_name="main",
            signature="def main():",
            docstring=None,
            start_line=1,
            end_line=10,
        ),
    ]


@pytest.fixture
def sample_repo() -> Repo:
    """Create a sample repo."""
    return Repo(
        id=uuid.uuid4(),
        name="test_repo",
        source="/tmp/test",
        source_format="git",
    )


def test_module_analyzer_empty_nodes(mock_session: Mock, sample_repo: Repo) -> None:
    """Test module analyzer on empty node list."""
    mock_session.query.return_value.filter.return_value.all.return_value = []

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(mock_session, sample_repo)

    assert hierarchy.repo_id == sample_repo.id
    assert hierarchy.module_count == 0
    assert hierarchy.entity_count == 0
    assert hierarchy.root_modules == []


def test_module_analyzer_python_modules(
    mock_session: Mock, sample_repo: Repo, sample_nodes: list[Node]
) -> None:
    """Test module analyzer detects Python modules."""
    mock_session.query.return_value.filter.return_value.all.return_value = sample_nodes

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(mock_session, sample_repo)

    assert hierarchy.entity_count == 5
    assert hierarchy.module_count >= 2  # At least auth and utils

    # Check that modules have entities
    module_paths = {m.path for m in hierarchy.all_modules}
    assert any("auth" in path for path in module_paths)
    assert any("utils" in path for path in module_paths)


def test_module_analyzer_hierarchy_building(
    mock_session: Mock, sample_repo: Repo, sample_nodes: list[Node]
) -> None:
    """Test module analyzer builds correct hierarchy."""
    mock_session.query.return_value.filter.return_value.all.return_value = sample_nodes[:2]

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(mock_session, sample_repo)

    # Should have root modules
    assert len(hierarchy.root_modules) > 0

    # Check flattening works
    assert hierarchy.module_count >= 1


def test_module_analyzer_entry_point_detection(
    mock_session: Mock, sample_repo: Repo, sample_nodes: list[Node]
) -> None:
    """Test entry point detection."""
    # Use only the main node
    main_nodes = [sample_nodes[4]]
    mock_session.query.return_value.filter.return_value.all.return_value = main_nodes

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(mock_session, sample_repo)

    # Check entry point is marked
    main_module = [m for m in hierarchy.all_modules if m.name == "main"]
    assert len(main_module) > 0
    assert main_module[0].is_entry_point


def test_module_analyzer_public_module_detection(
    mock_session: Mock, sample_repo: Repo, sample_nodes: list[Node]
) -> None:
    """Test public module heuristic."""
    mock_session.query.return_value.filter.return_value.all.return_value = sample_nodes[:2]

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(mock_session, sample_repo)

    # Top-level auth module should be public
    auth_module = [m for m in hierarchy.all_modules if m.name == "auth"]
    assert len(auth_module) > 0
    assert auth_module[0].is_public


def test_module_analyzer_entities_grouped(
    mock_session: Mock, sample_repo: Repo, sample_nodes: list[Node]
) -> None:
    """Test entities are correctly grouped into modules."""
    mock_session.query.return_value.filter.return_value.all.return_value = sample_nodes

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(mock_session, sample_repo)

    # Find modules with entities
    modules_with_entities = [m for m in hierarchy.all_modules if m.entities]
    assert len(modules_with_entities) > 0

    # Should have at least 5 total entities
    total_entities = sum(len(m.entities) for m in modules_with_entities)
    assert total_entities == 5


def test_module_analyzer_infer_module_path_python() -> None:
    """Test module path inference for Python."""
    analyzer = ModuleAnalyzer()

    node = Node(
        id=uuid.uuid4(),
        repo_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        language="python",
        kind="class",
        name="SessionManager",
        qualified_name="auth.session.SessionManager",
        signature=None,
        docstring=None,
        start_line=1,
        end_line=10,
    )

    path = analyzer._infer_module_path(node)
    assert path == "auth.session"


def test_module_analyzer_infer_module_path_root() -> None:
    """Test module path inference for root module."""
    analyzer = ModuleAnalyzer()

    node = Node(
        id=uuid.uuid4(),
        repo_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        language="python",
        kind="module",
        name="utils",
        qualified_name="utils",
        signature=None,
        docstring=None,
        start_line=0,
        end_line=1,
    )

    path = analyzer._infer_module_path(node)
    assert path == "utils"


def test_module_analyzer_flatten_modules() -> None:
    """Test module flattening."""
    from spec_atlas.ingest.strategies.module_analyzer import Module

    root = Module(name="root", path="root", language="python")
    child1 = Module(name="child1", path="root.child1", language="python")
    child2 = Module(name="child2", path="root.child2", language="python")
    root.submodules = [child1, child2]

    analyzer = ModuleAnalyzer()
    flattened = analyzer._flatten_modules([root])

    assert len(flattened) == 3
    assert flattened[0] == root
    assert child1 in flattened
    assert child2 in flattened
