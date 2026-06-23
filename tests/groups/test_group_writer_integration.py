"""Integration regression test: BatchSpecGenerator -> GroupWriter -> SpecGraphBuilder
against a real, migrated Postgres.

All three previously compared ``Spec.repo`` (a loose *name* ref, see
db/spec.py) against ``repo_id`` (a UUID) — ``varchar = uuid`` has no implicit
cast in Postgres, so this silently failed end-to-end on every real ingest:
specs were stored with the wrong ``repo`` value, group->spec linking always
errored, and spec-graph (L3) building always errored. Caught by actually
running the ingest pipeline against live Postgres (not mocks) and discovered
fresh during Phase 0 manual verification.

Marked ``db``; skipped automatically when no Postgres is available."""

from __future__ import annotations

import pytest

from spec_atlas import db
from spec_atlas.db.spec import Spec, SpecEdge
from spec_atlas.groups.clustering import GroupClustering
from spec_atlas.groups.group_writer import GroupWriter
from spec_atlas.llm.fake import FakeLLMProvider
from spec_atlas.specify.batch_generator import BatchSpecGenerator
from spec_atlas.specify.spec_graph_builder import SpecGraphBuilder

pytestmark = pytest.mark.db


def test_spec_repo_field_and_group_linking_use_repo_name(migrated: None, tmp_path) -> None:
    AnalysisSession = db.analysis_session()
    SpecSession = db.spec_session()
    llm = FakeLLMProvider()

    with AnalysisSession() as s:
        repo = db.Repo(name="integ-repo", source=str(tmp_path))
        s.add(repo)
        s.flush()

        file = db.File(
            repo_id=repo.id,
            path="pkg/mod.py",
            language="python",
            content_hash="abc",
            loc=10,
        )
        s.add(file)
        s.flush()

        a = db.Node(
            repo_id=repo.id,
            file_id=file.id,
            language="python",
            kind="class",
            name="A",
            qualified_name="pkg.mod.A",
            signature="class A:",
            docstring="Class A.",
            start_line=1,
            end_line=5,
        )
        b = db.Node(
            repo_id=repo.id,
            file_id=file.id,
            language="python",
            kind="class",
            name="B",
            qualified_name="pkg.mod.B",
            signature="class B:",
            docstring="Class B.",
            start_line=10,
            end_line=15,
        )
        s.add_all([a, b])
        s.flush()

        edge = db.Edge(
            repo_id=repo.id, src_node_id=a.id, dst_node_id=b.id, kind="calls", confidence=0.8
        )
        s.add(edge)
        s.commit()
        repo_id, repo_name = repo.id, repo.name

    with AnalysisSession() as analysis_session, SpecSession() as spec_session:
        # 1. Batch-generate specs (previously stored Spec.repo = repo_id, a UUID).
        gen_report = BatchSpecGenerator.generate_for_repo(
            repo_id,
            str(tmp_path),
            user_id="default",
            analysis_session=analysis_session,
            spec_session=spec_session,
            llm_provider=llm,
        )
        assert gen_report["succeeded"] == 2, gen_report

        specs = spec_session.query(Spec).filter(Spec.repo == repo_name).all()
        assert len(specs) == 2
        assert {s.component_ref for s in specs} == {"pkg.mod.A", "pkg.mod.B"}

        # 2. Form a group containing both nodes, then write/link it (previously
        # _link_specs_to_group and the related_specs lookup both errored).
        root_group, _ = GroupClustering.cluster_from_directory(
            repo_id, str(tmp_path), analysis_session
        )
        analysis_session.commit()

        from spec_atlas.db.analysis import Group as GroupModel

        group = (
            analysis_session.query(GroupModel)
            .filter(GroupModel.repo_id == repo_id)
            .order_by(GroupModel.level)
            .first()
        )
        group.member_node_ids = [a.id, b.id]
        analysis_session.merge(group)
        analysis_session.commit()

        report = GroupWriter.write_groups_for_repo(
            repo_id, str(tmp_path), analysis_session, spec_session, llm
        )
        assert report["errors"] == [], report["errors"]
        assert report["linked_specs"] >= 1

        analysis_session.refresh(group)
        assert set(group.member_spec_refs) == {"pkg.mod.A", "pkg.mod.B"}

        # 3. Build the spec graph (previously errored the same way).
        sg_report = SpecGraphBuilder.build_spec_graph(
            repo_id, user_id="default", analysis_session=analysis_session, spec_session=spec_session
        )
        assert sg_report["errors"] == [], sg_report["errors"]
        assert sg_report["created_edges"] == 1

        spec_edges = spec_session.query(SpecEdge).filter(SpecEdge.repo == repo_name).all()
        assert len(spec_edges) == 1
        assert spec_edges[0].src_component_ref == "pkg.mod.A"
        assert spec_edges[0].dst_component_ref == "pkg.mod.B"
