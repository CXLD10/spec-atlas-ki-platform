"""DB roundtrip: migrations apply, then one row per table is created and queried,
including a groups parent/child pair and a spec_edges row (T-000.2 DoD).

Marked ``db``; skipped automatically when no Postgres is available."""

from __future__ import annotations

import uuid

import pytest

from spec_atlas import db

pytestmark = pytest.mark.db


def test_roundtrip_all_tables(migrated: None) -> None:
    # --- Analysis DB (L1 graph + L4 groups + embeddings) ---------------------
    AnalysisSession = db.analysis_session()
    with AnalysisSession() as s:
        repo = db.Repo(name="demo", source="/tmp/demo", default_branch="main")
        s.add(repo)
        s.flush()

        file = db.File(
            repo_id=repo.id,
            path="auth/tokens.py",
            language="python",
            content_hash="abc123",
            loc=42,
        )
        s.add(file)
        s.flush()

        n1 = db.Node(
            repo_id=repo.id,
            file_id=file.id,
            language="python",
            kind="function",
            name="mint",
            qualified_name="auth.tokens.mint",
            start_line=1,
            end_line=10,
        )
        n2 = db.Node(
            repo_id=repo.id,
            file_id=file.id,
            language="python",
            kind="function",
            name="verify",
            qualified_name="auth.tokens.verify",
            start_line=12,
            end_line=20,
        )
        s.add_all([n1, n2])
        s.flush()

        edge = db.Edge(
            repo_id=repo.id,
            src_node_id=n1.id,
            dst_node_id=n2.id,
            kind="calls",
            confidence=0.8,
        )
        s.add(edge)

        parent = db.Group(
            repo_id=repo.id,
            parent_id=None,
            level=0,
            path="",
            title="root",
            member_node_ids=[],
            member_spec_refs=[],
        )
        s.add(parent)
        s.flush()
        child = db.Group(
            repo_id=repo.id,
            parent_id=parent.id,
            level=1,
            path="auth",
            title="auth",
            member_node_ids=[n1.id, n2.id],
            member_spec_refs=["auth"],
            summary_md="# auth\n...",
        )
        s.add(child)

        emb = db.Embedding(
            owner_kind="group",
            owner_ref="auth",
            model="bge-small",
            repo_id=repo.id,
            vector=[0.0] * 384,
        )
        s.add(emb)
        s.commit()

        # Query back: parent/child link resolves, edge present, embedding stored.
        loaded_child = s.get(db.Group, child.id)
        assert loaded_child is not None and loaded_child.parent_id == parent.id
        assert s.get(db.Edge, edge.id).kind == "calls"
        assert s.get(db.Embedding, ("group", "auth", "bge-small")) is not None

    # --- Spec DB (L2 specs + L3 spec graph) ----------------------------------
    SpecSession = db.spec_session()
    with SpecSession() as s:
        spec = db.Spec(
            user_id="local",
            repo="demo",
            component_ref="auth",
            version=1,
            status="draft",
            content={"purpose": "issue/verify tokens", "invariants": ["token signed"]},
            provenance=[{"file_path": "auth/tokens.py", "start_line": 1, "end_line": 20}],
            source_fingerprint="fp1",
        )
        s.add(spec)
        s.flush()

        spec_edge = db.SpecEdge(
            user_id="local",
            repo="demo",
            src_component_ref="auth",
            dst_component_ref="crypto",
            kind="uses",
            derived_from="calls",
        )
        s.add(spec_edge)
        s.commit()

        assert isinstance(s.get(db.Spec, spec.id).id, uuid.UUID)
        assert s.get(db.SpecEdge, spec_edge.id).derived_from == "calls"
