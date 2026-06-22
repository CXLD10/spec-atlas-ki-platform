"""Tests for query routing."""

from __future__ import annotations

from spec_atlas.retrieve.router import QueryRouter


class TestQueryRouter:
    """Tests for query routing to retrieval strategies."""

    def test_route_empty_query(self) -> None:
        """Empty query defaults to vector search."""
        result = QueryRouter.route("")
        assert result == "vector_search"

    def test_route_graph_queries_call(self) -> None:
        """Queries with 'call' route to graph_query."""
        queries = [
            "What calls this function?",
            "Which functions call authenticate()?",
            "Show me all callers of user_service",
        ]

        for query in queries:
            result = QueryRouter.route(query)
            assert result == "graph_query", f"Query '{query}' should route to graph_query"

    def test_route_graph_queries_depend(self) -> None:
        """Queries with 'depend' route to graph_query."""
        queries = [
            "What does this depend on?",
            "Show dependencies",
            "What modules depend on auth?",
        ]

        for query in queries:
            result = QueryRouter.route(query)
            assert result == "graph_query", f"Query '{query}' should route to graph_query"

    def test_route_graph_queries_import(self) -> None:
        """Queries with 'import' route to graph_query."""
        queries = [
            "Which files import database?",
            "What is imported by the API?",
            "Show imports",
        ]

        for query in queries:
            result = QueryRouter.route(query)
            assert result == "graph_query", f"Query '{query}' should route to graph_query"

    def test_route_graph_queries_reference(self) -> None:
        """Queries with 'reference' route to graph_query."""
        queries = [
            "What references this class?",
            "Show me references to config",
        ]

        for query in queries:
            result = QueryRouter.route(query)
            assert result == "graph_query", f"Query '{query}' should route to graph_query"

    def test_route_vector_queries_explain(self) -> None:
        """Explain/describe queries route to vector_search."""
        queries = [
            "Explain the authentication module",
            "What is the purpose of this component?",
            "Describe the API layer",
        ]

        for query in queries:
            result = QueryRouter.route(query)
            assert result == "vector_search", f"Query '{query}' should route to vector_search"

    def test_route_vector_queries_how(self) -> None:
        """How/why questions route to vector_search."""
        queries = [
            "How does user login work?",
            "Why is this needed?",
        ]

        for query in queries:
            result = QueryRouter.route(query)
            assert result == "vector_search", f"Query '{query}' should route to vector_search"

    def test_route_vector_queries_overview(self) -> None:
        """Overview/summary questions route to vector_search."""
        queries = [
            "Give me an overview of the system",
            "Summarize the auth module",
            "What is the main purpose?",
        ]

        for query in queries:
            result = QueryRouter.route(query)
            assert result == "vector_search", f"Query '{query}' should route to vector_search"

    def test_route_case_insensitive(self) -> None:
        """Routing is case-insensitive."""
        queries_graph = [
            "WHAT CALLS THIS?",
            "What CALLS this?",
            "what calls this?",
        ]

        for query in queries_graph:
            result = QueryRouter.route(query)
            assert result == "graph_query", (
                f"Query '{query}' should route to graph_query (case insensitive)"
            )

    def test_route_multiple_keywords(self) -> None:
        """Query with first matching keyword determines routing."""
        # "call" comes before vector search keywords
        query = "What calls this and why is it important?"
        result = QueryRouter.route(query)
        assert result == "graph_query"

    def test_route_substring_matching(self) -> None:
        """Keyword matching is substring-based (simple heuristic)."""
        # "import" is in "important", so it matches
        query = "Is this important?"
        result = QueryRouter.route(query)
        # This will match "import" in "important" - substring matching v1
        assert result == "graph_query"
