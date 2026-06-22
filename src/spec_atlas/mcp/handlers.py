"""Tool handlers: wire MCP tools to backend services."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from spec_atlas.answer.engine import AnswerEngine
from spec_atlas.retrieve.descent import TreeDescent
from spec_atlas.retrieve.router import QueryRouter
from spec_atlas.retrieve.search import VectorSearch
from spec_atlas.spec.store import SpecStore

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MCPHandlers:
    """Handlers for MCP tools with direct database access."""

    def __init__(
        self,
        spec_session: Session,
        analysis_session: Session,
        embedding_provider,
        llm_provider,
    ):
        """Initialize handlers with database sessions.

        Args:
            spec_session: SQLAlchemy session for Spec DB.
            analysis_session: SQLAlchemy session for Analysis DB.
            embedding_provider: Embedding provider for vector search.
            llm_provider: LLM provider for answer generation.
        """
        self.spec_session = spec_session
        self.analysis_session = analysis_session
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider

    async def search_knowledge(self, query: str, repo: str = "default", limit: int = 10) -> dict:
        """Search the knowledge graph.

        Returns top matching specs/sources by relevance.

        Args:
            query: Search query
            repo: Repository identifier
            limit: Maximum results to return

        Returns:
            dict with query, results, and count
        """
        try:
            # Route the query
            strategy = QueryRouter.route(query)

            # For now, we'll use vector search as the primary retrieval method
            # In a full implementation, this would integrate TreeDescent
            search = VectorSearch(self.analysis_session, self.embedding_provider)

            # Perform search
            results = search.search(query, limit=limit)

            return {
                "query": query,
                "strategy": strategy,
                "results": [
                    {
                        "id": str(r.get("id", "")),
                        "label": r.get("name", ""),
                        "relevance": r.get("score", 0.0),
                        "kind": r.get("kind", ""),
                    }
                    for r in results
                ],
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "error": f"Search failed: {str(e)}",
                "query": query,
                "results": [],
                "count": 0,
            }

    async def get_spec(
        self,
        component_ref: str,
        repo: str = "default",
        version: int | None = None,
    ) -> dict:
        """Retrieve a specification.

        Returns the full spec (purpose, inputs, outputs, dependencies, etc.)

        Args:
            component_ref: Component reference
            repo: Repository identifier
            version: Spec version (optional)

        Returns:
            dict with spec content and metadata
        """
        try:
            store = SpecStore(self.spec_session)

            # Get current or specific version
            if version is not None:
                spec = store.get_version("default", repo, component_ref, version)
            else:
                spec = store.get_current("default", repo, component_ref)

            if not spec:
                return {
                    "error": f"Spec not found: {component_ref}",
                    "component_ref": component_ref,
                }

            def get_content_field(name: str, default=None):
                if isinstance(spec.content, dict):
                    return spec.content.get(name, default)
                return getattr(spec.content, name, default)

            return {
                "component_ref": component_ref,
                "version": spec.version,
                "status": spec.status,
                "confidence": get_content_field("confidence", 0.0),
                "purpose": get_content_field("purpose", ""),
                "inputs": get_content_field("inputs", []),
                "outputs": get_content_field("outputs", []),
                "dependencies": get_content_field("dependencies", []),
                "markdown": get_content_field("markdown", ""),
            }
        except Exception as e:
            logger.error(f"Get spec failed: {e}")
            return {
                "error": f"Get spec failed: {str(e)}",
                "component_ref": component_ref,
            }

    async def get_graph(
        self,
        repo: str = "default",
        layer: str = "spec",
        limit: int = 100,
    ) -> dict:
        """Retrieve graph structure.

        Returns nodes and edges for visualization or analysis.
        Layers: "source" (L1), "spec" (L2/L3), "group" (L4), or "all"

        Args:
            repo: Repository identifier
            layer: Graph layer to retrieve
            limit: Maximum nodes to return

        Returns:
            dict with nodes and edges
        """
        try:
            # For now, return an empty graph structure
            # A full implementation would query the Analysis DB for nodes/edges
            return {
                "repo": repo,
                "layer": layer,
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
            }
        except Exception as e:
            logger.error(f"Get graph failed: {e}")
            return {
                "error": f"Get graph failed: {str(e)}",
                "repo": repo,
                "nodes": [],
                "edges": [],
            }

    async def ask_question(self, question: str, repo: str = "default") -> dict:
        """Ask a question about the project.

        Returns an answer with citations.

        Args:
            question: User question
            repo: Repository identifier

        Returns:
            dict with answer, claims, and confidence
        """
        try:
            # Route the query
            strategy = QueryRouter.route(question)

            # Use TreeDescent for context retrieval
            descent = TreeDescent(self.analysis_session)

            # Retrieve context
            context = descent.retrieve(question, repo_id=None)  # TODO: Get repo_id from repo

            # Generate answer using AnswerEngine
            answer = AnswerEngine.answer(question, context, self.llm_provider)

            return {
                "question": question,
                "answer": answer.text,
                "claims": [{"claim": c.claim, "source": c.source} for c in answer.claims],
                "confidence": 1.0,  # TODO: Extract from answer
                "strategy": strategy,
            }
        except Exception as e:
            logger.error(f"Ask question failed: {e}")
            return {
                "error": f"Answer generation failed: {str(e)}",
                "question": question,
                "answer": "",
                "claims": [],
                "confidence": 0.0,
            }


# Backwards compatibility: keep old HTTP-based handlers for existing tests
class MCPToolHandlers:
    """Handlers for MCP tools, wired to backend services (HTTP-based)."""

    def __init__(self, backend_url: str = "http://localhost:8000"):
        """Initialize handlers.

        Args:
            backend_url: Backend API URL (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url

    async def search(self, query: str, repo: str = "default") -> dict:
        """Search specs and groups (stub)."""
        return {
            "answer": "Search not yet implemented",
            "claims": [],
            "confidence": 0.0,
            "strategy": "vector_search",
            "repo": repo,
            "query": query,
        }

    async def get_spec(self, component_ref: str, repo: str = "default") -> dict:
        """Fetch a spec by reference (stub)."""
        return {
            "component_ref": component_ref,
            "repo": repo,
            "spec": None,
            "error": "Spec not found",
        }

    async def get_group(self, group_path: str, repo: str = "default") -> dict:
        """Fetch a group and its members (stub)."""
        return {
            "group_path": group_path,
            "repo": repo,
            "group": None,
            "error": "Group not found",
        }

    async def list_stale_specs(self, repo: str = "default") -> dict:
        """List stale specs (stub)."""
        return {"repo": repo, "stale_specs": []}

    async def close(self) -> None:
        """Close HTTP client connection (stub)."""
        pass
