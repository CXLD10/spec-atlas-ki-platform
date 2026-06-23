"""Tests for SpecSelector: intelligent entity selection for specs."""

from __future__ import annotations

import uuid

import pytest

from spec_atlas.ingest.strategies.module_analyzer import Module, ModuleEntity, ModuleHierarchy
from spec_atlas.ingest.strategies.spec_selector import SpecSelector


@pytest.fixture
def sample_hierarchy() -> ModuleHierarchy:
    """Create a sample module hierarchy for testing."""
    # Create modules
    auth_module = Module(
        name="auth",
        path="auth",
        language="python",
        is_public=True,
        entities=[
            ModuleEntity(
                node_id=uuid.uuid4(),
                qualified_name="auth.SessionManager",
                kind="class",
                language="python",
                file_path="auth/session.py",
                start_line=1,
                end_line=100,
                docstring="Manages user sessions",
                signature="class SessionManager:",
            ),
            ModuleEntity(
                node_id=uuid.uuid4(),
                qualified_name="auth.create_session",
                kind="function",
                language="python",
                file_path="auth/session.py",
                start_line=110,
                end_line=130,
                docstring=None,
                signature=None,
            ),
        ],
    )

    utils_module = Module(
        name="validators",
        path="utils.validators",
        language="python",
        is_public=True,
        entities=[
            ModuleEntity(
                node_id=uuid.uuid4(),
                qualified_name="utils.validators.EmailValidator",
                kind="class",
                language="python",
                file_path="utils/validators.py",
                start_line=1,
                end_line=50,
                docstring="Validates email addresses",
            ),
            ModuleEntity(
                node_id=uuid.uuid4(),
                qualified_name="utils.validators.validate_email",
                kind="function",
                language="python",
                file_path="utils/validators.py",
                start_line=60,
                end_line=75,
                docstring=None,
                signature=None,
            ),
        ],
    )

    api_module = Module(
        name="api",
        path="api",
        language="typescript",
        is_public=True,
        entities=[
            ModuleEntity(
                node_id=uuid.uuid4(),
                qualified_name="api.Server",
                kind="class",
                language="typescript",
                file_path="api/server.ts",
                start_line=1,
                end_line=150,
                docstring="HTTP server handler",
                signature="class Server {",
            ),
            ModuleEntity(
                node_id=uuid.uuid4(),
                qualified_name="api.handler",
                kind="function",
                language="typescript",
                file_path="api/handler.ts",
                start_line=1,
                end_line=30,
                docstring=None,
                signature=None,
            ),
        ],
    )

    hierarchy = ModuleHierarchy(
        repo_id=uuid.uuid4(),
        repo_name="test_repo",
        root_modules=[auth_module, utils_module, api_module],
        all_modules=[auth_module, utils_module, api_module],
        entity_count=6,
        module_count=3,
    )

    return hierarchy


def test_spec_selector_initialization() -> None:
    """Test spec selector initializes with correct defaults."""
    selector = SpecSelector(target_count=35, max_per_module=3)

    assert selector.target_count == 35
    assert selector.max_per_module == 3


def test_spec_selector_selects_target_count(sample_hierarchy: ModuleHierarchy) -> None:
    """Test selector returns approximately target number of specs."""
    selector = SpecSelector(target_count=10, max_per_module=3)
    selected = selector.select_entities(sample_hierarchy)

    # Should not exceed target
    assert len(selected) <= selector.target_count
    # Should select something
    assert len(selected) > 0


def test_spec_selector_respects_module_capacity(
    sample_hierarchy: ModuleHierarchy,
) -> None:
    """Test selector respects max_per_module."""
    selector = SpecSelector(target_count=35, max_per_module=2)
    selected = selector.select_entities(sample_hierarchy)

    # Count per module
    module_counts = {}
    for entity in selected:
        module_counts[entity.module_path] = module_counts.get(entity.module_path, 0) + 1

    # No module should exceed capacity
    for count in module_counts.values():
        assert count <= selector.max_per_module


def test_spec_selector_prefers_public_modules(
    sample_hierarchy: ModuleHierarchy,
) -> None:
    """Test selector includes public module representatives."""
    selector = SpecSelector(target_count=35, max_per_module=3)
    selected = selector.select_entities(sample_hierarchy)

    # Should have representatives from public modules
    public_module_paths = {m.path for m in sample_hierarchy.all_modules if m.is_public}
    selected_modules = {s.module_path for s in selected}

    # Should select at least some public module representatives
    assert len(selected_modules & public_module_paths) > 0


def test_spec_selector_prefers_classes(
    sample_hierarchy: ModuleHierarchy,
) -> None:
    """Test selector prefers classes for public module representatives."""
    selector = SpecSelector(target_count=35, max_per_module=3)
    selected = selector.select_entities(sample_hierarchy)

    # Find public module representatives
    for selected_entity in selected:
        if selected_entity.reason == "public_module_representative":
            # Should prefer classes when available
            # In sample hierarchy, both auth and utils have classes
            if selected_entity.module_path in ("auth", "utils.validators"):
                assert selected_entity.kind == "class"


def test_spec_selector_selects_entry_points(
    sample_hierarchy: ModuleHierarchy,
) -> None:
    """Test selector includes entry points with high priority."""
    # Add an entry point to the hierarchy
    main_entity = ModuleEntity(
        node_id=uuid.uuid4(),
        qualified_name="main",
        kind="function",
        language="python",
        file_path="main.py",
        start_line=1,
        end_line=20,
        docstring=None,
        signature=None,
    )

    main_module = Module(
        name="main",
        path="main",
        language="python",
        is_public=True,
        is_entry_point=True,
        entities=[main_entity],
    )

    sample_hierarchy.all_modules.append(main_module)
    sample_hierarchy.root_modules.append(main_module)

    selector = SpecSelector(target_count=35, max_per_module=3)
    selected = selector.select_entities(sample_hierarchy)

    # Entry point should be selected
    entry_point_selected = [s for s in selected if s.qualified_name == "main"]
    assert len(entry_point_selected) > 0
    # Entry point should have priority 0 (highest)
    assert entry_point_selected[0].priority == 0


def test_spec_selector_spreads_evenly(
    sample_hierarchy: ModuleHierarchy,
) -> None:
    """Test selector spreads selections evenly across modules."""
    # Expand hierarchy with more entities
    for i in range(10):
        entity = ModuleEntity(
            node_id=uuid.uuid4(),
            qualified_name=f"auth.func{i}",
            kind="function",
            language="python",
            file_path="auth/funcs.py",
            start_line=i * 10,
            end_line=(i + 1) * 10,
        )
        sample_hierarchy.all_modules[0].entities.append(entity)

    selector = SpecSelector(target_count=20, max_per_module=2)
    selected = selector.select_entities(sample_hierarchy)

    # Count per module
    module_counts = {}
    for entity in selected:
        module_counts[entity.module_path] = module_counts.get(entity.module_path, 0) + 1

    # Should have relatively balanced distribution
    max_count = max(module_counts.values()) if module_counts else 0
    min_count = min(module_counts.values()) if module_counts else 0
    # Difference should be small (max 2 due to capacity)
    assert max_count - min_count <= 2


def test_spec_selector_reason_is_set(sample_hierarchy: ModuleHierarchy) -> None:
    """Test selector sets reason for each selected entity."""
    selector = SpecSelector(target_count=35, max_per_module=3)
    selected = selector.select_entities(sample_hierarchy)

    valid_reasons = {
        "entry_point",
        "public_module_representative",
        "high_complexity",
        "integration_point",
        "class_coverage",
    }

    for entity in selected:
        assert entity.reason in valid_reasons


def test_spec_selector_priority_ordering(sample_hierarchy: ModuleHierarchy) -> None:
    """Test selector orders by priority (lower priority value = higher)."""
    selector = SpecSelector(target_count=35, max_per_module=3)
    selected = selector.select_entities(sample_hierarchy)

    # List should be ordered by priority
    priorities = [s.priority for s in selected]
    assert priorities == sorted(priorities)


def test_spec_selector_handles_empty_modules() -> None:
    """Test selector handles modules with no entities."""
    empty_module = Module(
        name="empty",
        path="empty",
        language="python",
        is_public=True,
        entities=[],
    )

    hierarchy = ModuleHierarchy(
        repo_id=uuid.uuid4(),
        repo_name="test_repo",
        root_modules=[empty_module],
        all_modules=[empty_module],
        entity_count=0,
        module_count=1,
    )

    selector = SpecSelector(target_count=10, max_per_module=3)
    selected = selector.select_entities(hierarchy)

    # Should not crash and return empty list
    assert selected == []


def test_spec_selector_complexity_scoring() -> None:
    """Test complexity score calculation."""
    selector = SpecSelector()

    # Simple function
    simple_entity = ModuleEntity(
        node_id=uuid.uuid4(),
        qualified_name="simple_func",
        kind="function",
        language="python",
        file_path="simple.py",
        start_line=1,
        end_line=5,
        docstring=None,
        signature="def simple_func(): pass",
    )

    # Complex class
    complex_entity = ModuleEntity(
        node_id=uuid.uuid4(),
        qualified_name="ComplexClass",
        kind="class",
        language="python",
        file_path="complex.py",
        start_line=1,
        end_line=200,
        docstring="A complex class with many methods",
        signature="class ComplexClass(BaseClass, Mixin): def __init__(self, a, b, c, d, e, f): ...",
    )

    simple_score = selector._compute_complexity_score(simple_entity)
    complex_score = selector._compute_complexity_score(complex_entity)

    # Complex should score higher
    assert complex_score > simple_score


def test_spec_selector_importance_scoring() -> None:
    """Test importance score calculation."""
    selector = SpecSelector()

    # Simple function without docstring
    simple_entity = ModuleEntity(
        node_id=uuid.uuid4(),
        qualified_name="helper_func",
        kind="function",
        language="python",
        file_path="utils.py",
        start_line=1,
        end_line=5,
        docstring=None,
        signature=None,
    )

    # Manager class with docstring
    important_entity = ModuleEntity(
        node_id=uuid.uuid4(),
        qualified_name="SessionManager",
        kind="class",
        language="python",
        file_path="session.py",
        start_line=1,
        end_line=100,
        docstring="Manages session lifecycle",
        signature=None,
    )

    simple_score = selector._compute_importance_score(simple_entity)
    important_score = selector._compute_importance_score(important_entity)

    # Manager should score higher
    assert important_score > simple_score
