"""Tests for file inventory (content hash, LOC, idempotency)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from spec_atlas.ingest.inventory import FileInventory
from spec_atlas.ingest.resolver import RepoMetadata


class TestFileInventory:
    """Tests for file inventory scanning."""

    def test_scan_with_mocked_session(self) -> None:
        """Scan files with a mocked DB session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file1.py").write_text("x = 1\ny = 2\n")
            Path(tmpdir, "file2.js").write_text("const a = 1;")

            metadata = RepoMetadata(
                name="test-repo",
                source=tmpdir,
                default_branch="main",
                commit="abc123",
                working_dir=tmpdir,
                file_paths=["file1.py", "file2.js"],
            )

            # Mock the session
            mock_session = MagicMock()
            mock_repo = MagicMock()
            mock_repo.id = 1
            mock_session.query.return_value.filter_by.return_value.first.return_value = None

            repo, files = FileInventory.scan(metadata, metadata.file_paths, mock_session)

            # Check File rows
            assert len(files) == 2
            assert files[0].path == "file1.py"
            assert files[0].loc == 2
            assert files[1].path == "file2.js"
            assert files[1].loc == 1
            # Hashes should be computed
            assert len(files[0].content_hash) == 64  # SHA-256 hex
            assert len(files[1].content_hash) == 64

    def test_loc_counting(self) -> None:
        """Test LOC counting for various file types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Empty file
            Path(tmpdir, "empty.txt").write_text("")

            # File with only whitespace/empty lines
            Path(tmpdir, "whitespace.py").write_text("\n\n\n")

            # File with content and empty lines
            Path(tmpdir, "mixed.py").write_text("x = 1\n\n\ny = 2\n")

            # Use the internal function
            from spec_atlas.ingest.inventory import _count_loc

            assert _count_loc(Path(tmpdir, "empty.txt")) == 0
            assert _count_loc(Path(tmpdir, "whitespace.py")) == 0
            assert _count_loc(Path(tmpdir, "mixed.py")) == 2

    def test_hash_computation(self) -> None:
        """Test SHA-256 hash computation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir, "test.txt")
            file_path.write_text("hello world")

            from spec_atlas.ingest.inventory import _compute_hash

            hash1 = _compute_hash(file_path)
            hash2 = _compute_hash(file_path)

            # Hashes should be consistent
            assert hash1 == hash2
            # Should be valid hex (64 chars for SHA-256)
            assert len(hash1) == 64
            assert all(c in "0123456789abcdef" for c in hash1)

            # Change content, hash should differ
            file_path.write_text("goodbye world")
            hash3 = _compute_hash(file_path)
            assert hash1 != hash3

    def test_binary_file_handling(self) -> None:
        """Handle binary files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bin_file = Path(tmpdir, "binary.bin")
            bin_file.write_bytes(b"\x00\x01\x02\x03\xff")

            from spec_atlas.ingest.inventory import _compute_hash, _count_loc

            # LOC counting ignores encoding errors, may return 1 for binary
            loc = _count_loc(bin_file)
            assert isinstance(loc, int) and loc >= 0
            # Hash should still compute (even for binary)
            hash_val = _compute_hash(bin_file)
            assert isinstance(hash_val, str)
            assert len(hash_val) == 64  # SHA-256 hex
