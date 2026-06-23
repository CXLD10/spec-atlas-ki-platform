# EXECUTION PROMPT — Phase 2: Real document ingestion

Repo: `CXLD10/spec-atlas-ki-platform`. Phases 0–1 done. Goal: documents become first-class sources — upload PDF/Excel/Markdown, run the existing adapters, persist `SourceUnit`s with locators, include them in retrieval, and surface citations that resolve to real page/cell/section.

## Rules
- The adapters (`ingest/adapters/{pdf,excel,markdown}.py`) already work in isolation — **don't rewrite them**, wire them. Provenance mandatory. Offline contract holds.

## Do these, in order

**1. `POST /api/documents` + ingest path (Dev B).** Accept multipart upload; route by type to the right adapter; run a document ingest path producing `SourceUnit`s and embedding them (mirror the repo pipeline's persist+embed phases). Return a real `job_id` consumable by `useIndexJob` (`GET /api/ingest/:jobId`). Frontend: `OmniIngest` document path calls this; kill the `mock-document-…` dead-end so progress/completion render like the repo path.

**2. Persist `SourceUnit`s + retrieval inclusion (Dev B).** New table with locator columns (`page`/`cell`/`section`/`start_line`/`end_line` as applicable) + provenance. Embed and include `SourceUnit`s in vector search / tree descent so document content is retrievable and **citable**. Answers over doc knowledge carry resolvable citations.

**3. Persistent docs store (Dev B).** `groups/group_writer.py:190-213` writes `group.md` into the temp clone (`ingest/resolver.py:91`), which is discarded. Write to a configured persistent docs dir (or object store) and serve via an API. DB stays the durable source; this makes on-disk Markdown durable too.

## Seed
Add real sample docs under `tests/fixtures/docs/`: a multi-page PDF, an Excel workbook with named cells, a Markdown doc. Use in tests + a manual upload demo.

## Must pass before commit
```bash
pytest -q tests/ingest
pytest -q tests/api/test_documents.py
pytest -q tests/retrieve
pytest -q
cd frontend && npm run build && npm run test
```
Add: `test_upload_pdf_creates_source_units`, `test_upload_excel_cell_locators`, `test_markdown_section_locators`, `test_answer_cites_document_source`, `test_group_md_persisted_to_durable_store`.

## Frontend checks (manual)
1. Upload a PDF in `OmniIngest` → real `job_id` → `/index/:jobId` to 100% (no 404, no `mock-document-`).
2. Uploaded doc appears in Sources + KnowledgeBase.
3. Ask a doc-only question → answer cites the real page/cell/section and the link resolves.
4. Excel + Markdown behave equivalently with correct locator types.

## STOP & COMMIT
```
feat(phase2): real document ingestion — SourceUnits, locators, citations, durable docs
```
Report changed files, test output, and a demo note showing a resolvable document citation. Do not start Phase 3.
