"""MCP tool handlers — wired to the same code paths as AnswerRouter."""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING

from spec_atlas.answer.engine import AnswerEngine
from spec_atlas.retrieve.router import QueryRouter
from spec_atlas.retrieve.search import VectorSearch
from spec_atlas.spec.store import SpecStore

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MCPHandlers:
    """Handlers for the four MCP tools; sessions are passed in at construction."""

    def __init__(
        self,
        spec_session: Session | None,
        analysis_session: Session,
        embedding_provider,
        llm_provider,
    ):
        self.spec_session = spec_session
        self.analysis_session = analysis_session
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider

    # ------------------------------------------------------------------ #
    # Tool 1: search_knowledge
    # ------------------------------------------------------------------ #

    async def search_knowledge(
        self, query: str, repo: str = "default", limit: int = 10
    ) -> dict:
        """Search the knowledge graph using the same path as AnswerRouter."""
        try:
            strategy = QueryRouter.route(query)
            results = VectorSearch.search(
                query,
                self.embedding_provider,
                self.analysis_session,
                k=min(limit, 20),
            )
            return {
                "query": query,
                "strategy": strategy,
                "results": [
                    {
                        "id": str(owner.id),
                        "label": (
                            owner.title
                            if hasattr(owner, "title")
                            else getattr(owner, "source_id", "")
                        ),
                        "relevance": round(float(score), 4),
                        "kind": "group" if hasattr(owner, "title") else "source_unit",
                    }
                    for owner, score in results
                ],
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"search_knowledge failed: {e}")
            return {"error": str(e), "query": query, "results": [], "count": 0}

    # ------------------------------------------------------------------ #
    # Tool 2: get_spec
    # ------------------------------------------------------------------ #

    async def get_spec(
        self,
        component_ref: str,
        repo: str = "default",
        version: int | None = None,
    ) -> dict:
        """Retrieve a spec using SpecStore."""
        if not self.spec_session:
            return {"error": "Spec DB not configured", "component_ref": component_ref}
        try:
            store = SpecStore(self.spec_session)
            spec = (
                store.get_version("default", repo, component_ref, version)
                if version is not None
                else store.get_current("default", repo, component_ref)
            )
            if not spec:
                return {"error": f"Spec not found: {component_ref}", "component_ref": component_ref}

            content = spec.content if isinstance(spec.content, dict) else {}
            return {
                "component_ref": component_ref,
                "version": spec.version,
                "status": spec.status,
                "confidence": content.get("confidence", 0.0),
                "purpose": content.get("purpose", ""),
                "inputs": content.get("inputs", []),
                "outputs": content.get("outputs", []),
                "dependencies": content.get("dependencies", []),
                "markdown": content.get("markdown", ""),
            }
        except Exception as e:
            logger.error(f"get_spec failed: {e}")
            return {"error": str(e), "component_ref": component_ref}

    # ------------------------------------------------------------------ #
    # Tool 3: get_graph
    # ------------------------------------------------------------------ #

    async def get_graph(
        self, repo: str = "default", layer: str = "spec", limit: int = 100
    ) -> dict:
        """Query L1 nodes/edges and L4 groups from the Analysis DB."""
        from spec_atlas.db.analysis import Edge, Group, Node

        try:
            nodes: list[dict] = []
            edges: list[dict] = []

            want_l1 = layer in ("source", "all", "L1", "spec")
            want_l4 = layer in ("group", "all", "L4", "spec")

            per_kind = limit // 2 if (want_l1 and want_l4) else limit

            if want_l1:
                for n in self.analysis_session.query(Node).limit(per_kind).all():
                    nodes.append(
                        {
                            "id": str(n.id),
                            "label": n.qualified_name or n.name,
                            "kind": n.kind,
                            "layer": "L1",
                        }
                    )
                for e in self.analysis_session.query(Edge).limit(per_kind).all():
                    edges.append(
                        {
                            "src": str(e.src_node_id),
                            "dst": str(e.dst_node_id),
                            "kind": e.kind,
                            "layer": "L1",
                        }
                    )

            if want_l4:
                for g in self.analysis_session.query(Group).limit(per_kind).all():
                    nodes.append(
                        {
                            "id": str(g.id),
                            "label": g.title or g.path,
                            "kind": "group",
                            "layer": "L4",
                        }
                    )
                    if g.parent_id:
                        edges.append(
                            {
                                "src": str(g.parent_id),
                                "dst": str(g.id),
                                "kind": "contains",
                                "layer": "L4",
                            }
                        )

            return {
                "repo": repo,
                "layer": layer,
                "nodes": nodes[:limit],
                "edges": edges[:limit],
                "node_count": len(nodes),
                "edge_count": len(edges),
            }
        except Exception as e:
            logger.error(f"get_graph failed: {e}")
            return {"error": str(e), "repo": repo, "nodes": [], "edges": []}

    # ------------------------------------------------------------------ #
    # Tool 4: ask_question
    # ------------------------------------------------------------------ #

    async def ask_question(self, question: str, repo: str = "default") -> dict:
        """Answer a question using the same retrieval pipeline as AnswerRouter."""
        from spec_atlas.db.analysis import SourceUnit as SourceUnitModel

        try:
            strategy = QueryRouter.route(question)
            results = VectorSearch.search(
                question, self.embedding_provider, self.analysis_session, k=1
            )

            if not results:
                return {
                    "question": question,
                    "answer": "No matching content found in the knowledge base.",
                    "claims": [],
                    "confidence": 0.0,
                    "strategy": strategy,
                }

            top_match, similarity = results[0]

            # Build context — same branch logic as AnswerRouter.answer()
            if isinstance(top_match, SourceUnitModel):
                from spec_atlas.api.answer import _build_context_from_source_unit

                context = _build_context_from_source_unit(top_match)
            else:
                from spec_atlas.api.answer import _build_context_from_node
                from spec_atlas.retrieve.descent import TreeDescent

                try:
                    context = TreeDescent.descend(top_match.id, self.analysis_session)
                except Exception:
                    context = _build_context_from_node(top_match, self.analysis_session)

            maybe_answer = AnswerEngine.answer_async(question, context, self.llm_provider)
            answer_obj = await maybe_answer if inspect.isawaitable(maybe_answer) else maybe_answer

            return {
                "question": question,
                "answer": answer_obj.text,
                "claims": [{"claim": c.claim, "source": c.source} for c in answer_obj.claims],
                "confidence": round(float(similarity), 4),
                "strategy": strategy,
            }
        except Exception as e:
            logger.error(f"ask_question failed: {e}")
            return {
                "error": str(e),
                "question": question,
                "answer": "",
                "claims": [],
                "confidence": 0.0,
            }


# ---------------------------------------------------------------------------
# Backwards-compat stub — kept so existing tests/imports don't break.
# MCPToolHandlers was the old HTTP-proxy-based handler; real work moved to
# MCPHandlers above. Remove after tests/mcp/test_handlers.py is updated.
# ---------------------------------------------------------------------------
class MCPToolHandlers:
    """Legacy HTTP-based stub. Do not use for new code."""

    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url

    async def search(self, query: str, repo: str = "default") -> dict:
        return {"answer": "stub", "claims": [], "confidence": 0.0, "query": query}

    async def get_spec(self, component_ref: str, repo: str = "default") -> dict:
        return {"component_ref": component_ref, "error": "stub"}

    async def get_group(self, group_path: str, repo: str = "default") -> dict:
        return {"group_path": group_path, "error": "stub"}

    async def list_stale_specs(self, repo: str = "default") -> dict:
        return {"repo": repo, "stale_specs": []}

    async def close(self) -> None:
        pass
