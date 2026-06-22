"""Query router: classify question type and route to strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class QueryRouter:
    """Route queries to appropriate retrieval strategy."""

    # Keywords that indicate graph queries (detailed edge/dependency questions)
    GRAPH_KEYWORDS = {"call", "depend", "import", "reference", "invoke", "inherit"}

    @staticmethod
    def route(query: str) -> str:
        """Classify question and return routing strategy.

        Args:
            query: User query string.

        Returns:
            "vector_search" for big-picture questions, "graph_query" for detail.
        """
        if not query:
            return "vector_search"

        # Heuristic v1: check if query contains graph-related keywords
        query_lower = query.lower()

        for keyword in QueryRouter.GRAPH_KEYWORDS:
            # Check for keyword as substring (simple heuristic)
            if keyword in query_lower:
                return "graph_query"

        # Default to vector search (big-picture, conceptual questions)
        return "vector_search"
