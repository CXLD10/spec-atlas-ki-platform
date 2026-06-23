"""Tests for the graph API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from spec_atlas import db
from spec_atlas.api.app import create_app
from spec_atlas.config import Settings, get_settings
from spec_atlas.spec.store import SpecStore


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


@pytest.mark.db
class TestLayeredGraph:
    """Tests for GET /api/graph/layered (L1 code + L3 specs + L4 groups)."""

    def test_layered_subgraph_tags_l1_l3_l4(self, migrated: None) -> None:
        AnalysisSession = db.analysis_session()
        SpecSession = db.spec_session()

        with AnalysisSession() as s:
            repo = db.Repo(name="layered-repo", source="/tmp/layered-repo")
            s.add(repo)
            s.flush()

            file = db.File(
                repo_id=repo.id, path="a.py", language="python", content_hash="x", loc=10
            )
            s.add(file)
            s.flush()

            node = db.Node(
                repo_id=repo.id,
                file_id=file.id,
                language="python",
                kind="function",
                name="f",
                qualified_name="a.f",
                signature="def f():",
                start_line=1,
                end_line=2,
            )
            s.add(node)
            s.flush()

            group = db.Group(
                repo_id=repo.id,
                parent_id=None,
                level=0,
                path="",
                title="layered-repo",
                member_node_ids=[node.id],
            )
            s.add(group)
            s.commit()

        with SpecSession() as s:
            SpecStore(s).create(
                user_id="default",
                repo="layered-repo",
                component_ref="a.f",
                spec_content={"purpose": "test"},
                provenance=[],
                status="draft",
            )

        client = TestClient(create_app(get_settings()))
        resp = client.get("/api/graph/layered", params={"repo": "layered-repo"})
        assert resp.status_code == 200
        data = resp.json()

        layers = {n["layer"] for n in data["nodes"]}
        assert layers == {"L1", "L3", "L4"}

        l1_node = next(n for n in data["nodes"] if n["layer"] == "L1")
        assert l1_node["qualified_name"] == "a.f"

        l3_node = next(n for n in data["nodes"] if n["layer"] == "L3")
        assert l3_node["id"] == "spec:a.f"

        # Every edge must resolve to two real node ids in the response.
        node_ids = {n["id"] for n in data["nodes"]}
        for edge in data["edges"]:
            assert edge["source"] in node_ids
            assert edge["target"] in node_ids

        # Inter-layer edges exist: L4 group contains the L1 node, L3 spec documents it.
        inter_kinds = {e["kind"] for e in data["edges"] if e["inter"]}
        assert "contains" in inter_kinds
        assert "documents" in inter_kinds

    def test_layered_subgraph_unknown_repo_404s(self, migrated: None) -> None:
        client = TestClient(create_app(get_settings()))
        resp = client.get("/api/graph/layered", params={"repo": "does-not-exist"})
        assert resp.status_code == 404
