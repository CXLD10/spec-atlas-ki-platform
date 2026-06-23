"""Tests for the Knowledge Base API (GET /api/kb, /api/kb/:ref).

Marked ``db``; skipped automatically when no Postgres is available."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from spec_atlas import db
from spec_atlas.api.app import create_app
from spec_atlas.config import get_settings
from spec_atlas.spec.store import SpecStore

pytestmark = pytest.mark.db


@pytest.fixture
def seeded_client(migrated: None) -> TestClient:
    SpecSession = db.spec_session()

    with SpecSession() as s:
        store = SpecStore(s)
        store.create(
            user_id="default",
            repo="kb-repo",
            component_ref="kb.Widget",
            spec_content={"purpose": "Renders a widget.", "inputs": [], "outputs": []},
            provenance=[{"field": "purpose", "file": "kb/widget.py", "start_line": 1, "end_line": 9}],
            status="verified",
        )
        # SpecStore.create derives a real "depends-on" SpecEdge from
        # spec_content["dependencies"] — no need to insert one manually.
        store.create(
            user_id="default",
            repo="kb-repo",
            component_ref="kb.WidgetFactory",
            spec_content={"purpose": "Builds widgets.", "dependencies": ["kb.Widget"]},
            provenance=[],
            status="draft",
        )

    return TestClient(create_app(get_settings()))


def test_kb_lists_and_fetches_specs(seeded_client: TestClient) -> None:
    listed = seeded_client.get("/api/kb", params={"repo": "kb-repo"})
    assert listed.status_code == 200
    cards = listed.json()
    assert {c["ref"] for c in cards} == {"kb.Widget", "kb.WidgetFactory"}

    widget = next(c for c in cards if c["ref"] == "kb.Widget")
    assert widget["status"] == "verified"
    assert "Renders a widget." in widget["markdown"]
    assert widget["provenance"] == [{"ref": "kb/widget.py", "kind": "code", "loc": "1-9"}]

    detail = seeded_client.get("/api/kb/kb.WidgetFactory", params={"repo": "kb-repo"})
    assert detail.status_code == 200
    card = detail.json()
    assert card["ref"] == "kb.WidgetFactory"
    assert card["relations"] == [{"kind": "depends-on", "ref": "kb.Widget"}]


def test_kb_unknown_ref_404s(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/api/kb/does-not-exist", params={"repo": "kb-repo"})
    assert resp.status_code == 404
