"""File inventory with content hashing and LOC counting."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import File, Repo


class FileInventory:
    """Scan files, compute hashes and LOC, upsert to the Analysis DB."""

    @staticmethod
    def scan(
        repo_metadata,
        file_paths: list[str],
        analysis_db_session: Session,
        session_id=None,
    ) -> tuple[Repo, list[File]]:
        """Scan files, compute hashes/LOC, upsert to DB.

        Args:
            repo_metadata: RepoMetadata from T-001.1 resolver.
            file_paths: List of relative file paths from repo root.
            analysis_db_session: SQLAlchemy session to the Analysis DB.

        Returns:
            Tuple of (Repo row, list of File rows).
        """
        repo_path = Path(repo_metadata.working_dir)

        # Upsert Repo row
        repo = (
            analysis_db_session.query(Repo)
            .filter_by(
                name=repo_metadata.name,
                source=repo_metadata.source,
            )
            .first()
        )

        if repo is None:
            repo = Repo(
                session_id=session_id,
                name=repo_metadata.name,
                source=repo_metadata.source,
                default_branch=repo_metadata.default_branch,
                indexed_commit=repo_metadata.commit,
            )
            analysis_db_session.add(repo)
            analysis_db_session.flush()
        else:
            repo.indexed_commit = repo_metadata.commit
            repo.default_branch = repo_metadata.default_branch

        # Scan and upsert files
        files = []
        for file_path in file_paths:
            full_path = repo_path / file_path
            if not full_path.exists():
                continue

            # Compute content hash
            content_hash = _compute_hash(full_path)

            # Count lines
            loc = _count_loc(full_path)

            # Placeholder; overwritten by LanguageDetector.detect() in the ingest
            # pipeline's phase 3 (api/ingest.py), which runs after this scan.
            language = "unknown"

            # Upsert File row
            file = (
                analysis_db_session.query(File)
                .filter_by(
                    repo_id=repo.id,
                    path=file_path,
                )
                .first()
            )

            if file is None:
                file = File(
                    session_id=session_id,
                    repo_id=repo.id,
                    path=file_path,
                    language=language,
                    content_hash=content_hash,
                    loc=loc,
                )
                analysis_db_session.add(file)
            else:
                # Check if content changed
                if file.content_hash != content_hash:
                    file.content_hash = content_hash
                    file.loc = loc

            files.append(file)

        analysis_db_session.commit()
        return repo, files


def _compute_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file content.

    Args:
        file_path: Path to the file.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
    except Exception:
        # Binary file or read error; use a placeholder
        return "error"
    return hasher.hexdigest()


def _count_loc(file_path: Path) -> int:
    """Count non-empty lines in a file.

    Args:
        file_path: Path to the file.

    Returns:
        Number of non-empty lines.
    """
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0
