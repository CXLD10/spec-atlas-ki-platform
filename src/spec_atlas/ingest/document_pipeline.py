"""Document ingest pipeline: upload -> adapter -> persisted, embedded SourceUnits.

Mirrors the repo pipeline's persist+embed phases (api/ingest.py), but for a
single PDF/Excel/Markdown file instead of a git repo. The adapters
(ingest/adapters/{pdf,excel,markdown}.py) are unchanged — this module is
purely the wiring that was missing: nothing persisted their output, so no
document content was ever retrievable or citable.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from spec_atlas.db.analysis import Repo
from spec_atlas.db.analysis import SourceUnit as SourceUnitRow
from spec_atlas.embed.base import EmbeddingProvider
from spec_atlas.ingest.adapters.base import SourceAdapter
from spec_atlas.ingest.adapters.excel import ExcelAdapter
from spec_atlas.ingest.adapters.markdown import MarkdownAdapter
from spec_atlas.ingest.adapters.pdf import PDFAdapter
from spec_atlas.ingest.source_unit import SourceUnit as SourceUnitDC

logger = logging.getLogger(__name__)

# document source_format -> (Adapter class, source_type tag stored on SourceUnit rows)
ADAPTERS_BY_FORMAT: dict[str, type[SourceAdapter]] = {
    "pdf": PDFAdapter,
    "xlsx": ExcelAdapter,
    "md": MarkdownAdapter,
}
SOURCE_TYPE_BY_FORMAT = {"pdf": "pdf", "xlsx": "excel", "md": "markdown"}

EXTENSION_TO_FORMAT = {
    ".pdf": "pdf",
    ".xlsx": "xlsx",
    ".md": "md",
    ".markdown": "md",
}

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # matches embed/pipeline.py's DEFAULT_MODEL

_PDF_LOCATOR_RE = re.compile(r":p\.(\d+)$")
_EXCEL_LOCATOR_RE = re.compile(r":sheet=(.*):row=(\d+)$")
_MARKDOWN_LOCATOR_RE = re.compile(r":section=(.*)$")


def detect_format(filename: str) -> str | None:
    """Map a filename's extension to a document source_format, or None if unsupported."""
    suffix = Path(filename).suffix.lower()
    return EXTENSION_TO_FORMAT.get(suffix)


def _locator_fields(source_format: str, locator: str) -> dict[str, object]:
    """Parse an adapter's locator string into typed columns.

    Locator formats are adapter-owned and covered by tests/ingest/ — this
    only reads them, never changes adapter behavior.
    """
    if source_format == "pdf":
        m = _PDF_LOCATOR_RE.search(locator)
        return {"page": int(m.group(1))} if m else {}
    if source_format == "xlsx":
        m = _EXCEL_LOCATOR_RE.search(locator)
        return {"sheet": m.group(1), "row": int(m.group(2))} if m else {}
    if source_format == "md":
        m = _MARKDOWN_LOCATOR_RE.search(locator)
        return {"section": m.group(1)} if m else {}
    return {}


def persist_source_units(
    repo_id, source_type: str, units: list[SourceUnitDC], source_format: str, session: Session, session_id=None
) -> list[SourceUnitRow]:
    """Persist in-memory adapter SourceUnits as durable, citable DB rows."""
    rows = []
    for unit in units:
        locator = unit.citation_locator()
        row = SourceUnitRow(
            session_id=session_id,
            repo_id=repo_id,
            source_id=unit.source_id,
            source_type=source_type,
            text=unit.text,
            structure=unit.structure,
            locator=locator,
            **_locator_fields(source_format, locator),
        )
        session.add(row)
        rows.append(row)
    session.commit()
    return rows


def embed_source_units(
    repo_id, rows: list[SourceUnitRow], embed_provider: EmbeddingProvider, session: Session, session_id=None
) -> int:
    """Embed each SourceUnit's text and store in the embeddings table."""
    from spec_atlas.db.analysis import Embedding

    if not rows:
        return 0

    texts = [row.text for row in rows]
    vectors = embed_provider.embed(texts)

    for row, vector in zip(rows, vectors, strict=True):
        session.add(
            Embedding(
                session_id=session_id,
                owner_kind="source_unit",
                owner_ref=str(row.id),
                model=EMBED_MODEL,
                repo_id=repo_id,
                vector=vector,
            )
        )
    session.commit()
    return len(rows)


def run_document_ingest_sync(
    job_id: str,
    file_path: str,
    original_filename: str,
    source_format: str,
    session_factory,
    embed_provider: EmbeddingProvider,
    session_id=None,
) -> None:
    """Synchronous document ingest: parse -> persist SourceUnits -> embed.

    Runs off the event loop via asyncio.to_thread (file parsing blocks),
    mirroring _run_ingest_sync's pattern for repos.
    """
    from spec_atlas.ingest.job_store import IngestJobStore

    session = session_factory()
    try:
        IngestJobStore.update_job_status(session, job_id, status="in_progress", progress_pct=10)

        adapter_cls = ADAPTERS_BY_FORMAT[source_format]
        adapter = adapter_cls(source_id=original_filename, file_path=file_path)
        units = asyncio.run(adapter.ingest())
        IngestJobStore.update_job_status(session, job_id, status="in_progress", progress_pct=50)

        repo = Repo(
            session_id=session_id,
            name=original_filename,
            source=original_filename,
            source_format=source_format,
        )
        session.add(repo)
        session.flush()

        rows = persist_source_units(
            repo.id, SOURCE_TYPE_BY_FORMAT[source_format], units, source_format, session, session_id
        )
        IngestJobStore.update_job_status(session, job_id, status="in_progress", progress_pct=80)

        embed_source_units(repo.id, rows, embed_provider, session, session_id)
        IngestJobStore.update_job_status(session, job_id, status="in_progress", progress_pct=99)

        logger.info(
            f"Job {job_id}: ingested document {original_filename!r} "
            f"({len(rows)} source units, repo_id={repo.id})"
        )
        IngestJobStore.update_job_status(session, job_id, status="done", progress_pct=100)

    except Exception as e:
        logger.error(f"Document ingest job {job_id} failed: {e}", exc_info=True)
        IngestJobStore.update_job_status(
            session, job_id, status="error", progress_pct=0, error_message=str(e)
        )
    finally:
        session.close()
        try:
            Path(file_path).unlink(missing_ok=True)
        except OSError:
            pass


async def process_document_ingest_job(
    job_id: str,
    file_path: str,
    original_filename: str,
    source_format: str,
    session_factory,
    embed_provider: EmbeddingProvider,
    session_id=None,
) -> None:
    """Background task: real document ingest work, run off the event loop."""
    await asyncio.to_thread(
        run_document_ingest_sync,
        job_id,
        file_path,
        original_filename,
        source_format,
        session_factory,
        embed_provider,
        session_id,
    )
