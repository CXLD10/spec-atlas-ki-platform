"""Tests for the real source-aggregation endpoints (GET /api/sources, /api/sources/:id).

Marked ``db``; skipped automatically when no Postgres is available."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from spec_atlas import db
from spec_atlas.api.app import create_app
from spec_atlas.config import get_settings
from spec_atlas.db.analysis import IngestJob
from spec_atlas.spec.store import SpecStore

pytestmark = pytest.mark.db


@pytest.fixture
def seeded_client(migrated: None) -> TestClient:
    AnalysisSession = db.analysis_session()
    SpecSession = db.spec_session()

    with AnalysisSession() as s:
        repo = db.Repo(name="sources-repo", source="https://github.com/example/sources-repo")
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

        group = db.Group(
            repo_id=repo.id, parent_id=None, level=0, path="", title="sources-repo"
        )
        s.add(group)

        job = IngestJob(
            repo_url=repo.source, status="done", progress_pct=100
        )
        s.add(job)
        s.commit()

    with SpecSession() as s:
        SpecStore(s).create(
            user_id="default",
            repo="sources-repo",
            component_ref="a.f",
            spec_content={"purpose": "test"},
            provenance=[{"file": "a.py", "start_line": 1, "end_line": 2}],
            status="draft",
        )

    return TestClient(create_app(get_settings()))


def test_sources_aggregates_repos_and_docs(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/api/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) == 1

    source = sources[0]
    assert source["type"] == "repo"
    assert source["name"] == "sources-repo"
    assert source["status"] == "ready"
    # Real counts, not a fudge factor.
    assert source["stats"]["entities"] == 1  # 1 node
    assert source["stats"]["cards"] == 1  # 1 current spec
    assert source["stats"]["domains"] == 1  # 1 group


def test_source_detail_by_id(seeded_client: TestClient) -> None:
    sources = seeded_client.get("/api/sources").json()
    source_id = sources[0]["id"]

    resp = seeded_client.get(f"/api/sources/{source_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == source_id


def test_source_detail_404_for_unknown_id(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/api/sources/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
