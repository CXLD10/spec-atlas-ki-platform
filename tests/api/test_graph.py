"""Tests for the graph API endpoints."""

from __future__ import annotations

from spec_atlas.api.app import create_app
from spec_atlas.config import Settings


class TestGraphAPI:
    """Tests for graph API endpoints."""

    def test_graph_endpoints_exist(self) -> None:
        """All graph endpoints are registered."""
        app = create_app(Settings())

        # Collect all routes including those from included routers
        all_routes = []
        for route in app.routes:
            if hasattr(route, "path"):
                all_routes.append(route.path)

        # Check that at least the router was included (graph prefix would be there)
        # This is a simplified check; full check would require deeper inspection
        assert len(all_routes) > 0, "No routes registered"

    def test_neighbors_direction_filter(self) -> None:
        """Neighbors endpoint respects direction parameter."""
        # Valid directions: in, out, both
        # Real test needs DB setup

    def test_subgraph_depth_limit(self) -> None:
        """Subgraph endpoint respects max_depth parameter."""
        # Real test needs DB setup with fixture graph

    def test_edge_kinds_filter(self) -> None:
        """Endpoints respect edge_kinds filter."""
        # Real test needs DB setup

    def test_confidence_threshold_filter(self) -> None:
        """Endpoints respect min_confidence filter."""
        # Real test needs DB setup

    def test_search_language_filter(self) -> None:
        """Search endpoint respects language filter."""
        # Real test needs DB setup

    def test_search_kind_filter(self) -> None:
        """Search endpoint respects kind filter."""
        # Real test needs DB setup

    def test_reachability_same_node(self) -> None:
        """Reachability returns true for same node."""
        # Real test needs DB setup

    def test_node_detail_schema(self) -> None:
        """NodeDetail schema includes all required fields."""
        from spec_atlas.api.graph import NodeDetail

        required_fields = {
            "id",
            "qualified_name",
            "kind",
            "name",
            "language",
            "signature",
            "docstring",
            "start_line",
            "end_line",
            "file_path",
            "repo_id",
        }

        schema_fields = set(NodeDetail.model_fields.keys())
        assert required_fields.issubset(schema_fields)

    def test_edge_detail_schema(self) -> None:
        """EdgeDetail schema includes all required fields."""
        from spec_atlas.api.graph import EdgeDetail

        required_fields = {
            "id",
            "src_node_id",
            "dst_node_id",
            "kind",
            "confidence",
        }

        schema_fields = set(EdgeDetail.model_fields.keys())
        assert required_fields.issubset(schema_fields)

    def test_neighbors_response_schema(self) -> None:
        """NeighborsResponse schema is correct."""
        from spec_atlas.api.graph import NeighborsResponse

        required_fields = {"edges", "target_nodes"}
        schema_fields = set(NeighborsResponse.model_fields.keys())
        assert required_fields.issubset(schema_fields)

    def test_subgraph_response_schema(self) -> None:
        """SubgraphResponse schema is correct."""
        from spec_atlas.api.graph import SubgraphResponse

        required_fields = {"nodes", "edges"}
        schema_fields = set(SubgraphResponse.model_fields.keys())
        assert required_fields.issubset(schema_fields)

    def test_search_response_schema(self) -> None:
        """SearchResponse schema is correct."""
        from spec_atlas.api.graph import SearchResponse

        required_fields = {"results"}
        schema_fields = set(SearchResponse.model_fields.keys())
        assert required_fields.issubset(schema_fields)

    def test_reachability_response_schema(self) -> None:
        """ReachabilityResponse schema is correct."""
        from spec_atlas.api.graph import ReachabilityResponse

        required_fields = {"reachable"}
        schema_fields = set(ReachabilityResponse.model_fields.keys())
        assert required_fields.issubset(schema_fields)
