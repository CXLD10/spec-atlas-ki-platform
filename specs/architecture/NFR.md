# NFR.md — Spec-Atlas (Non-Functional Requirements)

Status: ready

## Cost
- **Hard constraint: $0.** Local compute + free tiers only. Any paid dependency requires an accepted ADR (default: rejected).

## Security
- The indexing and spec-generation pipeline **only reads files and calls the model — it never executes repository code or runs commands.** Static analysis only.
- No secrets in the repo; `.env` gitignored; `.env.example` documents required vars.

## Privacy
- Source code stays on the user's machine. The DB stores structure (symbols, edges, line spans, hashes), generated summaries/specs, and embeddings — **not** raw file contents. Answers read source from local disk at query time.

## Performance (targets)
- Index a ~20k-LOC repo locally in < ~5 min.
- Answer (route + retrieve + generate) in < ~10 s on a free-tier LLM.
- Incremental: regenerate a changed area's subtree in < ~5 s.
- Spec/group context per question ≥ 3× smaller than a raw-node baseline (estimate; validated by the eval harness).

## Reliability
- Idempotent re-ingest (stable keys, content-hash skip).
- Every external call handles 429 / timeout / cold-start with retry + backoff; a failed LLM call degrades to "couldn't generate," never a crash.
- Specs immutable per version; fingerprints make staleness visible, never silent.

## Correctness & grounding
- No answer/spec field/group claim without provenance (`{file,start_line,end_line}`).
- Edge confidence recorded; answers distinguish certain vs. heuristic relationships.
- The spec verifier catches invariants unsupported by code before a spec is `verified`.
- Spec-graph links derive from real code edges, never AI guesses.

## Observability
- Structured per-stage logs (counts: files, nodes, edges, groups, specs, embeddings, tokens used).
- A `stats` surface for the last index run + cumulative LLM token usage (stay within free quotas).

## Maintainability / agent-buildability
- Everything behind interfaces (LLM, embeddings, DB, language packs) for swap + test.
- Additive feature modules; shared contracts frozen in specs before dependents build.
- Tests required (`testing-standard`); contract tests run offline against fakes so CI is free.

## Portability
- macOS/Linux/Windows; no GPU (CPU embeddings).
