# ADR-0001: v1 key decisions (groups, languages, embeddings)

Status: accepted (defaults — revisit after the first pilot)
Context: The architecture left three decisions open (ARCHITECTURE.md "Open decisions" D1–D3). Downstream specs (DATA-MODEL, FEATURES) need concrete defaults to proceed.

## Decision

**D1 — Group/tree formation.** Build the `group.md` tree skeleton from the **directory/package structure first** (deterministic, free, multi-language-friendly), then **refine with graph community detection** (e.g. Louvain/Leiden over the L1 call graph) where the folder layout poorly reflects real coupling. Target a **bounded number of functional areas (~tens)**, not hundreds — small enough that 3–8 pages answer most questions.

**D2 — Initial languages.** Ship **Python + TypeScript/JavaScript** query packs in v1 (covers the common stack). Additional languages (e.g. Go, Java) are additive follow-ons (FR-L2 / F-015).

**D3 — Embedding scope.** Embed **`group.md` summaries (primary retrieval)** and **specs (direct lookup)**. **Code spans are not embedded** — they are fetched by descending the tree.

## Alternatives considered
- D1: pure community detection (more semantic, but non-deterministic and slower to stabilize) or pure directory (misses cross-cutting coupling). The hybrid gets both.
- D3: embedding raw code nodes too (defeats the point — that's the costly baseline we're improving on).

## Consequences
- DATA-MODEL defines a `groups` tree (parent_id, summary, fingerprint) and group/spec embeddings; raw nodes carry no vectors.
- FEATURES sequences clustering before specify/embedding.
- All defaults are cost-neutral (local clustering + local embeddings). Revisit group formation and the language set after measuring on a real repo (eval harness, F-016).
