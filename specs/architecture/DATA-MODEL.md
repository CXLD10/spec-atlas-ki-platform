# DATA-MODEL.md — Spec-Atlas

Status: ready
References: ARCHITECTURE.md, INTEGRATIONS.md; decisions in ADR-0001

Two logical databases (PostgreSQL on Neon free; `pgvector` enabled in the Analysis DB):
- **Analysis DB** — rebuildable: code graph (L1), the group tree (L4), and all embeddings. Disposable; re-derivable from source.
- **Spec DB** — durable, per-user, versioned: specs (L2) and the spec graph (L3).

Cross-DB references are **by value (refs), never FK** — the Spec DB is independent of the Analysis DB. Conventions: uuid surrogate keys; UTC `created_at`/`updated_at`; the DB stores structure + summaries + specs, **never raw source**.

---

## Analysis DB

### `projects` (Phase 0, new in v2.0)
`id` uuid pk · `name` · `description` · `created_at` · `ingest_status` (`queued|ingesting|complete|failed`) · `ingest_progress` real 0–1 · `indexed_at` timestamp null. **Root scope for all downstream data.** All repos, sources, specs, memory, embeddings are scoped to a project.

### `repos`
`id` uuid pk · `project_id` fk · `name` · `source` (path/URL) · `default_branch` · `indexed_commit` (sha) · timestamps. **Scoped to project.**

### `files`
`id` pk · `repo_id` fk · `path` · `language` · `content_hash` · `loc`. Unique `(repo_id, path)`.

### `sources` (Phase 1, multi-source)
`id` uuid pk · `project_id` fk · `type` enum (`code|pdf|markdown|excel|jira|git_history`) · `name` · `metadata` jsonb (language, pages, encoding) · `ingest_status` · `created_at`. **Each project can have multiple sources.** Code source is implicit; other sources are added explicitly.

### `source_locators` (Phase 1, multi-source citations)
Normalized representation of where content lives in each source type:
```
CodeLocator:      {source_id, file_path, start_line, end_line}
PDFLocator:       {source_id, page_num, bbox: [x0,y0,x1,y1]}
TextLocator:      {source_id, section_id, offset_start, offset_end}
ExcelLocator:     {source_id, sheet_name, cell_start, cell_end}
```
Stored as polymorphic `locator_type` + `locator_data` jsonb in a single `source_locators` table or separate typed tables per source.

### `nodes` (L1 symbols)
`id` pk · `repo_id` fk · `file_id` fk · `language` · `kind` (`module|class|function|method`) · `name` · `qualified_name` · `signature` · `docstring` · `start_line` · `end_line`.
**Stable identity:** `(repo_id, language, qualified_name, kind)` — idempotent re-ingest. No embeddings on nodes (ADR-0001 D3).

### `edges` (L1)
`id` pk · `repo_id` fk · `src_node_id` · `dst_node_id` · `kind` (`imports|calls|inherits|defines`) · `confidence` real 0–1 (heuristic/dynamic < 1). Index `(repo_id, src_node_id)`, `(repo_id, dst_node_id)`.

### `groups` (L4 tree)
`id` pk · `repo_id` fk · `parent_id` uuid null (null = root) · `level` int · `path` text (e.g. `auth/tokens`) · `title` · `summary_md` text (the `group.md` page) · `member_node_ids` uuid[] · `member_spec_refs` text[] (component_refs into the Spec DB) · `source_fingerprint` text (hash of covered source spans — drives staleness) · timestamps. Index `(repo_id, parent_id)`.

### `embeddings`
`owner_kind` (`group|spec`) · `owner_ref` (group `path` or spec `component_ref@version`) · `repo_id` · `vector` vector(384) · `model`. PK `(owner_kind, owner_ref, model)`. **Groups = primary retrieval surface; specs = direct lookup.** (ADR-0001 D3.)

---

## Spec DB (separate)

### `specs` (L2)
`id` pk · `user_id` · `repo` (loose ref) · `component_ref` (the area/group path or qualified_name) · `version` int (monotonic per `(user_id, repo, component_ref)`) · `valid_from` · `valid_to` (null = current) · `status` (`draft|verified|stale`) · `content` jsonb (schema below) · `provenance` jsonb (list of `{file_path,start_line,end_line}`) · `source_fingerprint` text (hash of source the spec was generated from) · `created_at`. Unique `(user_id, repo, component_ref, version)`. Current = `valid_to is null`.

### `spec_edges` (L3 spec graph)
`id` pk · `user_id` · `repo` · `src_component_ref` · `dst_component_ref` · `kind` (`depends-on|part-of|uses`) · `derived_from` (the L1 edge kind that produced it — links are from real code edges, never AI guesses). Index `(user_id, repo, src_component_ref)`.

### `memory_facts` (Phase 3, conversation memory)
`id` uuid pk · `user_id` · `project_id` fk · `fact` text (e.g., "entry point is main.py") · `sources` text[] (`code|pdf|markdown|excel|jira`) · `provenance` jsonb (list of locators: `{locator_type, locator_data}`) · `relevance_score` real 0–1 (TBD: static 1.0 or LLM-ranked) · `created_from_turn` (conversation_id + turn_num) · `created_at` · `last_used_at`. **Durable facts, not ephemeral.** Index `(user_id, project_id, created_at)` for retrieval.

### `conversations` (Phase 3, conversation history)
`id` uuid pk · `user_id` · `project_id` fk · `created_at` · `turns` jsonb (list of {query, answer, citations, memory_facts_used}). **For traceability and memory enrichment.**

### Spec `content` shape (validated by JSON Schema)
```
{
  "purpose": "...",
  "inputs":  [{"name","type","description"}],
  "outputs": [{"name","type","description"}],
  "dependencies": ["component_ref", ...],
  "invariants":   ["..."],          # each grounded by an entry in provenance
  "side_effects": ["..."],
  "failure_modes":["..."]
}
```

---

## Rules
- **Idempotency:** re-ingest upserts on the node stable key; unchanged files (same `content_hash`) are skipped.
- **Versioning:** specs are immutable per version; an update creates a new version and sets the prior `valid_to`.
- **Fingerprints / drift:** if a spec's or group's `source_fingerprint` no longer matches current source spans, mark it `stale`; only the affected subtree regenerates.
- **Provenance:** every spec field, group claim, and answer carries provenance. For code: `{file, start_line, end_line}`. For multi-source: `{source_id, locator_type, locator_data}` (e.g., `{source_id: "pdf_001", locator_type: "PDFLocator", locator_data: {page: 5, bbox: [0.1, 0.2, 0.9, 0.8]}}`). Without it, it is not allowed.
- **Layer placement:** L1 + L4 + embeddings = Analysis DB (rebuildable index); L2 + L3 + memory = Spec DB (durable). Groups reference specs by `component_ref`.
- **Project scoping:** all data (repos, sources, specs, memory, embeddings) is scoped to a `project_id`. Multi-project deployments partition by project.
- **Multi-source citations:** answers aggregate citations from all sources; frontend renders by source type (code snippet with file:line, PDF with page/bbox, Markdown with excerpt, etc.).
- **Memory durability:** memory facts persist across sessions within a project. Relevance scores are computed at query time (vector similarity or LLM-ranked TBD).
