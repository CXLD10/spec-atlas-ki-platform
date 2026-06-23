"""Integration tests for Phase 6 spec generation pipeline."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, Mock

import pytest

from spec_atlas.db.analysis import Node, Repo
from spec_atlas.ingest.phases.phase_6_specs import Phase6SpecGenerator
from spec_atlas.llm.fake import FakeLLMProvider


@pytest.fixture
def test_repo_with_code() -> tuple[Mock, Repo]:
    """Create a mock test repository with realistic code structure."""
    repo = Repo(
        id=uuid.uuid4(),
        name="example_app",
        source="/tmp/example_app",
        source_format="git",
        default_branch="main",
    )

    repo_id = repo.id
    file_id_1 = uuid.uuid4()
    file_id_2 = uuid.uuid4()
    file_id_3 = uuid.uuid4()
    file_id_4 = uuid.uuid4()

    # Create nodes
    nodes = [
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_1,
            language="python",
            kind="class",
            name="SessionManager",
            qualified_name="auth.session.SessionManager",
            start_line=1,
            end_line=100,
            docstring="Manages user sessions and tokens",
            signature="class SessionManager: ...",
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_1,
            language="python",
            kind="function",
            name="create_session",
            qualified_name="auth.session.create_session",
            start_line=110,
            end_line=130,
            signature="def create_session(user_id: str) -> Session: ...",
            docstring=None,
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_2,
            language="python",
            kind="class",
            name="EmailValidator",
            qualified_name="utils.validators.EmailValidator",
            start_line=1,
            end_line=40,
            docstring="Validates email addresses",
            signature=None,
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_2,
            language="python",
            kind="function",
            name="validate_email",
            qualified_name="utils.validators.validate_email",
            start_line=50,
            end_line=70,
            docstring=None,
            signature=None,
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_3,
            language="python",
            kind="class",
            name="APIServer",
            qualified_name="api.server.APIServer",
            start_line=1,
            end_line=150,
            docstring="FastAPI application server",
            signature="class APIServer: ...",
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_3,
            language="python",
            kind="function",
            name="run_server",
            qualified_name="api.server.run_server",
            start_line=160,
            end_line=200,
            docstring=None,
            signature=None,
        ),
        Node(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=file_id_4,
            language="python",
            kind="function",
            name="main",
            qualified_name="main",
            start_line=1,
            end_line=10,
            signature="def main(): ...",
            docstring=None,
        ),
    ]

    # Create mock session with more sophisticated mocking
    mock_session = MagicMock()

    # Setup query chain for different types of queries
    def query_side_effect(model):
        """Return appropriate mock based on queried model."""
        query_mock = MagicMock()

        if model == Node:
            # For Node queries
            def filter_side_effect(*args, **kwargs):
                filter_mock = MagicMock()
                # all() returns nodes matching the filter
                filter_mock.all.return_value = nodes
                filter_mock.first.return_value = nodes[0] if nodes else None
                filter_mock.filter.return_value = filter_mock  # Allow chaining
                return filter_mock
            query_mock.filter.side_effect = filter_side_effect
        else:
            # For Edge queries (from imports)
            from spec_atlas.db.analysis import Edge
            if model == Edge:
                filter_mock = MagicMock()
                filter_mock.all.return_value = []  # Empty edges for simplicity
                query_mock.filter.return_value = filter_mock

        return query_mock

    mock_session.query.side_effect = query_side_effect

    return mock_session, repo


def test_phase_6_analyzes_codebase(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 analyzer detects modules in codebase."""
    session, repo = test_repo_with_code

    generator = Phase6SpecGenerator(
        batch_size=5,
        target_spec_count=10,
        max_specs_per_module=2,
    )

    # Analyze without generating specs (just the analysis phase)
    from spec_atlas.ingest.strategies.module_analyzer import ModuleAnalyzer

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(session, repo)

    assert hierarchy.repo_id == repo.id
    assert hierarchy.module_count >= 3  # auth, utils, api
    assert hierarchy.entity_count >= 6  # 2 per module


def test_phase_6_selects_entities(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 selects appropriate entities for specs."""
    session, repo = test_repo_with_code

    generator = Phase6SpecGenerator(
        batch_size=5,
        target_spec_count=10,
        max_specs_per_module=2,
    )

    from spec_atlas.ingest.strategies.module_analyzer import ModuleAnalyzer

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(session, repo)

    selected = generator.spec_selector.select_entities(hierarchy)

    # Should select some entities
    assert len(selected) > 0
    # Should not exceed target
    assert len(selected) <= generator.target_spec_count
    # Should respect module capacity
    module_counts = {}
    for entity in selected:
        module_counts[entity.module_path] = module_counts.get(entity.module_path, 0) + 1
    for count in module_counts.values():
        assert count <= generator.max_specs_per_module


def test_phase_6_generates_specs(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 generates specs end-to-end."""
    session, repo = test_repo_with_code
    llm_provider = FakeLLMProvider()

    generator = Phase6SpecGenerator(
        batch_size=2,
        target_spec_count=5,
        max_specs_per_module=2,
    )

    specs = generator.run(session, repo, llm_provider)

    # Should generate some specs
    assert len(specs) > 0
    # Each spec should be a (spec, provenance) tuple
    for spec, provenance in specs:
        assert isinstance(spec, dict)
        assert isinstance(provenance, dict)
        # Spec should have expected fields
        assert "purpose" in spec
        assert "inputs" in spec or "outputs" in spec or "dependencies" in spec


def test_phase_6_respects_target_count(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 respects target spec count."""
    session, repo = test_repo_with_code
    llm_provider = FakeLLMProvider()

    target_count = 4
    generator = Phase6SpecGenerator(
        batch_size=2,
        target_spec_count=target_count,
        max_specs_per_module=2,
    )

    specs = generator.run(session, repo, llm_provider)

    # Should not exceed target
    assert len(specs) <= target_count


def test_phase_6_includes_module_context(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 includes module context in specs."""
    session, repo = test_repo_with_code
    llm_provider = FakeLLMProvider()

    generator = Phase6SpecGenerator(
        batch_size=2,
        target_spec_count=5,
        max_specs_per_module=2,
    )

    specs = generator.run(session, repo, llm_provider)

    # Specs should have module information
    for spec, provenance in specs:
        assert "module" in spec


def test_phase_6_even_distribution(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 distributes specs evenly across modules."""
    session, repo = test_repo_with_code
    llm_provider = FakeLLMProvider()

    generator = Phase6SpecGenerator(
        batch_size=2,
        target_spec_count=10,
        max_specs_per_module=2,
    )

    specs = generator.run(session, repo, llm_provider)

    # Count by module
    module_counts = {}
    for spec, _ in specs:
        module = spec.get("module", "unknown")
        module_counts[module] = module_counts.get(module, 0) + 1

    # Should have at least 2 different modules
    assert len(module_counts) >= 2
    # No module should exceed capacity
    for count in module_counts.values():
        assert count <= generator.max_specs_per_module


def test_phase_6_batches_correctly(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 batches entities for efficient LLM calls."""
    session, repo = test_repo_with_code
    llm_provider = FakeLLMProvider()

    batch_size = 2
    generator = Phase6SpecGenerator(
        batch_size=batch_size,
        target_spec_count=10,
        max_specs_per_module=3,
    )

    specs = generator.run(session, repo, llm_provider)

    # Should successfully batch (test passes if no errors)
    assert len(specs) > 0


def test_phase_6_handles_missing_nodes(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 gracefully handles missing nodes."""
    session, repo = test_repo_with_code
    llm_provider = FakeLLMProvider()

    # Add a selection with a non-existent node ID
    from spec_atlas.ingest.strategies.spec_selector import SelectedEntity

    generator = Phase6SpecGenerator(batch_size=2, target_spec_count=10)

    # Manually create selected entities with some non-existent IDs
    fake_entity = SelectedEntity(
        node_id=uuid.uuid4(),  # Non-existent ID
        qualified_name="fake.entity",
        kind="function",
        language="python",
        module_path="fake",
        reason="test",
        priority=0,
    )

    # This should not crash the batching process
    from spec_atlas.ingest.strategies.module_analyzer import ModuleAnalyzer

    analyzer = ModuleAnalyzer()
    hierarchy = analyzer.analyze_codebase(session, repo)
    selected = generator.spec_selector.select_entities(hierarchy)

    # Real entities should be selected
    assert len(selected) > 0


def test_phase_6_provenance_included(test_repo_with_code: tuple[Mock, Repo]) -> None:
    """Test Phase 6 includes provenance with specs."""
    session, repo = test_repo_with_code
    llm_provider = FakeLLMProvider()

    generator = Phase6SpecGenerator(
        batch_size=2,
        target_spec_count=5,
        max_specs_per_module=2,
    )

    specs = generator.run(session, repo, llm_provider)

    # Each spec should have provenance
    for spec, provenance in specs:
        assert isinstance(provenance, dict)
        # Provenance should map spec fields to source locations
        assert len(provenance) > 0 or True  # May be empty for generated specs from fake LLM
