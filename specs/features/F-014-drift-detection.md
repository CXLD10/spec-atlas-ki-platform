# F-014 — Drift Detection

Status: ready
References: ARCHITECTURE.md#components, DATA-MODEL.md, PRD.md#fr-i

## Intent

When code changes, specs/groups covering it become automatically `stale` — never silently wrong. On re-ingest, compare source fingerprints (hash of covered spans) against current code; mismatch → mark affected specs/groups `stale`. This enables a living product: the knowledge base updates itself when the code does, and consumers can trust that a non-stale spec reflects the current codebase.

## Contract

**Input:**
- A re-ingested repo (new L1 graph: nodes, edges, updated file contents)
- Previous fingerprints for specs/groups (stored in Spec DB and Analysis DB)

**Output:**
- Set of affected specs/groups marked with status `stale` + timestamp `staleness_detected_at`
- A drift report: what changed, which items became stale, why

**Logic:**
1. For each spec/group with a `source_fingerprint` in the DB:
   - Re-compute the fingerprint from the current source spans (current file contents + line ranges)
   - Compare: old fingerprint vs. new fingerprint
   - If different → mark the spec/group `stale`
2. For any spec/group covering a re-ingested file that was not in the previous ingest:
   - Mark as potential new coverage (not stale, but new)
3. Return a report: {stale_specs: [...], stale_groups: [...], new_coverage: [...], details: {...}}

**Fingerprint recomputation:**
- Use the same algorithm as during spec/group creation (F-005.3 / T-005.3)
- SHA256 of concatenated `{file}:{start_line}:{end_line}` for all covered spans, sorted

**Status transitions:**
- `verified` → `stale` (if fingerprint mismatch)
- `draft` → `stale` (if fingerprint mismatch)
- Stale specs are excluded from retrieval (F-007 search should skip `stale` specs)

## Acceptance criteria

- [x] (mapped to PRD FR-I1) Fingerprints detect source changes (same source = same fingerprint, different source = different fingerprint).
- [x] (mapped to PRD FR-I2) Specs/groups marked `stale` on re-ingest if their source has changed.
- [x] (mapped to PRD FR-I3) Stale specs are excluded from retrieval (search should not return stale specs).
- [x] (mapped to PRD FR-I4) Drift report is human-readable (audit trail for when things became outdated).
- [x] (mapped to NFR.md cost) On-demand, no background watching or webhooks (v1 is simple: drift check happens on re-ingest).
- [x] (mapped to testing-standard) Unit tests: fixture specs with changed source → verify fingerprint mismatch detected.

## Out of scope

- Real-time file watching / webhooks (v1 is on-demand; watching is Phase 6+ scope)
- Automatic regeneration of stale specs (stale is a flag; regeneration is manual or a later scheduled job)
- Auto-rollback or version pinning (versioning is immutable; stale is just a status, not a revert)

## Key decisions

**D1 — Fingerprints are deterministic:** Same source → same fingerprint, enforced by hash. No randomness. This enables idempotent re-ingests.

**D2 — Drift check runs on re-ingest only:** Not a background watcher. User (or a CI job) re-ingests the repo; drift check is automatic as part of ingest. Simple, no infrastructure for file watching / webhooks in v1.

**D3 — Stale items are excluded from retrieval:** Specs marked `stale` should not appear in search results (F-007 filter), because they're known to be outdated. This prevents hallucination based on stale specs.

**D4 — Status `stale` is advisory, not destructive:** Stale specs remain in the DB (immutable, auditable); consumers just know not to use them. Regeneration is a separate, opt-in action (not implemented in v1).

## Tasks

### T-014.1 — Fingerprint comparison engine
Status: ready · Depends on: [T-005.3, T-011.2] · Reads: [DATA-MODEL.md, ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/drift/detector.py, tests/drift/test_detector.py]
Contract: `DriftDetector` class:
  - `detect_drift(repo_id: uuid, new_ingestion: IngestResult) -> DriftReport` — compare old vs. new fingerprints, return stale items
  - Uses same fingerprint algorithm as F-005.3 (SHA256 of sorted spans)
  - Report includes: stale_specs (list), stale_groups (list), new_coverage (list), per-item change reason
DoD: unit test: fixture spec with old fingerprint, simulate re-ingest with changed source, verify DriftReport identifies mismatch.

### T-014.2 — Status update + retrieval filtering
Status: ready · Depends on: [T-014.1] · Reads: [DATA-MODEL.md, ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/spec/store.py (extend), src/spec_atlas/retrieve/search.py (extend), tests/spec/test_store.py, tests/retrieve/test_search.py]
Contract: Wire drift detector into ingest + retrieval:
  - `IngestPipeline.ingest() -> IngestResult` (extend): after storing new L1 graph, run drift detector, mark stale specs/groups
  - `DriftDetector.mark_stale(drift_report, session)` → update Spec DB: set status=`stale`, staleness_detected_at=now
  - `VectorSearch.search() -> list[Group]` (extend): filter out any groups with member_specs marked `stale`
DoD: integration test: ingest → change source → re-ingest → verify stale items marked in DB + excluded from search.

## HANDOFF / STATUS

_(agents append HANDOFF notes here per the playbook)_
