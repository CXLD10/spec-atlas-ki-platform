# Phase 2 — Real document ingestion (close the biggest "multi-source" gap)

**Effort:** L · **Depends on:** Phase 0, 1 · **Audit items:** §3.11, §3.22, PRODUCT feature 7

## Objective
Documents become first-class sources. Uploading a PDF/Excel/Markdown runs the existing adapters, persists `SourceUnit`s with precise locators, includes them in retrieval, and surfaces **citations that resolve to a real page/cell/section.** The "multi-source" USP becomes true, not aspirational.

> The adapters (`ingest/adapters/{pdf,excel,markdown}.py`) already parse correctly in isolation (`tests/ingest/`). The gap is purely wiring: no `POST /api/documents`, no persistence, no retrieval inclusion.

---

## Tasks

### 2.1 — `POST /api/documents` (multipart) + document ingest path *(Dev B, L)* — §3.22
- Accept multipart upload; route by type to the PDF/Excel/Markdown adapter.
- Run a document ingest path that produces `SourceUnit`s and embeds them, mirroring the repo pipeline's persist+embed phases.
- Return a real `job_id` consumable by `useIndexJob` (`GET /api/ingest/:jobId`) — kill the `mock-document-…` dead-end.
- **Frontend:** `OmniIngest` document path calls the new endpoint; progress + completion render like the repo path.

### 2.2 — Persist `SourceUnit`s + include in retrieval *(Dev B, L)*
- New table for `SourceUnit`s with locator columns (`page`, `cell`, `section`, `start_line`/`end_line` as applicable) + provenance.
- Embed and include them in vector search / tree descent so document content can be retrieved and **cited**.
- Answers over document knowledge carry resolvable citations (PDF page, Excel cell, MD section).

### 2.3 — Persistent docs store *(Dev B, M)* — §3.11
- `groups/group_writer.py:190-213` currently writes `group.md` into the **temp clone** (`ingest/resolver.py:91`), discarded after ingest.
- Write to a configured persistent docs directory (or object store); serve via an API. DB (`groups.summary_md`, `specs.content`) remains the durable source; this makes the on-disk Markdown durable too.

---

## Seed / fixtures
Add 2–3 real sample documents (a multi-page PDF, an Excel workbook with named cells, a Markdown doc) under `tests/fixtures/docs/`. Use them in both tests and a manual upload demo.

## Backend tests
```bash
pytest -q tests/ingest                       # adapters still green
pytest -q tests/api/test_documents.py        # new: upload→job→persisted units
pytest -q tests/retrieve                     # SourceUnits retrievable + cited
pytest -q
```
New tests:
- `test_upload_pdf_creates_source_units` — multipart → job done → `SourceUnit` rows with page locators.
- `test_upload_excel_cell_locators` — cell-level provenance persists.
- `test_markdown_section_locators`.
- `test_answer_cites_document_source` — an answer over doc content carries a resolvable page/cell/section citation.
- `test_group_md_persisted_to_durable_store` — file exists after ingest, served by API.

## Frontend integration checks
1. **Upload** a PDF in `OmniIngest` → real `job_id` → `/index/:jobId` climbs to 100% (no 404, no `mock-document-`).
2. Uploaded doc appears in **Sources** and **KnowledgeBase**.
3. **Ask** a question answerable only from the document → answer cites the **real page/cell/section**, and the citation link resolves to that locator.
4. Excel and Markdown uploads behave equivalently with correct locator types.

## Definition of Done
- `POST /api/documents` ingests PDF/Excel/Markdown to persisted, embedded `SourceUnit`s.
- Document citations resolve to real page/cell/section.
- `group.md` durable and served.
- New tests green; full suite green; adapters unchanged in behavior.

## Commit checkpoint
```
feat(phase2): real document ingestion — SourceUnits, locators, citations, durable docs
```
