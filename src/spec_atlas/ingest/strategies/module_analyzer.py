"""Module analyzer: Detects and hierarchically organizes code modules/packages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Node

if TYPE_CHECKING:
    from spec_atlas.db.analysis import Repo


@dataclass
class ModuleEntity:
    """Represents a node (function, class) in a module."""

    node_id: uuid.UUID
    qualified_name: str
    kind: str  # "module", "class", "function", "method"
    language: str
    file_path: str
    start_line: int
    end_line: int
    docstring: str | None = None
    signature: str | None = None

    @property
    def name(self) -> str:
        """Get the short name from qualified_name."""
        return self.qualified_name.split(".")[-1]


@dataclass
class Module:
    """Represents a single module (package/directory) in the codebase."""

    name: str  # e.g., "auth", "utils.validators"
    path: str  # e.g., "src/auth", "src/utils/validators"
    language: str  # "python", "typescript", "go"
    is_public: bool = False  # Heuristic: public if at a high level or exports public members
    entities: list[ModuleEntity] = field(default_factory=list)  # Classes, functions in this module
    submodules: list[Module] = field(default_factory=list)  # Child modules
    import_count: int = 0  # Number of imports from other modules
    is_entry_point: bool = False  # True if this is a known entry point (main, __main__, index, etc.)


@dataclass
class ModuleHierarchy:
    """Complete module hierarchy for a repository."""

    repo_id: uuid.UUID
    repo_name: str
    root_modules: list[Module] = field(default_factory=list)
    all_modules: list[Module] = field(default_factory=list)  # Flattened list of all modules
    entity_count: int = 0
    module_count: int = 0


class ModuleAnalyzer:
    """Analyzes a codebase and builds a hierarchical module structure."""

    def analyze_codebase(
        self,
        session: Session,
        repo: Repo,
    ) -> ModuleHierarchy:
        """Analyze a repository and build its module hierarchy.

        Args:
            session: SQLAlchemy session for DB access.
            repo: The repository to analyze.

        Returns:
            ModuleHierarchy with organized modules, entities, and metadata.
        """
        # Fetch all nodes for this repo
        nodes = session.query(Node).filter(Node.repo_id == repo.id).all()

        # Group nodes by module (qualified_name prefix)
        module_map = self._build_module_map(nodes)

        # Build hierarchy
        root_modules = self._build_hierarchy(module_map)

        # Flatten and sort
        all_modules = self._flatten_modules(root_modules)

        # Calculate metadata
        entity_count = len(nodes)
        module_count = len(all_modules)

        return ModuleHierarchy(
            repo_id=repo.id,
            repo_name=repo.name,
            root_modules=root_modules,
            all_modules=all_modules,
            entity_count=entity_count,
            module_count=module_count,
        )

    def _build_module_map(self, nodes: list[Node]) -> dict[str, Module]:
        """Group nodes into modules by qualified_name prefix.

        A module is inferred from the file path and the qualified name hierarchy.
        For Python, it's the package; for TS/JS, the src/ directory structure.

        Args:
            nodes: All nodes in the repo.

        Returns:
            Dict mapping module path -> Module object.
        """
        module_map: dict[str, Module] = {}

        for node in nodes:
            # Infer module path from qualified_name or file path
            module_path = self._infer_module_path(node)

            # Ensure all ancestor modules exist (create intermediate nodes)
            # E.g., "auth.session" requires "auth" to exist first
            normalized = module_path.replace("/", ".")
            parts = normalized.split(".")
            for i in range(1, len(parts) + 1):
                ancestor_path = ".".join(parts[:i])
                if ancestor_path not in module_map:
                    module_map[ancestor_path] = Module(
                        name=parts[i - 1],  # This component's name
                        path=ancestor_path,
                        language=node.language,
                        is_public=self._is_public_module(ancestor_path, node.language),
                        is_entry_point=False,  # Only direct nodes can be entry points
                    )

            # Add node as an entity to its direct module
            entity = ModuleEntity(
                node_id=node.id,
                qualified_name=node.qualified_name,
                kind=node.kind,
                language=node.language,
                file_path=node.id.hex[:8],  # Placeholder; callers can lookup via DB
                start_line=node.start_line,
                end_line=node.end_line,
                docstring=node.docstring,
                signature=node.signature,
            )
            module_map[module_path].entities.append(entity)

            # Mark as entry point if appropriate
            if self._is_entry_point(node):
                module_map[module_path].is_entry_point = True

        return module_map

    def _infer_module_path(self, node: Node) -> str:
        """Infer module path from node's qualified_name or file location.

        For Python (e.g., "auth.session.AuthManager"):
          -> "auth.session" (or "auth" if that's the only component)
        For TS/JS (e.g., "src/utils/validator.ts"):
          -> "utils" or "utils/validator"

        Args:
            node: The node to infer module path from.

        Returns:
            Module path string.
        """
        if node.language == "python":
            # qualified_name like "auth.session.AuthManager" -> "auth.session"
            # qualified_name like "auth.SessionManager" -> "auth"
            # qualified_name like "main" -> "main"
            parts = node.qualified_name.split(".")
            if len(parts) > 1 and node.kind != "module":
                # For classes/functions, take all but last component
                return ".".join(parts[:-1])
            # For modules or single-component names, return as-is
            return parts[0] if parts else "root"
        else:
            # TS/JS: extract directory from file_id (if available)
            # For now, use first part of qualified_name
            parts = node.qualified_name.split("/")
            if len(parts) > 1:
                return "/".join(parts[:-1])
            parts = node.qualified_name.split(".")
            return parts[0] if parts else "root"

    def _is_public_module(self, module_path: str, language: str) -> bool:
        """Heuristic: determine if a module is public/top-level.

        Public modules are typically top-level packages (depth 1).

        Args:
            module_path: The module path.
            language: The programming language.

        Returns:
            True if the module should be considered public.
        """
        depth = module_path.count("/") + module_path.count(".")
        # Top-level modules (depth 0-1) are public
        return depth <= 1

    def _is_entry_point(self, node: Node) -> bool:
        """Heuristic: determine if a node is an entry point.

        Entry points include main functions, __main__ modules, index.ts, etc.

        Args:
            node: The node to check.

        Returns:
            True if the node is an entry point.
        """
        entry_point_names = {"main", "__main__", "index", "index.ts", "index.js"}
        return node.qualified_name in entry_point_names or node.name in entry_point_names

    def _build_hierarchy(self, module_map: dict[str, Module]) -> list[Module]:
        """Build parent-child hierarchy from flat module map.

        A module with path "auth.session" is a child of "auth".

        Args:
            module_map: Flat mapping of module paths -> Module objects.

        Returns:
            List of root modules (with submodules populated recursively).
        """
        # Create parent-child relationships
        for module_path, module in list(module_map.items()):
            # Normalize path separators
            normalized_path = module_path.replace("/", ".")
            parts = normalized_path.split(".")

            if len(parts) > 1:
                parent_path = ".".join(parts[:-1])
                # Look for parent in both normalized and original formats
                if parent_path in module_map:
                    module_map[parent_path].submodules.append(module)

        # Collect roots (modules with no parent)
        roots = []
        for m_path, m in module_map.items():
            normalized = m_path.replace("/", ".")
            # A root has no dots (top-level module)
            if "." not in normalized:
                roots.append(m)

        return roots

    def _flatten_modules(self, root_modules: list[Module]) -> list[Module]:
        """Flatten module hierarchy into a single list.

        Args:
            root_modules: List of root modules.

        Returns:
            Flattened list of all modules (depth-first).
        """
        result = []

        def traverse(module: Module) -> None:
            result.append(module)
            for submodule in module.submodules:
                traverse(submodule)

        for root in root_modules:
            traverse(root)

        return result
