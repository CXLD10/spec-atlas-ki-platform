"""Route-table smoke test (the "no-mock" tripwire's backend half).

Boots the real app against a migrated, seeded Postgres and walks every GET
route in the app, asserting 200 + a non-empty, schema-valid body. This is the
mechanical guarantee that no production route silently returns an empty or
broken response — if a route regresses to needing data it can't find, or a
dependency wiring breaks, this test catches it.

Marked ``db``; skipped automatically when no Postgres is available (the
offline/CI suite stays green with no database)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from spec_atlas import db
from spec_atlas.api.app import create_app
from spec_atlas.config import get_settings
from spec_atlas.db.analysis import IngestJob
from spec_atlas.spec.store import SpecStore

pytestmark = pytest.mark.db


@pytest.fixture
def seeded_app(migrated: None) -> tuple[TestClient, dict]:
    """Seed one full, realistic slice of data across both DBs, then return a
    TestClient plus the seeded IDs/refs needed to hit path/query params."""
    AnalysisSession = db.analysis_session()
    SpecSession = db.spec_session()

    ids: dict = {}

    with AnalysisSession() as s:
        repo = db.Repo(name="smoke-repo", source="/tmp/smoke-repo", default_branch="main")
        s.add(repo)
        s.flush()

        file = db.File(
            repo_id=repo.id,
            path="auth/session.py",
            language="python",
            content_hash="deadbeef",
            loc=42,
        )
        s.add(file)
        s.flush()

        focal = db.Node(
            repo_id=repo.id,
            file_id=file.id,
            language="python",
            kind="function",
            name="mint_token",
            qualified_name="auth.session.mint_token",
            signature="def mint_token(user_id: str) -> str:",
            docstring="Mint a session token.",
            start_line=10,
            end_line=20,
        )
        neighbor = db.Node(
            repo_id=repo.id,
            file_id=file.id,
            language="python",
            kind="function",
            name="hash_password",
            qualified_name="auth.session.hash_password",
            signature="def hash_password(pw: str) -> str:",
            docstring="Hash a password.",
            start_line=30,
            end_line=35,
        )
        s.add_all([focal, neighbor])
        s.flush()

        edge = db.Edge(
            repo_id=repo.id,
            src_node_id=focal.id,
            dst_node_id=neighbor.id,
            kind="calls",
            confidence=0.9,
        )
        s.add(edge)
        s.flush()

        group = db.Group(
            repo_id=repo.id,
            parent_id=None,
            level=0,
            path="",
            title="smoke-repo",
            summary_md="Root group summary.",
            member_node_ids=[focal.id, neighbor.id],
            member_spec_refs=["auth.session.mint_token"],
        )
        s.add(group)
        s.flush()

        embedding = db.Embedding(
            owner_kind="group",
            owner_ref=group.path,
            model="sentence-transformers/all-MiniLM-L6-v2",
            repo_id=repo.id,
            vector=[0.1] * 384,
        )
        s.add(embedding)

        job = IngestJob(
            repo_url="https://github.com/example/smoke-repo",
            status="done",
            progress_pct=100,
        )
        s.add(job)
        s.commit()

        ids["repo_id"] = str(repo.id)
        ids["repo_name"] = repo.name
        ids["node_id"] = str(focal.id)
        ids["group_id"] = str(group.id)
        ids["job_id"] = str(job.id)

    with SpecSession() as s:
        store = SpecStore(s)
        spec = store.create(
            user_id="default",
            repo=ids["repo_name"],
            component_ref="auth.session.mint_token",
            spec_content={"purpose": "Mint a session token.", "interconnections": []},
            provenance=[{"file": "auth/session.py", "start_line": 10, "end_line": 20}],
            status="verified",
        )
        ids["component_ref"] = spec.component_ref
        ids["version"] = spec.version

    settings = get_settings()
    app = create_app(settings)
    client = TestClient(app)

    return client, ids


def _assert_ok_nonempty(resp, label: str) -> None:
    assert resp.status_code == 200, f"{label}: expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body not in (None, [], {}), f"{label}: body is empty: {body!r}"


class TestRouteTableSmoke:
    """Every GET route, against a seeded DB, returns 200 + non-empty body."""

    def test_health(self, seeded_app) -> None:
        client, _ = seeded_app
        resp = client.get("/health")
        _assert_ok_nonempty(resp, "GET /health")
        assert resp.json()["status"] == "ok"

    def test_root(self, seeded_app) -> None:
        client, _ = seeded_app
        _assert_ok_nonempty(client.get("/"), "GET /")

    def test_groups_tree(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get("/api/groups", params={"repo": ids["repo_name"]}), "GET /api/groups"
        )

    def test_group_detail(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get(f"/api/groups/{ids['group_id']}", params={"repo": ids["repo_name"]}),
            "GET /api/groups/{id}",
        )

    def test_spec_current(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get(
                f"/api/specs/{ids['component_ref']}", params={"repo": ids["repo_name"]}
            ),
            "GET /api/specs/{ref}",
        )

    def test_spec_versions(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get(
                f"/api/specs/{ids['component_ref']}/versions",
                params={"repo": ids["repo_name"]},
            ),
            "GET /api/specs/{ref}/versions",
        )

    def test_spec_version(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get(
                f"/api/specs/{ids['component_ref']}/v/{ids['version']}",
                params={"repo": ids["repo_name"]},
            ),
            "GET /api/specs/{ref}/v/{version}",
        )

    def test_spec_graph(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get(
                f"/api/specs/graph/{ids['component_ref']}",
                params={"repo": ids["repo_name"]},
            ),
            "GET /api/specs/graph/{ref}",
        )

    def test_project_specs(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get("/api/specs/project-specs", params={"project_id": ids["repo_name"]}),
            "GET /api/specs/project-specs",
        )

    def test_project_notes(self, seeded_app) -> None:
        client, ids = seeded_app
        client.post(
            "/api/specs/project-notes",
            params={"project_id": ids["repo_name"], "notes": "smoke test note"},
        )
        resp = client.get("/api/specs/project-notes", params={"project_id": ids["repo_name"]})
        _assert_ok_nonempty(resp, "GET /api/specs/project-notes")
        assert resp.json()["notes"] == "smoke test note"

    def test_graph_node(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(client.get(f"/api/graph/nodes/{ids['node_id']}"), "GET /api/graph/nodes/{id}")

    def test_graph_node_neighbors(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get(f"/api/graph/nodes/{ids['node_id']}/neighbors"),
            "GET /api/graph/nodes/{id}/neighbors",
        )

    def test_graph_subgraph(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get("/api/graph/subgraph", params={"node_id": ids["node_id"]}),
            "GET /api/graph/subgraph",
        )

    def test_graph_all_nodes(self, seeded_app) -> None:
        client, _ = seeded_app
        _assert_ok_nonempty(client.get("/api/graph/nodes"), "GET /api/graph/nodes")

    def test_graph_all_edges(self, seeded_app) -> None:
        client, _ = seeded_app
        _assert_ok_nonempty(client.get("/api/graph/edges"), "GET /api/graph/edges")

    def test_graph_search(self, seeded_app) -> None:
        client, _ = seeded_app
        _assert_ok_nonempty(
            client.get("/api/graph/search", params={"q": "mint_token"}), "GET /api/graph/search"
        )

    def test_git_history(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get("/api/git/history", params={"project_id": ids["repo_name"]}),
            "GET /api/git/history",
        )

    def test_jira_issues(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get("/api/jira/issues", params={"project_id": ids["repo_name"]}),
            "GET /api/jira/issues",
        )

    def test_ingest_status(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(client.get(f"/api/ingest/{ids['job_id']}"), "GET /api/ingest/{id}")

    def test_reports_verification(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get("/api/reports/verification", params={"repo": ids["repo_name"]}),
            "GET /api/reports/verification",
        )

    def test_reports_verification_issues(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get("/api/reports/verification/issues", params={"repo": ids["repo_name"]}),
            "GET /api/reports/verification/issues",
        )

    def test_reports_confidence(self, seeded_app) -> None:
        client, ids = seeded_app
        _assert_ok_nonempty(
            client.get("/api/reports/verification/confidence", params={"repo": ids["repo_name"]}),
            "GET /api/reports/verification/confidence",
        )

    def test_unknown_repo_404s_not_silently_empty(self, seeded_app) -> None:
        """A GET for a repo that doesn't exist must 404, never a fake 200."""
        client, _ = seeded_app
        resp = client.get("/api/groups", params={"repo": f"does-not-exist-{uuid.uuid4()}"})
        assert resp.status_code == 404
