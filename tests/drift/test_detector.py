"""Tests for DriftDetector (F-014 T-014.1 + T-014.2).

All tests are offline (no DB required) unless marked pytest.mark.db.
"""

from __future__ import annotations

import hashlib
import uuid
from unittest.mock import MagicMock, patch


class TestComputeFingerprint:
    """Unit tests for the deterministic fingerprint algorithm."""

    def test_same_spans_same_fingerprint(self) -> None:
        """Identical spans always produce the same fingerprint."""
        from spec_atlas.drift.detector import compute_fingerprint

        spans = [
            {"file": "src/auth.py", "start_line": 1, "end_line": 50},
            {"file": "src/utils.py", "start_line": 10, "end_line": 20},
        ]
        fp1 = compute_fingerprint(spans)
        fp2 = compute_fingerprint(spans)
        assert fp1 == fp2

    def test_different_source_different_fingerprint(self) -> None:
        """Spans with different files/lines produce different fingerprints."""
        from spec_atlas.drift.detector import compute_fingerprint

        spans_a = [{"file": "src/auth.py", "start_line": 1, "end_line": 50}]
        spans_b = [{"file": "src/auth.py", "start_line": 1, "end_line": 99}]
        assert compute_fingerprint(spans_a) != compute_fingerprint(spans_b)

    def test_order_independent(self) -> None:
        """Fingerprint is deterministic regardless of span list order."""
        from spec_atlas.drift.detector import compute_fingerprint

        spans = [
            {"file": "b.py", "start_line": 5, "end_line": 10},
            {"file": "a.py", "start_line": 1, "end_line": 3},
        ]
        reversed_spans = list(reversed(spans))
        assert compute_fingerprint(spans) == compute_fingerprint(reversed_spans)

    def test_fingerprint_is_sha256_hex(self) -> None:
        """Fingerprint is a 64-char hex string (SHA256)."""
        from spec_atlas.drift.detector import compute_fingerprint

        fp = compute_fingerprint([{"file": "x.py", "start_line": 1, "end_line": 5}])
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_empty_spans_returns_consistent_fingerprint(self) -> None:
        """Empty span list produces a stable (but non-None) fingerprint."""
        from spec_atlas.drift.detector import compute_fingerprint

        fp = compute_fingerprint([])
        assert isinstance(fp, str)
        assert len(fp) == 64


class TestDriftDetectorDetectDrift:
    """Test DriftDetector.detect_drift against mock Spec DB rows."""

    def _make_spec(self, component_ref: str, fingerprint: str, provenance: list) -> MagicMock:
        spec = MagicMock()
        spec.id = str(uuid.uuid4())
        spec.repo = "test-repo"
        spec.component_ref = component_ref
        spec.source_fingerprint = fingerprint
        spec.provenance = provenance
        spec.valid_to = None
        return spec

    def test_no_drift_when_fingerprints_match(self) -> None:
        """detect_drift returns empty stale list when fingerprints are unchanged."""
        from spec_atlas.drift.detector import DriftDetector, compute_fingerprint

        provenance = [{"file": "src/auth.py", "start_line": 1, "end_line": 50}]
        current_fp = compute_fingerprint(provenance)

        spec = self._make_spec("auth/session", current_fp, provenance)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [spec]

        report = DriftDetector.detect_drift("test-repo", mock_session)
        assert report.is_clean()
        assert report.stale_specs == []

    def test_drift_marks_stale_on_reingest(self) -> None:
        """detect_drift identifies specs whose fingerprints no longer match.

        Simulates: spec was created with fingerprint from lines 1-50;
        re-ingest finds lines shifted to 1-99 (refactor added 49 lines).
        DriftDetector re-hashes the stored provenance with updated line ranges
        supplied via file_contents → fingerprint differs → spec marked stale.
        """
        from spec_atlas.drift.detector import DriftDetector, compute_fingerprint

        original_provenance = [{"file": "src/auth.py", "start_line": 1, "end_line": 50}]
        old_fingerprint = compute_fingerprint(original_provenance)

        # After re-ingest, the source file content has changed (hash suffix differs)
        # We simulate this via file_contents with a new hash
        file_contents = {"src/auth.py": "new_content_hash_after_refactor"}

        spec = self._make_spec("auth/session", old_fingerprint, original_provenance)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [spec]

        report = DriftDetector.detect_drift("test-repo", mock_session, file_contents)

        assert not report.is_clean()
        assert len(report.stale_specs) == 1
        assert report.stale_specs[0].component_ref == "auth/session"
        assert report.stale_specs[0].reason == "source_fingerprint_mismatch"
        assert report.stale_specs[0].old_fingerprint == old_fingerprint
        assert report.stale_specs[0].new_fingerprint != old_fingerprint

    def test_skips_specs_without_fingerprint(self) -> None:
        """Specs with no source_fingerprint are silently skipped (not yet fingerprinted)."""
        from spec_atlas.drift.detector import DriftDetector

        spec = self._make_spec("new/component", None, [])

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [spec]

        report = DriftDetector.detect_drift("test-repo", mock_session)
        assert report.is_clean()

    def test_report_includes_metadata(self) -> None:
        """DriftReport.details records how many specs were checked."""
        from spec_atlas.drift.detector import DriftDetector, compute_fingerprint

        provenance = [{"file": "a.py", "start_line": 1, "end_line": 5}]
        spec = self._make_spec("a/component", compute_fingerprint(provenance), provenance)

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [spec]

        report = DriftDetector.detect_drift("test-repo", mock_session)
        assert "specs_checked" in report.details
        assert report.details["specs_checked"] == 1


class TestDriftDetectorMarkStale:
    """Test DriftDetector.mark_stale updates the Spec DB correctly."""

    def test_mark_stale_sets_status_and_timestamp(self) -> None:
        """mark_stale sets status='stale' and staleness_detected_at on affected specs."""
        from spec_atlas.drift.detector import DriftDetector, DriftReport, StaleItem

        spec_id = str(uuid.uuid4())
        spec = MagicMock()
        spec.id = spec_id
        spec.status = "verified"
        spec.component_ref = "auth/session"
        spec.staleness_detected_at = None

        mock_session = MagicMock()
        # Make in_ filter return our mock spec
        mock_session.query.return_value.filter.return_value.all.return_value = [spec]

        report = DriftReport(repo_id="test-repo")
        report.stale_specs.append(
            StaleItem(
                id=spec_id,
                kind="spec",
                component_ref="auth/session",
                old_fingerprint="old",
                new_fingerprint="new",
                reason="source_fingerprint_mismatch",
            )
        )

        count = DriftDetector.mark_stale(report, mock_session)

        assert count == 1
        assert spec.status == "stale"
        assert spec.staleness_detected_at is not None
        mock_session.commit.assert_called_once()

    def test_mark_stale_skips_already_stale(self) -> None:
        """mark_stale does not touch specs already in status='stale'."""
        from spec_atlas.drift.detector import DriftDetector, DriftReport, StaleItem

        spec_id = str(uuid.uuid4())
        spec = MagicMock()
        spec.id = spec_id
        spec.status = "stale"
        spec.component_ref = "auth/session"

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [spec]

        report = DriftReport(repo_id="test-repo")
        report.stale_specs.append(
            StaleItem(
                id=spec_id, kind="spec", component_ref="auth/session",
                old_fingerprint="old", new_fingerprint="new",
                reason="source_fingerprint_mismatch",
            )
        )

        count = DriftDetector.mark_stale(report, mock_session)
        assert count == 0  # already stale, not double-counted

    def test_mark_stale_no_op_on_clean_report(self) -> None:
        """mark_stale is a no-op when report is clean (no stale specs)."""
        from spec_atlas.drift.detector import DriftDetector, DriftReport

        mock_session = MagicMock()
        report = DriftReport(repo_id="test-repo")  # is_clean() is True

        count = DriftDetector.mark_stale(report, mock_session)
        assert count == 0
        mock_session.commit.assert_not_called()


class TestVectorSearchStaleFilter:
    """Test that VectorSearch.search() excludes groups with stale spec refs."""

    def test_stale_refs_excluded_from_results(self) -> None:
        """Groups with member_spec_refs in stale_spec_refs are filtered out."""
        from unittest.mock import patch

        from spec_atlas.db.analysis import Group
        from spec_atlas.embed.fake import FakeEmbeddingProvider
        from spec_atlas.retrieve.search import VectorSearch

        stale_group = Group(
            id=uuid.uuid4(),
            repo_id=uuid.uuid4(),
            path="auth/session",
            level=0,
            title="Auth",
            parent_id=None,
            member_spec_refs=["auth/session"],
            summary_md="Auth group",
        )
        clean_group = Group(
            id=uuid.uuid4(),
            repo_id=uuid.uuid4(),
            path="utils/helpers",
            level=0,
            title="Utils",
            parent_id=None,
            member_spec_refs=["utils/helpers"],
            summary_md="Utils group",
        )

        mock_session = MagicMock()
        mock_session.query.return_value.scalar.return_value = 0  # no embeddings → keyword fallback
        mock_session.query.return_value.all.return_value = []

        # Simulate _node_keyword_search returning both groups
        with patch.object(
            VectorSearch,
            "_node_keyword_search",
            return_value=[(stale_group, 0.9), (clean_group, 0.7)],
        ):
            results = VectorSearch.search(
                "auth",
                FakeEmbeddingProvider(),
                mock_session,
                k=10,
                stale_spec_refs={"auth/session"},
            )

        result_groups = [owner for owner, _ in results]
        assert stale_group not in result_groups
        assert clean_group in result_groups
