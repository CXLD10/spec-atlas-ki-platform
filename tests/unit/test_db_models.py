"""Offline unit tests for the DB models — assert the schema matches DATA-MODEL.md.

These run without a database (pure metadata introspection)."""

from __future__ import annotations

from spec_atlas.db import Embedding
from spec_atlas.db.analysis import AnalysisBase
from spec_atlas.db.spec import SpecBase


def test_analysis_tables_present() -> None:
    assert set(AnalysisBase.metadata.tables) == {
        "repos",
        "files",
        "nodes",
        "edges",
        "groups",
        "embeddings",
        "ingest_jobs",
    }


def test_spec_tables_present() -> None:
    assert set(SpecBase.metadata.tables) == {"specs", "spec_edges"}


def test_embedding_vector_dim_is_384() -> None:
    # Must match Settings.embed_dim and INTEGRATIONS.md (bge-small, 384-dim).
    assert Embedding.__table__.c.vector.type.dim == 384


def test_embedding_pk_is_owner_kind_ref_model() -> None:
    pk = {c.name for c in Embedding.__table__.primary_key.columns}
    assert pk == {"owner_kind", "owner_ref", "model"}


def test_node_stable_identity_unique_constraint() -> None:
    nodes = AnalysisBase.metadata.tables["nodes"]
    uniques = [
        tuple(c.name for c in con.columns)
        for con in nodes.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ("repo_id", "language", "qualified_name", "kind") in uniques


def test_spec_version_unique_constraint() -> None:
    specs = SpecBase.metadata.tables["specs"]
    uniques = [
        tuple(c.name for c in con.columns)
        for con in specs.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ("user_id", "repo", "component_ref", "version") in uniques


def test_cross_db_independence_no_fk_to_other_db() -> None:
    # Spec DB tables must not FK into Analysis DB tables (refs are by value).
    for table in SpecBase.metadata.tables.values():
        assert not table.foreign_keys
