"""Tool handlers: wire MCP tools to backend services."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class MCPToolHandlers:
    """Handlers for MCP tools, wired to backend services."""

    def __init__(self, backend_url: str = "http://localhost:8000"):
        """Initialize handlers.

        Args:
            backend_url: Backend API URL (e.g., http://localhost:8000)
        """
        self.backend_url = backend_url
        self.http_client = httpx.AsyncClient(base_url=backend_url, timeout=30.0)

    async def search(self, query: str, repo: str = "default") -> dict:
        """Search specs and groups via backend /api/ask endpoint.

        Wires to: F-007/008 pipeline (router → retriever → answerer)

        Args:
            query: User question
            repo: Repository identifier

        Returns:
            dict with answer, claims, confidence, strategy
        """
        try:
            response = await self.http_client.post(
                "/api/ask",
                json={"question": query, "repo": repo},
            )
            response.raise_for_status()
            result = response.json()
            return {
                "answer": result.get("text", ""),
                "claims": result.get("claims", []),
                "confidence": result.get("confidence", 0.0),
                "strategy": result.get("strategy_used", "vector_search"),
                "repo": repo,
                "query": query,
            }
        except httpx.HTTPError as e:
            logger.error(f"Search failed: {e}")
            return {
                "error": f"Search failed: {str(e)}",
                "code": "SEARCH_FAILED",
                "repo": repo,
            }

    async def get_spec(self, component_ref: str, repo: str = "default") -> dict:
        """Fetch a spec by component reference.

        Wires to: F-011 SpecStore (GET /api/specs/{component_ref})

        Args:
            component_ref: Component reference (e.g., AuthService)
            repo: Repository identifier

        Returns:
            dict with spec content, status, provenance
        """
        try:
            response = await self.http_client.get(
                f"/api/specs/{component_ref}",
                params={"repo": repo},
            )
            if response.status_code == 404:
                return {
                    "component_ref": component_ref,
                    "repo": repo,
                    "error": "spec not found",
                    "code": "SPEC_NOT_FOUND",
                }
            response.raise_for_status()
            spec = response.json()
            return {
                "component_ref": component_ref,
                "repo": repo,
                "spec": spec.get("content", {}),
                "status": spec.get("status", "draft"),
                "version": spec.get("version", 0),
                "provenance": spec.get("provenance", []),
            }
        except httpx.HTTPError as e:
            logger.error(f"Get spec failed: {e}")
            return {
                "error": f"Get spec failed: {str(e)}",
                "code": "GET_SPEC_FAILED",
                "component_ref": component_ref,
            }

    async def get_group(self, group_path: str, repo: str = "default") -> dict:
        """Fetch a group summary and its members.

        Wires to: F-005 GroupClustering (GET /api/groups/{id})

        Args:
            group_path: Group path (e.g., auth/tokens)
            repo: Repository identifier

        Returns:
            dict with group summary, children, member specs
        """
        try:
            # First, fetch group by path (would need a lookup endpoint)
            # For v1, we'll stub this to return the path as the ID
            response = await self.http_client.get(
                "/api/groups",
                params={"repo": repo, "path": group_path},
            )
            if response.status_code == 404:
                return {
                    "group_path": group_path,
                    "repo": repo,
                    "error": "group not found",
                    "code": "GROUP_NOT_FOUND",
                }
            response.raise_for_status()
            group = response.json()
            return {
                "group_path": group_path,
                "repo": repo,
                "title": group.get("title", ""),
                "summary": group.get("summary_md", ""),
                "children": group.get("children", []),
                "member_specs": group.get("member_spec_refs", []),
                "level": group.get("level", 0),
            }
        except httpx.HTTPError as e:
            logger.error(f"Get group failed: {e}")
            return {
                "error": f"Get group failed: {str(e)}",
                "code": "GET_GROUP_FAILED",
                "group_path": group_path,
            }

    async def list_stale_specs(self, repo: str = "default") -> dict:
        """List specs marked stale (source has changed).

        Wires to: F-014 drift detection (once implemented)

        Args:
            repo: Repository identifier

        Returns:
            dict with list of stale specs
        """
        try:
            response = await self.http_client.get(
                "/api/specs",
                params={"repo": repo, "status": "stale"},
            )
            response.raise_for_status()
            specs = response.json()
            return {
                "repo": repo,
                "stale_specs": specs.get("specs", []),
                "count": len(specs.get("specs", [])),
            }
        except httpx.HTTPError as e:
            logger.error(f"List stale specs failed: {e}")
            return {
                "repo": repo,
                "stale_specs": [],  # v1: return empty on error
                "error": str(e),
            }

    async def close(self) -> None:
        """Close HTTP client connection."""
        await self.http_client.aclose()
