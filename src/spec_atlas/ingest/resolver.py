"""Repository resolver — git clone or local path validation."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

logger = logging.getLogger(__name__)


@dataclass
class RepoMetadata:
    """Repository metadata from a resolved source."""

    name: str
    """Repository name (directory name)."""
    source: str
    """Original source (local path or git URL)."""
    default_branch: str
    """Branch name (e.g. 'main', 'master', or 'local' for local paths)."""
    commit: str
    """Commit SHA at the time of resolution (or 'N/A' for local paths)."""
    working_dir: str
    """Absolute path to the working directory (repo root)."""
    file_paths: list[str]
    """Relative file paths from repo root (inventory)."""


class RepoResolver:
    """Resolve a repository source (local path or git URL) and inventory files."""

    @staticmethod
    def resolve_local(path: str) -> RepoMetadata:
        """Validate and resolve a local filesystem path.

        Args:
            path: Local filesystem path to the repository.

        Returns:
            RepoMetadata with the path, directory name, and file inventory.

        Raises:
            ValueError: If path does not exist or is not a directory.
        """
        repo_path = Path(path).resolve()

        if not repo_path.exists():
            raise ValueError(f"Path does not exist: {path}")
        if not repo_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        # Inventory files
        file_paths = []
        for file in repo_path.rglob("*"):
            if file.is_file():
                rel_path = file.relative_to(repo_path).as_posix()
                file_paths.append(rel_path)

        return RepoMetadata(
            name=repo_path.name,
            source=str(repo_path),
            default_branch="local",
            commit="N/A",
            working_dir=str(repo_path),
            file_paths=sorted(file_paths),
        )

    @staticmethod
    def resolve_git(url: str, branch: str = None) -> RepoMetadata:
        """Clone a git repository and resolve its metadata.

        Args:
            url: Git repository URL (public repos only).
            branch: Branch to check out (default: remote default branch).

        Returns:
            RepoMetadata with the cloned repo path and commit SHA.

        Raises:
            ValueError: If URL is invalid or clone fails.
            RuntimeError: If git operations fail.
        """
        # Validate URL is a git URL
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("git@")):
            raise ValueError(f"Invalid git URL: {url}")

        temp_dir = tempfile.mkdtemp(prefix="spec_atlas_repo_")

        try:
            # Clone shallow (--depth=1) for speed
            clone_cmd = ["git", "clone", "--depth=1"]
            if branch:
                clone_cmd.extend(["--branch", branch])
            clone_cmd.extend([url, temp_dir])

            result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(f"Git clone failed: {result.stderr}")

            repo_path = Path(temp_dir)

            # Get commit SHA at HEAD
            commit_cmd = ["git", "-C", temp_dir, "rev-parse", "HEAD"]
            result = subprocess.run(commit_cmd, capture_output=True, text=True, timeout=10)
            commit_sha = result.stdout.strip() if result.returncode == 0 else "unknown"

            # Get current branch
            branch_cmd = ["git", "-C", temp_dir, "rev-parse", "--abbrev-ref", "HEAD"]
            result = subprocess.run(branch_cmd, capture_output=True, text=True, timeout=10)
            current_branch = result.stdout.strip() if result.returncode == 0 else "unknown"

            # Inventory files
            file_paths = []
            for file in repo_path.rglob("*"):
                # Skip .git directory
                if ".git" in file.parts:
                    continue
                if file.is_file():
                    rel_path = file.relative_to(repo_path).as_posix()
                    file_paths.append(rel_path)

            # Extract repo name from URL
            repo_name = url.split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]

            return RepoMetadata(
                name=repo_name,
                source=url,
                default_branch=current_branch,
                commit=commit_sha,
                working_dir=temp_dir,
                file_paths=sorted(file_paths),
            )

        except Exception as e:
            # Cleanup on failure
            try:
                rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp dir {temp_dir}: {cleanup_error}")
            raise RuntimeError(f"Failed to resolve git repository: {e}") from e
