"""Phase 3 tests: real git history, Jira import, and honest Deep Wiki fallback.

All DB tests are marked ``db`` and skipped when Postgres is not available.
The Deep Wiki fallback tests are offline-safe (no DB needed).
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# 1. Real git history
# ---------------------------------------------------------------------------

class TestGitHistoryFromRealLog:
    """_harvest_commits reads real commits from a git working dir."""

    def test_harvest_commits_from_real_repo(self) -> None:
        """_harvest_commits extracts commits from a local git repo."""
        from spec_atlas.api.ingest import _harvest_commits

        with tempfile.TemporaryDirectory() as tmp:
            # Create a minimal git repo with two commits
            subprocess.run(["git", "init", tmp], check=True, capture_output=True)
            subprocess.run(["git", "-C", tmp, "config", "user.email", "test@test.com"],
                           check=True, capture_output=True)
            subprocess.run(["git", "-C", tmp, "config", "user.name", "Test"],
                           check=True, capture_output=True)

            (Path(tmp) / "a.py").write_text("x = 1\n")
            subprocess.run(["git", "-C", tmp, "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", tmp, "commit", "-m", "feat: add a.py"],
                           check=True, capture_output=True)

            (Path(tmp) / "b.py").write_text("y = 2\n")
            subprocess.run(["git", "-C", tmp, "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", tmp, "commit", "-m", "fix: add b.py"],
                           check=True, capture_output=True)

            commits = _harvest_commits(tmp, limit=10)

        assert len(commits) == 2, f"Expected 2 commits, got {len(commits)}: {commits}"
        assert all("sha" in c for c in commits)
        assert all(len(c["sha"]) == 40 for c in commits), "SHA must be full 40-char hash"
        assert all(len(c["short_sha"]) == 7 for c in commits)
        messages = [c["message"] for c in commits]
        assert "fix: add b.py" in messages
        assert "feat: add a.py" in messages

    def test_harvest_commits_returns_empty_for_nonexistent_repo(self) -> None:
        """_harvest_commits returns [] when the path is not a git repo."""
        from spec_atlas.api.ingest import _harvest_commits

        with tempfile.TemporaryDirectory() as tmp:
            commits = _harvest_commits(tmp)
        assert commits == []

    def test_git_history_endpoint_reads_from_db(self, migrated: None, tmp_path: Path) -> None:
        """GET /api/git/history returns commits stored on repos.recent_commits."""
        from fastapi.testclient import TestClient

        from spec_atlas import db
        from spec_atlas.api.app import create_app
        from spec_atlas.config import get_settings
        from spec_atlas.db.analysis import Repo

        sample_commits = [
            {"sha": "a" * 40, "short_sha": "aaaaaaa", "message": "initial commit",
             "author": "Dev", "date": "2026-01-01"},
            {"sha": "b" * 40, "short_sha": "bbbbbbb", "message": "add feature",
             "author": "Dev", "date": "2026-01-02"},
        ]

        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            repo = Repo(
                name="test-git-repo",
                source="https://github.com/example/test-git-repo",
                recent_commits=sample_commits,
            )
            session.add(repo)
            session.commit()
            repo_name = repo.name

        settings = get_settings()
        client = TestClient(create_app(settings))
        resp = client.get(f"/api/git/history?project_id={repo_name}")
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert "commits" in body
        assert len(body["commits"]) == 2
        messages = [c["message"] for c in body["commits"]]
        assert "initial commit" in messages

    def test_git_history_endpoint_honors_limit(self, migrated: None) -> None:
        """GET /api/git/history respects the limit parameter."""
        from fastapi.testclient import TestClient

        from spec_atlas import db
        from spec_atlas.api.app import create_app
        from spec_atlas.config import get_settings
        from spec_atlas.db.analysis import Repo

        many_commits = [
            {"sha": f"{'x' * 39}{i}", "short_sha": f"xxxxxxx{i}",
             "message": f"commit {i}", "author": "Dev", "date": "2026-01-01"}
            for i in range(20)
        ]
        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            repo = Repo(
                name="test-git-limit",
                source="local",
                recent_commits=many_commits,
            )
            session.add(repo)
            session.commit()
            repo_name = repo.name

        settings = get_settings()
        client = TestClient(create_app(settings))
        resp = client.get(f"/api/git/history?project_id={repo_name}&limit=5")
        assert resp.status_code == 200
        assert len(resp.json()["commits"]) == 5


# ---------------------------------------------------------------------------
# 2. Jira import
# ---------------------------------------------------------------------------

class TestJiraImportIndexesIssues:
    """JiraImporter reads export JSON and creates SourceUnit rows."""

    FIXTURE = Path(__file__).parent.parent / "fixtures" / "jira" / "sample_export.json"

    def test_importer_creates_source_units(self, migrated: None) -> None:
        """JiraImporter persists one SourceUnit per issue."""
        from spec_atlas import db
        from spec_atlas.db.analysis import SourceUnit
        from spec_atlas.jira.importer import JiraImporter

        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            repo_id, count = JiraImporter.import_from_file(self.FIXTURE, "ATLAS", session)

        assert count == 5, f"Expected 5 new units, got {count}"

        with AnalysisSession() as session:
            units = session.query(SourceUnit).filter(SourceUnit.source_type == "jira").all()
            keys = [u.section for u in units]

        assert "ATLAS-101" in keys
        assert "ATLAS-105" in keys

    def test_importer_is_idempotent(self, migrated: None) -> None:
        """Re-importing the same file creates no duplicates."""
        from spec_atlas import db
        from spec_atlas.db.analysis import SourceUnit
        from spec_atlas.jira.importer import JiraImporter

        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            JiraImporter.import_from_file(self.FIXTURE, "ATLAS", session)
        with AnalysisSession() as session:
            _, count2 = JiraImporter.import_from_file(self.FIXTURE, "ATLAS", session)

        assert count2 == 0, "Second import should create 0 new units (idempotent)"

    def test_jira_issues_endpoint_returns_db_data(self, migrated: None) -> None:
        """GET /api/jira/issues queries SourceUnits rather than returning literals."""
        from fastapi.testclient import TestClient

        from spec_atlas import db
        from spec_atlas.api.app import create_app
        from spec_atlas.config import get_settings
        from spec_atlas.jira.importer import JiraImporter

        AnalysisSession = db.analysis_session()
        with AnalysisSession() as session:
            JiraImporter.import_from_file(self.FIXTURE, "ATLAS", session)

        settings = get_settings()
        client = TestClient(create_app(settings))
        resp = client.get("/api/jira/issues?project_id=ATLAS&limit=10")
        assert resp.status_code == 200, resp.text

        body = resp.json()
        keys = [i["key"] for i in body["issues"]]
        assert "ATLAS-101" in keys, f"ATLAS-101 not found in: {keys}"

    def test_jira_import_endpoint(self, migrated: None) -> None:
        """POST /api/jira/import accepts an upload and returns indexed count."""
        from fastapi.testclient import TestClient

        from spec_atlas.api.app import create_app
        from spec_atlas.config import get_settings

        settings = get_settings()
        client = TestClient(create_app(settings))

        payload = self.FIXTURE.read_bytes()
        resp = client.post(
            "/api/jira/import",
            files={"file": ("sample_export.json", payload, "application/json")},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["project_key"] == "ATLAS"
        assert body["indexed"] == 5


# ---------------------------------------------------------------------------
# 3. Deep Wiki fallback — honest confidence
# ---------------------------------------------------------------------------

class TestDeepWikiFallbackHonestConfidence:
    """_get_deep_wiki_answer calls llm_provider.complete and uses similarity as confidence.

    These tests are offline-safe (no DB, no Postgres).
    """

    pytestmark = pytest.mark.skipif(False, reason="offline-safe")  # override module mark

    def test_deep_wiki_calls_llm_provider(self) -> None:
        """_get_deep_wiki_answer calls llm_provider.complete (not a canned string)."""
        from spec_atlas.api.answer import AnswerRouter

        fake_llm = MagicMock()
        fake_llm.complete.return_value = {
            "answer": "Python is a high-level programming language.",
            "claims": [{"claim": "Python is interpreted.", "source": "general_knowledge"}],
        }

        router = AnswerRouter(
            analysis_session_factory=None,
            spec_session_factory=None,
            llm_provider=fake_llm,
            embedding_provider=None,
        )

        result = asyncio.run(router._get_deep_wiki_answer("What is Python?", similarity=0.25))

        assert result is not None
        fake_llm.complete.assert_called_once()
        args, _ = fake_llm.complete.call_args
        messages = args[0]
        assert any("Python" in m["content"] for m in messages)

    def test_deep_wiki_confidence_is_similarity_score(self) -> None:
        """confidence in the return dict equals the similarity passed in."""
        from spec_atlas.api.answer import AnswerRouter

        fake_llm = MagicMock()
        fake_llm.complete.return_value = {"answer": "Some answer.", "claims": []}

        router = AnswerRouter(
            analysis_session_factory=None,
            spec_session_factory=None,
            llm_provider=fake_llm,
            embedding_provider=None,
        )

        result = asyncio.run(router._get_deep_wiki_answer("test question", similarity=0.17))

        assert result is not None
        assert result["confidence"] == pytest.approx(0.17)

    def test_deep_wiki_returns_none_on_empty_answer(self) -> None:
        """Returns None when the LLM returns an empty answer string."""
        from spec_atlas.api.answer import AnswerRouter

        fake_llm = MagicMock()
        fake_llm.complete.return_value = {"answer": "", "claims": []}

        router = AnswerRouter(
            analysis_session_factory=None,
            spec_session_factory=None,
            llm_provider=fake_llm,
            embedding_provider=None,
        )

        result = asyncio.run(router._get_deep_wiki_answer("anything", similarity=0.1))
        assert result is None

    def test_deep_wiki_returns_none_on_llm_exception(self) -> None:
        """Returns None gracefully when the LLM call throws."""
        from spec_atlas.api.answer import AnswerRouter

        fake_llm = MagicMock()
        fake_llm.complete.side_effect = RuntimeError("LLM unavailable")

        router = AnswerRouter(
            analysis_session_factory=None,
            spec_session_factory=None,
            llm_provider=fake_llm,
            embedding_provider=None,
        )

        result = asyncio.run(router._get_deep_wiki_answer("test", similarity=0.0))
        assert result is None
