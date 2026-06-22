# Spec-Atlas — Product Requirements Document (PRD)

| | |
|---|---|
| **Product** | Spec-Atlas |
| **Version** | 1.1 (draft) |
| **Status** | For review |
| **Tagline** | From what the code *is* to what the code *means*. |
| **Related docs** | `specs/architecture/ARCHITECTURE.md`, `DATA-MODEL.md`, `INTEGRATIONS.md`, `NFR.md`, `specs/FEATURES.md`, `docs/PLAYBOOK.md` |
| **Supersedes** | `specs/product/VISION.md` + `SCOPE.md` (this PRD is the canonical product doc; those remain as focused sub-specs) |

> Note: the project was previously code-named *Sextant*. The repo root should be `spec-atlas`.
>
> **v1.1 changes** (informed by a reference pitch for a similar feature on another product): multi-language is now P0 via tree-sitter; the layered group.md model is reflected throughout; added dual-path retrieval with a router; added context-size/cost success metrics measured head-to-head against a baseline; added an evaluation requirement; added an execution-free security posture; elevated "living onboarding docs" to a first-class deliverable.

---

## 1. Overview

Spec-Atlas ingests a code repository (any supported language, via tree-sitter), builds a structural **code knowledge graph**, then layers understanding on top of it: an LLM generates structured, versioned **specs** from the graph; those specs link into a higher-level **spec graph**; and the whole thing rolls up into a navigable **`group.md` tree** of context-rich summaries. Specs are stored in a dedicated database and served over an API and an MCP server so AI coding agents (Claude Code, Codex, Gemini) build against an accurate, persistent model of the codebase instead of re-deriving it every prompt. The shift it delivers: from *what the code is* (structure) to *what the code means* (intent, contracts, and the "why") — so it can answer like an architect, not a search index.

**Two retrieval paths coexist.** Precise symbol-level questions ("what calls X", "what breaks if I rename this") are served by the **code-graph path**, unchanged. Big-picture questions ("why is it built this way", "walk me through a flow") are served by the **spec/group path**: a fast vector search over the `group.md` tree, then a descent into the matching specs and source — not a live graph traversal and not flat text chunks.

The product runs **local-first at zero cost**: the only external dependencies are a free managed Postgres and a free-tier LLM. It is explicitly not a generic documentation chatbot — every answer and every spec field is grounded in real source spans.

## 2. Problem statement

Three compounding problems motivate Spec-Atlas:

1. **Human comprehension is slow.** Understanding an unfamiliar, large, or legacy codebase takes days of archaeology. Docs rot, keyword search has no structural understanding, and the relationships that explain a system — who calls what, what depends on what, and *why* — are invisible in a file tree.
2. **AI agents lack grounding.** Coding agents do their worst work without an accurate, structured model of the repo. They hallucinate APIs, miss cross-cutting context, and waste tokens re-reading the same files every session.
3. **Raw-graph Q&A is costly.** Intent, contracts, and "why" live across whole regions of code — no single node holds them. Answering a question by dragging dozens of raw, low-level nodes into the model is slow, noisy, and expensive.

Spec-Atlas attacks all three: a graph for precise detail, durable specs and a group tree for meaning, and small dense context per question.

## 3. Goals and non-goals

### Goals
- Let a user understand an unfamiliar repository in minutes via grounded, cited answers.
- Produce structured, versioned specs that downstream agents and humans can rely on, in any supported language.
- Keep specs traceable to code and flag them when the code drifts.
- Answer big-picture questions with small, dense context (fewer tokens, lower cost) than a raw-node baseline.
- Operate at **$0** and keep source code private to the user's machine.

### Non-goals
- Not a chatbot or general assistant; it answers only about the indexed repo and refuses beyond it.
- Not a generic doc-RAG tool; retrieval is graph/spec-grounded with mandatory provenance.
- Does not edit or auto-apply code changes (it informs agents; agents act).
- No runtime/dynamic analysis (static only). The indexing/spec pipeline **only reads files and calls the model — it never executes repository code or runs commands.**
- Not a paid or multi-tenant SaaS in v1 (single-user, personal use first).

## 4. Success metrics

| Metric | Target (v1) | How measured |
|---|---|---|
| Index speed | ~20k-LOC repo indexed locally in < 5 min | timed run on a laptop |
| Retrieval accuracy | Correct source span cited in ≥ 80% of answers | curated Q&A test set |
| Context size per question | ≥ 3× smaller than a raw-node baseline (estimate) | head-to-head on the question set |
| Cost per question | materially lower than baseline (target ~60%+; estimate) | head-to-head on the question set |
| Spec groundedness | 0 invariants unsupported by code in `verified` specs | verifier pass rate |
| Agent uplift | Agent using a Spec-Atlas spec completes a scoped change correctly more often than without | A/B on fixture tasks |
| Cost (running) | $0 | dependency audit |
| Incremental re-index | Changed file's affected subtree regenerated in < 5 s | timed run |

Context/cost figures are design estimates; a measurement phase validates them head-to-head against the raw-node baseline before any auto-routing decision (we commit to numbers, not enthusiasm).

## 5. Target users and personas

**Persona A — The Onboarding Engineer.** Just joined a team, handed a large unfamiliar repo. Needs "how does auth work, what calls this, what breaks if I change it" without reading everything. Values speed, trustworthy citations, and an always-current map.

**Persona B — The Agent-Augmented Developer (primary).** Runs Claude Code / Codex daily. Wants to hand the agent an accurate spec of the relevant area so it implements changes correctly the first time, and to stop re-explaining the codebase every session.

**Persona C — The Spec-Driven Lead.** Practices spec-driven development. Wants durable specs that stay tied to actual code and get flagged when stale, so specs remain a source of truth rather than rotting docs.

## 6. User stories

- **US-1** As an onboarding engineer, I can ask "how does X work?" and get an answer with links to exact files and lines, so I trust it and can dig in.
- **US-2** As a developer, I can ask "what depends on this function?" and see the impacted call paths, so I understand a change's blast radius.
- **US-3** As an agent-augmented developer, my coding agent can fetch the spec for an area over MCP, so it builds against the real contract instead of guessing.
- **US-4** As a spec-driven lead, I can generate a structured spec and store a versioned copy, so I have a durable, citable contract.
- **US-5** As any user, when code changes, I can see which stored specs are now stale, so I know what to regenerate.
- **US-6** As a cost-sensitive student, I can run the entire system for free on my machine, so budget is never a blocker.
- **US-7** As a developer, I can re-index a repo repeatedly without creating duplicate graph data.
- **US-8** As an onboarding engineer, I can read a one-page summary per area of the codebase — generated, never hand-written, with `file:line` receipts — as living onboarding docs that can't silently rot.
- **US-9** As a developer, a precise symbol question routes to the code graph and a big-picture question routes to the spec/group layer, so each question hits the right source automatically.

## 7. Key scenarios (workflows)

1. **Index → Ask.** User points Spec-Atlas at a local repo or public git URL. It builds the graph, specs, and `group.md` tree, then answers questions — routed to the code-graph path for detail or the spec/group path for big-picture.
2. **Generate → Store spec.** User selects an area; Spec-Atlas generates a structured spec (purpose, inputs/outputs, dependencies, invariants, side effects, failure modes), verifies it against code, and stores a new immutable version in the Spec DB.
3. **Agent consumption.** A coding agent, mid-task, calls the MCP tools (`search`, `get_spec`, `get_group`) to ground its work and implements a change using the returned contract.
4. **Drift.** A new commit changes source under a stored spec; the drift detector marks it `stale`; only the affected subtree regenerates.
5. **Living onboarding docs.** Even before any agent use, the generated `group.md` tree is a readable, always-current map of the codebase — one page per area with `file:line` receipts — usable as onboarding documentation.

## 8. Functional requirements

Priorities: **P0** = required for v1, **P1** = important, **P2** = later/advanced. The "Feature" column maps each requirement to `specs/FEATURES.md` (roadmap to be re-phased around the four layers).

### A. Ingestion
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-A1 | Ingest a repository (any supported language) from a local path or public git URL. | P0 | F-001 |
| FR-A2 | Inventory files with path, language, content hash, and LOC. | P0 | F-001 |
| FR-A3 | Re-ingestion is idempotent: unchanged files (same hash) are skipped; no duplicate graph data. | P0 | F-001 |

### B. Code parsing & graph (L1)
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-B1 | Parse via tree-sitter into symbols (modules, classes, functions, methods) with signature, docstring, and line span. | P0 | F-002 |
| FR-B2 | Extract typed edges: `imports`, `calls`, `inherits`, `defines`. | P0 | F-003 |
| FR-B3 | Record a confidence score per edge; heuristic/dynamic-dispatch edges score below 1. | P0 | F-003 |
| FR-B4 | Persist nodes/edges and expose traversal queries: neighbors, subgraph, reachability (the detail path). | P0 | F-004 |
| FR-B5 | Each node has a stable identity `(repo, language, qualified_name, kind)`. | P0 | F-002 |

### C. Spec graph & group tree (L2–L4)
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-C1 | Cluster code into a bounded set of functional areas (target ~tens of groups) and build a `group.md` hierarchy with generated summaries. | P0 | F-005 |
| FR-C2 | Generate one spec page per area; links between areas (the spec graph) come from real edges in the code, never AI guesses. | P0 | F-005 |
| FR-C3 | Summaries/specs are cached; only the affected subtree regenerates on change. | P1 | F-005 |

### D. Embeddings & retrieval
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-D1 | Embed `group.md` summaries (primary retrieval) and specs (direct lookup) using a local (zero-cost) model by default. | P0 | F-006 |
| FR-D2 | Embedding is incremental: only changed/new owners are re-embedded. | P1 | F-006 |
| FR-D3 | Hierarchical retrieval: vector search over the `group.md` tree, then descend (group → spec → source) — not a live graph traversal, not flat chunks. | P0 | F-007 |

### E. Ask-anything (Q&A) & routing
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-E1 | Answer natural-language questions about the indexed repo. | P0 | F-008 |
| FR-E2 | Every answer includes provenance: the `{file, start_line, end_line}` spans it relied on. | P0 | F-008 |
| FR-E3 | Refuse or signal low confidence when the question is outside the indexed repo. | P1 | F-008 |
| FR-E4 | Answers distinguish certain vs. heuristic (low-confidence) relationships. | P1 | F-008 |
| FR-E5 | A query router routes detail/symbol questions to the code-graph path and big-picture/intent questions to the spec/group path. Both coexist; routing may begin heuristic and become automatic only on evaluation evidence. | P0 | F-007/F-008 |
| FR-E6 | Spec/group retrieval returns a small set of spec pages (target 3–8), not dozens of raw nodes. | P1 | F-007 |

### F. Spec generation (the "Specify" tool)
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-F1 | Generate a structured spec for an area: purpose, inputs, outputs, dependencies, invariants, side effects, failure modes. | P0 | F-010 |
| FR-F2 | The spec validates against a fixed JSON Schema. | P0 | F-010 |
| FR-F3 | Each invariant/claim carries provenance to source spans (`file:line` receipts). | P0 | F-010 |

### G. Spec store
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-G1 | Specs are stored in a database **separate** from the analysis graph. | P0 | F-011 |
| FR-G2 | Specs are per-user and versioned; a new generation creates a new immutable version (`valid_from`/`valid_to`). | P0 | F-011 |
| FR-G3 | Each spec/group page carries a fingerprint of the code it covers, so stale is visible, never silent. | P0 | F-011 |
| FR-G4 | An API exposes current and historical versions of a spec. | P0 | F-011 |

### H. Spec verification
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-H1 | A verifier checks each spec invariant/claim against code and flags unsupported ones. | P1 | F-012 |
| FR-H2 | A spec is only marked `verified` if it passes verification. | P1 | F-012 |

### I. Agent interface
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-I1 | A local MCP server exposes `search` (vector + descend), `get_group`, `get_spec`, `list_stale_specs`. | P0 | F-013 |
| FR-I2 | Tool responses include provenance so agents can cite/verify. | P0 | F-013 |
| FR-I3 | An HTTP API mirrors the core graph and spec operations for non-MCP callers. | P1 | F-004/F-011 |

### J. Drift detection
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-J1 | On a new commit, detect which specs/groups cover changed source (via fingerprints). | P1 | F-014 |
| FR-J2 | Mark affected pages `stale`; regenerate only the affected subtree. | P1 | F-014 |

### K. User interface
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-K1 | A web UI with a question box, grounded answer, clickable source citations. | P1 | F-009 |
| FR-K2 | A group-tree / spec browser to read areas as living docs. | P1 | F-009 |
| FR-K3 | A code-graph viewer to explore structure visually. | P2 | F-009 |

### L. Language coverage
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-L1 | Parse multiple languages from v1 via tree-sitter (initial set: Python + TypeScript/JS). | P0 | F-002 |
| FR-L2 | Adding a language is additive: a tree-sitter grammar + query pack implementing the same node/edge contract; nothing upstream changes. | P1 | F-015 |

### M. Evaluation
| ID | Requirement | Priority | Feature |
|---|---|---|---|
| FR-M1 | A head-to-head eval harness scores the spec/group path against a raw-node-RAG baseline on a curated question set (accuracy, context size, cost). | P1 | F-016 |
| FR-M2 | Auto-routing (FR-E5) is enabled only when eval evidence supports it. | P1 | F-016 |

## 9. Non-functional requirements (summary)

Full detail in `NFR.md`. Headlines: **$0 cost** (free tiers + local compute only); **privacy** (the DB stores structure, specs, summaries, and embeddings — never raw source); **security** (the indexing/spec pipeline only reads files and calls the model — it never executes repo code or runs commands); **performance** (targets in §4); **reliability** (idempotent re-ingest, graceful 429/timeout/cold-start handling, immutable spec versions); **grounding** (no provenance → not allowed in an answer/spec); **observability** (per-stage logs + token-usage stats); **portability** (CPU-only, runs on the dev's machine).

## 10. System overview

Full detail in `ARCHITECTURE.md`. Python/FastAPI backend with four knowledge layers — tree-sitter code graph (L1) → LLM-generated specs (L2) → spec graph (L3) → `group.md` tree (L4) — built bottom-up at index time; retrieval is top-down (vector search over L4, then descend) with a router that sends detail questions to the L1 graph. TypeScript/React frontend; PostgreSQL + pgvector for the Analysis DB and a separate Spec DB; provider-abstracted LLM (Gemini/Groq free, or local Ollama) and embeddings (local fastembed by default); a local MCP server for agent consumption.

## 11. Data and privacy

Two logical databases (both free Postgres): an **Analysis DB** (rebuildable code graph + group embeddings) and a **Spec DB** (durable, per-user, versioned specs + the spec graph), kept separate by design. Source code never leaves the user's machine and is not stored in the DB; answers read source from local disk at query time. No secrets in the repo. Public repos only in v1.

## 12. Dependencies and constraints

- **Hard constraint: zero cost.** Any paid dependency requires an accepted ADR (default: rejected).
- Free-tier services / libraries: tree-sitter (parsing), Neon (Postgres + pgvector), a free LLM tier (Gemini/Groq) or local Ollama, local fastembed embeddings, GitHub Actions for CI, optional Render/Vercel hosting. Quotas drift and must be re-verified.
- Built primarily by AI agents (Claude Code, Codex, Gemini) following the spec-driven `PLAYBOOK.md`; work is sliced into independent, additive, testable tasks.

## 13. Assumptions

- Target repos may be in multiple languages; tree-sitter provides uniform parsing, with Python + TypeScript/JS as the initial query packs.
- The user runs the system locally with the agents installed locally.
- Free-tier LLM quotas are sufficient for personal-scale indexing with caching.
- Static analysis is acceptable; perfect resolution of dynamic dispatch is not required (confidence scores communicate uncertainty), and the LLM spec layer carries the semantic load.

## 14. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM hallucination in answers/specs | Wrong guidance, lost trust | Mandatory provenance + `file:line` receipts; spec verifier; refuse-out-of-scope; head-to-head eval gates the spec path |
| Routing errs (wrong path for a question) | Worse answer | Both paths always available; heuristic routing first, automatic only on eval evidence (FR-M2) |
| Cross-language call imprecision | Missed/false edges | Confidence scores; LLM spec layer compensates; surface uncertainty |
| Free-tier quota/cold-start limits | Indexing stalls or cost appears | Local-first; local embeddings; caching; fakes in CI; local Postgres fallback |
| Graph/tree scaling on large repos | Slow/oversized index | Bounded group count; store structure not source; incremental subtree regen |
| Scope creep into "general chatbot" | Diluted product | Strict scope guard; grounded answers only |
| Multi-agent collisions during build | Rework, conflicts | "Owned files" + dependency-tracked board + HANDOFF notes |

## 15. Release plan

| Release | Contents | Phases (`FEATURES.md`) |
|---|---|---|
| **MVP** | Index a repo (Python + TS) → code graph → specs + `group.md` tree (= living onboarding docs) → one grounded, routed, cited answer → generate + store one spec → agent reads it via MCP | F-000 → F-001 → F-002 → F-003 → F-004 → F-005 → F-006 → F-007 → F-008 → F-010 → F-011 → F-013 |
| **v1** | + spec verification, drift detection, web UI / spec browser, head-to-head eval harness, additional language packs | + F-009, F-012, F-014, F-015, F-016 |
| **v1.x** | + auto-routing on eval evidence, optional free-tier deploy + observability | + remaining F-016 work |

## 16. v1 acceptance criteria (definition of done)

- [ ] Index a real ~20k-LOC repo (with at least two languages present) locally within the performance target.
- [ ] Ask-anything returns grounded, routed answers meeting the 80% citation-accuracy target on the curated set.
- [ ] The spec/group path uses materially smaller context than the raw-node baseline (measured head-to-head).
- [ ] Generate a spec that passes the grounding verifier and is stored as a version in the Spec DB, with a code fingerprint.
- [ ] The generated `group.md` tree is browsable as living onboarding docs.
- [ ] A coding agent retrieves a spec via the local MCP server and uses it in a task.
- [ ] Drift detection flags a stale page after a relevant commit; only the affected subtree regenerates.
- [ ] Total running cost is $0; CI passes offline with fake providers.

## 17. Out of scope (v1)

Runtime/dynamic analysis (and any execution of repo code), auto-applying code changes, multi-tenant SaaS / billing / org RBAC, and private-repo credential storage. (Multi-language is in scope from v1; language packs beyond the initial Python + TS/JS set are additive follow-ons.)

## 18. Open questions

1. Group/tree formation (architecture D1): directory/package skeleton vs. graph community detection vs. LLM clustering — and target group count (~tens of functional areas).
2. Initial language set beyond Python + TS/JS (e.g. add Go/Java in v1?).
3. Default hosted LLM provider for v1 — Gemini free vs. Groq free (or local Ollama as documented default).
4. Web UI in MVP or v1 (CLI-only MVP keeps the first slice smaller).
5. User identity model for the Spec DB while single-user — fixed local `user_id` or none until multi-user.

## 19. Glossary

- **Node / symbol** — a code entity (module, class, function, method) in the L1 graph.
- **Edge** — a typed relationship between nodes (imports, calls, inherits, defines).
- **Code knowledge graph (L1)** — the structural substrate from tree-sitter.
- **Spec (L2)** — a structured, schema-validated, versioned description of an area's contract, generated by the Specify tool.
- **Spec graph (L3)** — the higher-level graph linking specs via real code edges.
- **group.md tree (L4)** — the hierarchy of condensed, context-rich summaries; the vector-search entry point.
- **Routing** — choosing the code-graph path vs. the spec/group path per question.
- **Provenance / receipt** — the `{file, start_line, end_line}` spans backing a claim.
- **Fingerprint** — a hash of the source a spec/group covers; mismatch = stale.
- **Drift** — divergence between a stored spec and the current source it describes.
- **MCP** — the protocol by which coding agents call Spec-Atlas tools.
