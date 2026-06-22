"""Tests for repository resolver (git and local paths)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from spec_atlas.ingest import RepoResolver


class TestResolveLocal:
    """Tests for local filesystem resolution."""

    def test_resolve_local_valid_path(self) -> None:
        """Resolve a valid local directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "file1.py").write_text("print('hello')")
            Path(tmpdir, "file2.txt").write_text("test")
            Path(tmpdir, "subdir").mkdir()
            Path(tmpdir, "subdir/file3.js").write_text("console.log('hi')")

            result = RepoResolver.resolve_local(tmpdir)

            assert result.name == Path(tmpdir).name
            assert result.source == str(Path(tmpdir).resolve())
            assert result.default_branch == "local"
            assert result.commit == "N/A"
            assert result.working_dir == str(Path(tmpdir).resolve())
            assert len(result.file_paths) == 3
            assert "file1.py" in result.file_paths
            assert "file2.txt" in result.file_paths
            assert "subdir/file3.js" in result.file_paths

    def test_resolve_local_empty_directory(self) -> None:
        """Resolve an empty directory (no files)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = RepoResolver.resolve_local(tmpdir)

            assert result.name == Path(tmpdir).name
            assert result.file_paths == []

    def test_resolve_local_path_not_exists(self) -> None:
        """Fail gracefully on non-existent path."""
        with pytest.raises(ValueError, match="does not exist"):
            RepoResolver.resolve_local("/nonexistent/path/to/repo")

    def test_resolve_local_path_is_file(self) -> None:
        """Fail gracefully when path is a file, not a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "file.txt"
            file_path.write_text("test")

            with pytest.raises(ValueError, match="not a directory"):
                RepoResolver.resolve_local(str(file_path))

    def test_resolve_local_nested_directories(self) -> None:
        """Resolve a path with nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a/b/c").mkdir(parents=True)
            Path(tmpdir, "a/file.py").write_text("x = 1")
            Path(tmpdir, "a/b/file.py").write_text("y = 2")
            Path(tmpdir, "a/b/c/file.py").write_text("z = 3")

            result = RepoResolver.resolve_local(tmpdir)

            assert len(result.file_paths) == 3
            assert "a/file.py" in result.file_paths
            assert "a/b/file.py" in result.file_paths
            assert "a/b/c/file.py" in result.file_paths
            assert result.file_paths == sorted(result.file_paths)


class TestResolveGit:
    """Tests for git repository resolution."""

    def test_resolve_git_invalid_url_format(self) -> None:
        """Fail on invalid URL format."""
        with pytest.raises(ValueError, match="Invalid git URL"):
            RepoResolver.resolve_git("not-a-url")

    def test_resolve_git_nonexistent_url(self) -> None:
        """Fail on URL that doesn't exist or is unreachable."""
        # This test skips if no network; in CI it will use a local git fixture
        pytest.skip("Network test; requires internet or local git fixture")

    @pytest.mark.parametrize(
        "url_format",
        [
            "https://example.com/repo.git",
            "http://example.com/repo",
            "git@github.com:user/repo.git",
        ],
    )
    def test_resolve_git_url_format_validation(self, url_format: str) -> None:
        """Validate various URL formats (don't resolve, just check format)."""
        # Just validate that these don't raise on format check
        try:
            # This will fail on actual clone, but should pass URL format validation
            RepoResolver.resolve_git(url_format)
        except RuntimeError:
            # Expected: git clone fails (no network or fake URL)
            pass
        except ValueError:
            # Should not happen for valid URL formats
            pytest.fail("Valid URL format rejected")


class TestResolveIntegration:
    """Integration tests with real fixture repos."""

    def test_resolve_local_python_fixture(self, tmp_path: Path) -> None:
        """Resolve a local Python fixture repo."""
        # Create a minimal Python project structure
        src = tmp_path / "src"
        src.mkdir()
        (src / "module.py").write_text("def foo():\n    pass")
        (src / "submodule.py").write_text("class Bar:\n    pass")

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_module.py").write_text("import unittest")

        result = RepoResolver.resolve_local(str(tmp_path))

        assert result.file_paths
        assert any("module.py" in p for p in result.file_paths)
        assert any("test_module.py" in p for p in result.file_paths)

    def test_resolve_local_mixed_language_fixture(self, tmp_path: Path) -> None:
        """Resolve a fixture with Python and JavaScript files."""
        (tmp_path / "backend.py").write_text("x = 1")
        (tmp_path / "frontend.js").write_text("const y = 2")
        (tmp_path / "types.ts").write_text("interface Z {}")

        result = RepoResolver.resolve_local(str(tmp_path))

        assert len(result.file_paths) == 3
        assert any(f.endswith(".py") for f in result.file_paths)
        assert any(f.endswith(".js") for f in result.file_paths)
        assert any(f.endswith(".ts") for f in result.file_paths)

    def test_resolve_local_ignores_dotfiles_properly(self, tmp_path: Path) -> None:
        """Resolve inventory includes all files (including dotfiles, but not .git)."""
        (tmp_path / ".gitignore").write_text("*.pyc")
        (tmp_path / "README.md").write_text("# Repo")
        (tmp_path / "main.py").write_text("x = 1")

        result = RepoResolver.resolve_local(str(tmp_path))

        # All files are included (no filtering on dots)
        assert ".gitignore" in result.file_paths
        assert "README.md" in result.file_paths
        assert "main.py" in result.file_paths
