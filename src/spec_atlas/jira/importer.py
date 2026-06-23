"""Jira export JSON → SourceUnit rows.

Reads a Jira "Export to JSON" file (list of issues or ``{"issues": [...]}``
format) and persists each issue as a SourceUnit row with
``source_type='jira'``.  Import is idempotent: issues that already have a
matching ``locator`` (``jira:<KEY>``) are skipped.

A Repo row with ``source_format='md'`` is created once per project key and
reused on subsequent imports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JiraImporter:
    """Import Jira issues from an export JSON file as SourceUnits."""

    @staticmethod
    def import_from_file(
        file_path: str | Path,
        project_key: str,
        session,
    ) -> tuple[str, int]:
        """Read *file_path* and persist SourceUnit rows for each issue.

        Args:
            file_path: Path to the Jira export JSON file.
            project_key: Jira project key (e.g. ``"ATLAS"``).
            session: Open SQLAlchemy session for the Analysis DB.

        Returns:
            ``(repo_id_str, count)`` — repo UUID string and number of new units
            created (0 if all already existed).
        """
        from spec_atlas.db.analysis import Repo, SourceUnit

        data: Any = json.loads(Path(file_path).read_text())
        issues: list[dict] = (
            data if isinstance(data, list) else data.get("issues", [])
        )

        # Find or create a Repo row for this Jira project.
        # source_format='md' is the closest existing text-document format;
        # source_type='jira' on SourceUnit is the real discriminator.
        repo: Repo | None = session.query(Repo).filter(
            Repo.name == project_key,
            Repo.source_format == "md",
        ).first()

        if repo is None:
            repo = Repo(
                name=project_key,
                source=f"jira://{project_key}",
                source_format="md",
            )
            session.add(repo)
            session.flush()

        count = 0
        for issue in issues:
            key: str = issue.get("key", "")
            if not key:
                continue

            locator = f"jira:{key}"

            # Idempotency guard — skip already-indexed issues
            exists = (
                session.query(SourceUnit)
                .filter(SourceUnit.repo_id == repo.id, SourceUnit.locator == locator)
                .first()
            )
            if exists:
                continue

            summary: str = issue.get("summary", "")
            description: str = issue.get("description", "") or ""
            status: Any = issue.get("status", {})
            if isinstance(status, dict):
                status = status.get("name", "")
            created: str = issue.get("created", issue.get("createdAt", "")) or ""
            url: str = issue.get("url", issue.get("self", "")) or ""

            text_parts = [f"{key}: {summary}", f"Status: {status}"]
            if created:
                text_parts.append(f"Created: {created}")
            if description:
                text_parts.append(f"\nDescription:\n{description}")
            text = "\n".join(text_parts)

            unit = SourceUnit(
                repo_id=repo.id,
                source_id=project_key,
                source_type="jira",
                text=text,
                locator=locator,
                section=key,
                structure={
                    "key": key,
                    "summary": summary,
                    "status": status,
                    "created": created,
                    "url": url,
                },
            )
            session.add(unit)
            count += 1

        session.commit()
        return str(repo.id), count
