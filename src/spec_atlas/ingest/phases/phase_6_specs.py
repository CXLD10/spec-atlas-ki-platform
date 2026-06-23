"""Phase 6: Intelligent L3 spec generation with module-aware batching.

This phase:
1. Analyzes codebase into modules using ModuleAnalyzer
2. Selects 30-40 high-quality entities for spec generation using SpecSelector
3. Generates specs in parallel batches (5-10 per LLM call) to respect context budgets
4. Maintains module context in prompts for better semantic understanding
"""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Node, Repo
from spec_atlas.ingest.strategies.module_analyzer import ModuleAnalyzer
from spec_atlas.ingest.strategies.spec_selector import SpecSelector
from spec_atlas.specify.engine import SpecifyEngine

if TYPE_CHECKING:
    from spec_atlas.llm import LLMProvider


class Phase6SpecGenerator:
    """Generate intelligent, module-aware specs for entire codebase.

    Entry point: run(session, repo, llm_provider) -> specs with provenance.
    """

    def __init__(
        self,
        batch_size: int = 5,
        target_spec_count: int = 35,
        max_specs_per_module: int = 3,
    ):
        """Initialize the spec generator.

        Args:
            batch_size: Number of entities per LLM call (5-10 recommended).
            target_spec_count: Target total specs (30-40 recommended).
            max_specs_per_module: Maximum specs per module for even distribution.
        """
        self.batch_size = batch_size
        self.target_spec_count = target_spec_count
        self.max_specs_per_module = max_specs_per_module
        self.module_analyzer = ModuleAnalyzer()
        self.spec_selector = SpecSelector(
            target_count=target_spec_count,
            max_per_module=max_specs_per_module,
        )

    def run(
        self,
        session: Session,
        repo: Repo,
        llm_provider: LLMProvider,
    ) -> list[tuple[dict, dict]]:
        """Run full L3 spec generation pipeline.

        Args:
            session: SQLAlchemy session.
            repo: Repository to index.
            llm_provider: LLM provider for spec generation.

        Returns:
            List of (spec_dict, provenance_dict) tuples.
        """
        # Phase 1: Analyze codebase into modules
        print(f"[Phase 6] Analyzing codebase structure for {repo.name}...")
        hierarchy = self.module_analyzer.analyze_codebase(session, repo)
        print(f"  -> {hierarchy.module_count} modules, {hierarchy.entity_count} entities")

        # Phase 2: Select high-quality entities for spec generation
        print(f"[Phase 6] Selecting {self.target_spec_count} entities for specs...")
        selected_entities = self.spec_selector.select_entities(hierarchy)
        print(f"  -> Selected {len(selected_entities)} entities")

        # Phase 3: Batch and generate specs
        print(f"[Phase 6] Generating specs in batches of {self.batch_size}...")
        specs = self._generate_specs_batched(
            session,
            repo,
            selected_entities,
            llm_provider,
        )
        print(f"  -> Generated {len(specs)} specs")

        return specs

    def _generate_specs_batched(
        self,
        session: Session,
        repo: Repo,
        selected_entities: list,
        llm_provider: LLMProvider,
    ) -> list[tuple[dict, dict]]:
        """Generate specs in parallel batches.

        Args:
            session: SQLAlchemy session.
            repo: Repository.
            selected_entities: Selected entities (SelectedEntity objects).
            llm_provider: LLM provider.

        Returns:
            List of (spec, provenance) tuples.
        """
        all_specs = []

        # Batch into groups of batch_size
        for batch_idx in range(0, len(selected_entities), self.batch_size):
            batch = selected_entities[batch_idx : batch_idx + self.batch_size]
            print(f"  Batch {batch_idx // self.batch_size + 1}: {len(batch)} entities")

            for selected in batch:
                try:
                    # Fetch focal node from DB
                    focal_node = (
                        session.query(Node).filter(Node.id == selected.node_id).first()
                    )
                    if not focal_node:
                        print(f"    ! Skipped {selected.qualified_name} (not found in DB)")
                        continue

                    # Fetch neighbors
                    neighbors = self._fetch_neighbors(session, repo.id, focal_node)

                    # Fetch edges
                    from spec_atlas.db.analysis import Edge

                    edges = (
                        session.query(Edge)
                        .filter(
                            (Edge.src_node_id == focal_node.id)
                            | (Edge.dst_node_id == focal_node.id)
                        )
                        .all()
                    )

                    # Generate spec with module context
                    spec, provenance = self._generate_spec_with_context(
                        session,
                        focal_node,
                        neighbors,
                        edges,
                        llm_provider,
                        selected.module_path,
                    )

                    all_specs.append((spec, provenance))
                    print(f"    ✓ {selected.qualified_name} ({selected.reason})")

                except Exception as e:
                    print(f"    ! Error generating spec for {selected.qualified_name}: {e}")

        return all_specs

    def _fetch_neighbors(
        self,
        session: Session,
        repo_id: uuid.UUID,
        focal_node: Node,
    ) -> list[Node]:
        """Fetch neighboring nodes (callers, callees, base classes, etc.).

        Args:
            session: SQLAlchemy session.
            repo_id: Repository ID.
            focal_node: The focal node.

        Returns:
            List of neighbor nodes.
        """
        from spec_atlas.db.analysis import Edge

        # Find edges where focal_node is src or dst
        edges = session.query(Edge).filter(
            (Edge.src_node_id == focal_node.id) | (Edge.dst_node_id == focal_node.id),
            Edge.repo_id == repo_id,
        ).all()

        neighbor_ids = set()
        for edge in edges:
            if edge.src_node_id == focal_node.id:
                neighbor_ids.add(edge.dst_node_id)
            else:
                neighbor_ids.add(edge.src_node_id)

        if not neighbor_ids:
            return []

        neighbors = session.query(Node).filter(Node.id.in_(neighbor_ids)).all()
        return neighbors[:20]  # Limit to 20 neighbors

    def _generate_spec_with_context(
        self,
        session: Session,
        focal_node: Node,
        neighbors: list[Node],
        edges: list,
        llm_provider: LLMProvider,
        module_path: str,
    ) -> tuple[dict, dict]:
        """Generate a spec with module context included in the prompt.

        Args:
            session: SQLAlchemy session.
            focal_node: The focal node to spec.
            neighbors: Neighbor nodes.
            edges: Edge relationships.
            llm_provider: LLM provider.
            module_path: The module this entity belongs to.

        Returns:
            Tuple of (spec, provenance).
        """
        # Enhance prompt with module context
        from spec_atlas.specify.engine import _build_prompt

        base_prompt = _build_prompt(focal_node, neighbors, edges)

        # Add module context
        module_context = f"""
## Module Context
This entity is part of the `{module_path}` module, which is responsible for:
- Encapsulating related functionality for {module_path}
- Providing public interfaces for downstream modules
- Managing internal state and coordination

When explaining this component, consider its role within this module and how it serves both the module's internal purposes and external consumers.
"""

        enhanced_prompt = base_prompt + module_context

        # Use SpecifyEngine with enhanced prompt
        # Since we already built the prompt, we'll use the internal function
        from spec_atlas.specify.engine import spec_json_schema, validate_spec
        import asyncio
        import inspect
        import json

        schema_dict = spec_json_schema()
        messages = [{"role": "user", "content": enhanced_prompt}]

        maybe_response = llm_provider.complete(messages, schema=schema_dict)
        response = (
            asyncio.run(maybe_response)
            if inspect.isawaitable(maybe_response)
            else maybe_response
        )

        # Parse and validate
        if isinstance(response, str):
            spec_content = json.loads(response)
        else:
            spec_content = response

        validated_spec = validate_spec(spec_content)

        # Add module information to spec
        validated_spec["module"] = module_path

        # Build provenance
        from spec_atlas.specify.engine import _extract_interconnections

        interconnections = _extract_interconnections(focal_node, neighbors, edges)
        validated_spec["interconnections"] = interconnections

        from spec_atlas.specify.engine import _build_provenance

        provenance = _build_provenance(focal_node, neighbors, edges, validated_spec)

        return validated_spec, provenance
