"""Intelligent spec selection: Choose which entities to generate specs for."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spec_atlas.ingest.strategies.module_analyzer import (
        Module,
        ModuleEntity,
        ModuleHierarchy,
    )


@dataclass
class SelectedEntity:
    """An entity selected for spec generation."""

    node_id: uuid.UUID
    qualified_name: str
    kind: str
    language: str
    module_path: str
    reason: str  # Why this entity was selected (e.g., "public_class", "entry_point")
    priority: int  # 0 (highest) to N (lowest) for batching


class SpecSelector:
    """Selects which entities should have specs generated.

    Strategy:
    - 1 spec per public module (class or important function)
    - Entry points (main, __main__, index)
    - High-complexity nodes (many dependencies)
    - Integration points (heavily used/calling nodes)
    - Aim for 30-40 total specs spread evenly across modules
    """

    def __init__(self, target_count: int = 35, max_per_module: int = 3):
        """Initialize the spec selector.

        Args:
            target_count: Target number of specs to generate (30-40 recommended).
            max_per_module: Maximum specs per module to avoid clustering.
        """
        self.target_count = target_count
        self.max_per_module = max_per_module

    def select_entities(
        self,
        hierarchy: ModuleHierarchy,
    ) -> list[SelectedEntity]:
        """Select entities for spec generation.

        Strategy:
        1. Entry points (highest priority)
        2. Public module representatives (1 per module)
        3. High-complexity/high-dependency nodes
        4. Integration points
        5. Remaining capacity: fill with important functions

        Args:
            hierarchy: The module hierarchy from ModuleAnalyzer.

        Returns:
            Sorted list of SelectedEntity, prioritized for batching.
        """
        candidates: list[SelectedEntity] = []

        # Phase 1: Entry points
        for module in hierarchy.all_modules:
            for entity in module.entities:
                if self._is_entry_point(entity):
                    candidates.append(
                        SelectedEntity(
                            node_id=entity.node_id,
                            qualified_name=entity.qualified_name,
                            kind=entity.kind,
                            language=entity.language,
                            module_path=module.path,
                            reason="entry_point",
                            priority=0,
                        )
                    )

        # Phase 2: Public module representatives (prefer classes over functions)
        module_representatives = {}
        for module in hierarchy.all_modules:
            if module.is_public and module.path not in module_representatives:
                best_entity = self._find_best_representative(module, "class")
                if not best_entity:
                    best_entity = self._find_best_representative(module, "function")

                if best_entity:
                    module_representatives[module.path] = best_entity
                    candidates.append(
                        SelectedEntity(
                            node_id=best_entity.node_id,
                            qualified_name=best_entity.qualified_name,
                            kind=best_entity.kind,
                            language=best_entity.language,
                            module_path=module.path,
                            reason="public_module_representative",
                            priority=1,
                        )
                    )

        # Phase 3: High-complexity/high-dependency nodes
        complexity_candidates = []
        for module in hierarchy.all_modules:
            for entity in module.entities:
                if entity.node_id not in [c.node_id for c in candidates]:
                    complexity_score = self._compute_complexity_score(entity)
                    if complexity_score > 0:
                        complexity_candidates.append(
                            (entity, complexity_score, module.path)
                        )

        # Sort by complexity and take top candidates
        complexity_candidates.sort(key=lambda x: x[1], reverse=True)
        for entity, score, module_path in complexity_candidates[:self.target_count // 3]:
            if not self._module_at_capacity(candidates, module_path):
                candidates.append(
                    SelectedEntity(
                        node_id=entity.node_id,
                        qualified_name=entity.qualified_name,
                        kind=entity.kind,
                        language=entity.language,
                        module_path=module_path,
                        reason="high_complexity",
                        priority=2,
                    )
                )

        # Phase 4: Integration points (heavily imported/called)
        if len(candidates) < self.target_count:
            integration_candidates = []
            for module in hierarchy.all_modules:
                for entity in module.entities:
                    if entity.node_id not in [c.node_id for c in candidates]:
                        # Estimate importance by docstring presence and name patterns
                        importance = self._compute_importance_score(entity)
                        if importance > 0:
                            integration_candidates.append(
                                (entity, importance, module.path)
                            )

            integration_candidates.sort(key=lambda x: x[1], reverse=True)
            for entity, score, module_path in integration_candidates:
                if len(candidates) >= self.target_count:
                    break
                if not self._module_at_capacity(candidates, module_path):
                    candidates.append(
                        SelectedEntity(
                            node_id=entity.node_id,
                            qualified_name=entity.qualified_name,
                            kind=entity.kind,
                            language=entity.language,
                            module_path=module_path,
                            reason="integration_point",
                            priority=3,
                        )
                    )

        # Phase 5: Fill remaining capacity with remaining candidates
        if len(candidates) < self.target_count:
            remaining = []
            for module in hierarchy.all_modules:
                for entity in module.entities:
                    if entity.node_id not in [c.node_id for c in candidates]:
                        remaining.append((entity, module.path))

            for entity, module_path in remaining:
                if len(candidates) >= self.target_count:
                    break
                if entity.kind == "class" and not self._module_at_capacity(
                    candidates, module_path
                ):
                    candidates.append(
                        SelectedEntity(
                            node_id=entity.node_id,
                            qualified_name=entity.qualified_name,
                            kind=entity.kind,
                            language=entity.language,
                            module_path=module_path,
                            reason="class_coverage",
                            priority=4,
                        )
                    )

        # Trim to target and sort by priority
        selected = candidates[: self.target_count]
        selected.sort(key=lambda x: x.priority)

        return selected

    def _find_best_representative(
        self,
        module: Module,
        preferred_kind: str,
    ) -> "ModuleEntity | None":
        """Find the best representative entity in a module.

        Prefer entities with docstrings and matching kind.

        Args:
            module: The module to search.
            preferred_kind: Preferred entity kind ("class" or "function").

        Returns:
            Best entity, or None if module has no entities.
        """
        if not module.entities:
            return None

        # First, try to find preferred kind with docstring
        for entity in module.entities:
            if entity.kind == preferred_kind and entity.docstring:
                return entity

        # Then, try preferred kind without docstring
        for entity in module.entities:
            if entity.kind == preferred_kind:
                return entity

        # Fall back to first entity with docstring
        for entity in module.entities:
            if entity.docstring:
                return entity

        # Return first entity
        return module.entities[0]

    def _compute_complexity_score(self, entity: "ModuleEntity") -> float:
        """Compute complexity score for an entity.

        Higher score = more complex = higher priority.

        Args:
            entity: The entity to score.

        Returns:
            Complexity score (0.0-10.0).
        """
        score = 0.0

        # Classes are more complex than functions
        if entity.kind == "class":
            score += 3.0

        # Large entities (many lines) are likely more complex
        loc = entity.end_line - entity.start_line
        score += min(loc / 50.0, 3.0)  # Cap at 3 points

        # Entities with docstrings are more likely important
        if entity.docstring:
            score += 1.0

        # Long signatures indicate complex parameters
        if entity.signature:
            score += min(len(entity.signature) / 100.0, 1.5)

        return score

    def _compute_importance_score(self, entity: "ModuleEntity") -> float:
        """Compute importance score for an entity.

        Higher score = more important = higher priority.

        Args:
            entity: The entity to score.

        Returns:
            Importance score (0.0-10.0).
        """
        score = 0.0

        # Classes are important
        if entity.kind == "class":
            score += 2.0

        # Entities with docstrings are more likely important
        if entity.docstring:
            score += 2.0

        # Certain naming patterns indicate importance
        important_patterns = ["manager", "handler", "service", "controller", "base"]
        for pattern in important_patterns:
            if pattern in entity.qualified_name.lower():
                score += 1.5

        return score

    def _module_at_capacity(
        self,
        selected: list[SelectedEntity],
        module_path: str,
    ) -> bool:
        """Check if a module has reached its capacity.

        Args:
            selected: Currently selected entities.
            module_path: Module path to check.

        Returns:
            True if module is at capacity.
        """
        count = sum(1 for s in selected if s.module_path == module_path)
        return count >= self.max_per_module

    def _is_entry_point(self, entity: "ModuleEntity") -> bool:
        """Check if an entity is an entry point.

        Args:
            entity: The entity to check.

        Returns:
            True if entity is an entry point.
        """
        entry_names = {"main", "__main__", "index"}
        return entity.qualified_name in entry_names or entity.name in entry_names
