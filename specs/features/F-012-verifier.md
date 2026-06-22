# F-012 — Spec Grounding Verifier

Status: ready
References: ARCHITECTURE.md#layered-knowledge-model, DATA-MODEL.md#spec-db, PRD.md#fr-g

## Intent

Catch hallucinated invariants before a spec is trusted. A verifier re-reads the source spans cited in a spec's provenance and checks whether the claimed properties (purpose, I/O, invariants, side effects) are actually grounded in the code. Specs that fail verification stay `draft`; only verified specs become `verified` and are deemed safe to rely on.

## Contract

**Input:**
- A `Spec` object (from Spec DB, with component_ref, content, provenance)
- The L1 graph region it covers (nodes, edges, source spans)
- Optional: an LLM provider (for semantic verification as a stretch goal)

**Output:**
- Pass/fail per invariant + overall spec status (`draft` → `verified` or stays `draft`)
- A verification report: structured list of claims, each with pass/fail + reason (useful for debugging why a spec failed)

**Verification logic (v1: rule-based + provenance recheck):**
1. For each claim in the spec (purpose, inputs, outputs, dependencies, invariants, side_effects, failure_modes):
   - Extract the claimed text
   - Fetch the cited provenance spans from the code
   - Apply a rule: does the span text plausibly support the claim?
   - Rule examples:
     - **Purpose claim:** docstring exists and contains key terms from the claim → pass
     - **Inputs/Outputs:** function signature matches the claimed I/O structure → pass
     - **Dependencies:** L1 edges exist matching the claimed dependencies → pass
     - **Invariants:** code patterns match (e.g., "returns non-null" + code has explicit null-checks or return type hints) → pass
   - If any claim fails the rule → spec stays `draft`
2. Only if all claims pass → mark spec `verified`

**Report structure:**
```json
{
  "spec_ref": "AuthService",
  "version": 1,
  "status": "verified",
  "claims": [
    {
      "field": "purpose",
      "claim": "Handles user authentication and session management",
      "result": "pass",
      "reason": "Docstring matches; file:line 42–50 contains both 'authentication' and 'session'",
      "provenance": {"file": "auth.py", "start_line": 42, "end_line": 50}
    },
    {
      "field": "invariants",
      "claim": "Tokens expire after 1 hour",
      "result": "fail",
      "reason": "Code shows 24-hour expiry (line 103), contradicts claim",
      "provenance": {"file": "auth.py", "start_line": 103, "end_line": 105}
    }
  ],
  "overall_pass": false
}
```

## Acceptance criteria

- [x] (mapped to PRD FR-G1) Verify spec claims against code provenance (rule-based, deterministic).
- [x] (mapped to PRD FR-G2) Specs fail verification if any claim contradicts the source spans.
- [x] (mapped to PRD FR-G3) Verified specs are marked `verified` in Spec DB; draft specs stay draft.
- [x] (mapped to PRD FR-G4) Verification report is human-readable (useful for debugging spec quality).
- [x] (mapped to NFR.md cost) No cost: rule-based checks only, reuses existing code spans (no new LLM calls for v1).
- [x] (mapped to testing-standard) Unit tests: verify fixture specs with known-good and known-bad claims; check report structure.

## Out of scope

- Semantic verification via LLM (v1 is rule-based; LLM-assisted checks are P1 future work)
- Auto-repair of failed specs (verification is pass/fail only; repair is manual or requires re-spec)
- Real-time verification on spec generation (verification happens on-demand, post-generation)

## Key decisions

**D1 — Rule-based verification first:** Start with simple, deterministic rules (docstring presence, signature structure, edge existence). These catch the obvious hallucinations. LLM-assisted semantic verification (e.g., "does this behavior description match the implementation?") is a stretch goal, useful only if rule-based verification passes most specs and you want to squeeze out the last 5–10% of edge cases.

**D2 — Verification report is structured:** JSON report (not free text) makes it easy to aggregate across many specs ("X% passed", "most common failure reason", etc.) and to build tooling (e.g., a dashboard showing spec quality over time).

**D3 — Verification is opt-in (v1):** Users explicitly call `/specs/{ref}/verify` or an ingest-time flag triggers it. Not automatic on every spec generation, because verification is deterministic and can be re-run anytime if code changes (see F-014 drift detection).

## Tasks

### T-012.1 — Verifier core
Status: ready · Depends on: [T-011.2] · Reads: [DATA-MODEL.md#spec-db, ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/verify/engine.py, tests/verify/test_engine.py]
Contract: `SpecVerifier` class:
  - `verify_spec(spec: Spec, graph_context: dict) -> VerificationReport` — run rule-based checks per claim, return structured report
  - Rules: docstring presence for purpose, signature matching for I/O, edge existence for dependencies, code pattern matching for invariants
  - Report: JSON-serializable VerificationReport with per-claim pass/fail + reason
DoD: unit tests on fixture specs (mock graph context); verify known-good specs pass, known-bad specs fail.

### T-012.2 — Status transition + API
Status: ready · Depends on: [T-012.1] · Reads: [DATA-MODEL.md#spec-db, ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/spec/store.py (extend), tests/spec/test_store.py (extend), src/spec_atlas/api/specs.py (extend)]
Contract: Wire verifier into Spec store + FastAPI:
  - `SpecStore.verify_spec(spec_id) -> VerificationReport` — call verifier, update spec status to `verified` if report passes
  - `PATCH /specs/{component_ref}/verify` endpoint — trigger verification, return report
  - Idempotency: running verify twice on the same spec is idempotent (same report, same status change)
DoD: integration test: POST /specs → PATCH /verify → confirm status changed to `verified` and report is returned.

### T-012.3 — Verification report API + dashboard stub
Status: ready · Depends on: [T-012.2] · Reads: [skills: testing-standard]
Owns: [src/spec_atlas/api/verify.py (new), tests/api/test_verify.py (new)]
Contract: New endpoint:
  - `GET /specs/{component_ref}/verification-report` — fetch the most recent verification report for a spec
  - Response includes all past verification runs (each with timestamp, pass/fail, top failure reasons)
DoD: unit test: verify a spec, then fetch its report; confirm all fields present and timestamps monotonic.

## HANDOFF / STATUS

_(agents append HANDOFF notes here per the playbook)_
