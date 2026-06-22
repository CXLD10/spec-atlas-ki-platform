# DECISIONS.md — Architecture Decision Records (20-Hour Sprint)

**Index of ADRs** for Phases 0–4 of the Spec-Atlas sprint (2026-06-22 onward).

Each decision should be recorded in `docs/decisions/ADR-NNNN-<slug>.md` and linked below.

---

## Foundation Decisions (Phase 0)

| ADR | Title | Status | Phase |
|-----|-------|--------|-------|
| [ADR-0001](decisions/ADR-0001-v1-key-decisions.md) | v1 Key Decisions (Legacy) | Superseded | 0 |
| [ADR-0002](decisions/ADR-0002-toolchain-and-offline-defaults.md) | Toolchain & Offline Defaults | Active | 0 |
| [ADR-0003](decisions/ADR-0003-phase0-recovery.md) | Phase 0 Recovery | Active | 0 |

---

## Phase 0: Stabilize Seam

**Decision Topics**:
- [ ] Which LLM provider to default (free/local for Phase 0–3)? → ADR-0002
- [ ] How to handle project_id scoping? → TBD
- [ ] Frontend route mapping to API_CONTRACT? → TBD (doc in docs/frontend/architecture/API-CONTRACT.md)

---

## Phase 1: Multi-Source Ingestion

**Decision Topics**:
- [ ] SourceUnit abstraction design → *To be written*
- [ ] PDF citation format (page + bbox) → *To be written*
- [ ] Mixed-source embedding strategy → *To be written*
- [ ] How to normalize code + PDF metadata? → *To be written*

**Future ADRs**:
- ADR-0004: SourceUnit Abstraction Design
- ADR-0005: PDF Citation & Bbox Preservation
- ADR-0006: Multi-Source Embedding Strategy

---

## Phase 2: Graph + Specify

**Decision Topics**:
- [ ] L2 (spec) node creation & lifecycle → *To be written*
- [ ] Spec versioning & update strategy → *To be written*
- [ ] L3 clustering algorithm (manual vs LLM-driven) → *To be written*
- [ ] Graph rendering (D3.js vs Cytoscape) → *To be written*

**Future ADRs**:
- ADR-0007: Spec Persistence & Versioning
- ADR-0008: L3 Clustering Strategy
- ADR-0009: Graph Visualization Library Choice

---

## Phase 3: Breadth + Persistence

**Decision Topics**:
- [ ] Conversation memory schema & retrieval → *To be written*
- [ ] Excel adapter design → *To be written*
- [ ] Markdown adapter design → *To be written*
- [ ] Jira adapter (if in scope) → *To be written*
- [ ] MCP server architecture (if stretch) → *To be written*

**Future ADRs**:
- ADR-0010: Conversation Memory Persistence
- ADR-0011: Adapter Registry Pattern
- ADR-0012: MCP Server Integration (Stretch)

---

## Phase 4: Harden + Record

**Decision Topics**:
- [ ] Golden demo project selection → *To be written*
- [ ] Recording/demo infrastructure → *To be written*
- [ ] Observability & monitoring for demo → *To be written*

**Future ADRs**:
- ADR-0013: Demo Setup & Infrastructure

---

## Cross-Cutting Decisions

| Topic | Decision | ADR | Status |
|-------|----------|-----|--------|
| **LLM Provider** | Default free/local; offline tests with `fake` | ADR-0002 | Active |
| **Offline Testing** | All tests pass with `LLM_PROVIDER=fake EMBED_PROVIDER=fake` | ADR-0002 | Active |
| **Provenance** | Every claim must cite source (file, line, page, bbox) | ADR-0001 | Active |
| **API Stability** | No breaking changes mid-sprint; versioning in API_CONTRACT.md | TBD | Pending |
| **No Vendor SDK** | Go through LLMProvider/EmbeddingProvider abstraction | ADR-0002 | Active |

---

## How to Add a Decision

1. **Discuss** the issue (why does it matter? what are the options?)
2. **Document** in `docs/decisions/ADR-NNNN-<slug>.md` (use template below)
3. **Link** to this index with status (Pending → Active → Superseded)
4. **Communicate** to team (PR, Slack #decisions)

### ADR Template

```markdown
# ADR-NNNN: <Title>

**Date**: YYYY-MM-DD  
**Status**: Proposed | Accepted | Superseded  
**Relevant Phase(s)**: 0, 1, 2, ...  

## Problem

What's the question or trade-off?

## Options Considered

1. **Option A**: ... (pros: ..., cons: ...)
2. **Option B**: ... (pros: ..., cons: ...)
3. **Option C**: ... (pros: ..., cons: ...)

## Decision

We chose **Option X** because:
- Fits project constraints (offline, no paid deps)
- Aligns with CLAUDE.md (spec-driven, zero cost)
- Unblocks Phase N

## Consequences

### Positive
- ...
- ...

### Negative
- ...
- ...

## Implementation Notes

How do we enforce/test this decision?

## References

- Slack thread: (link)
- Related ADRs: ADR-000X
- Code location: src/...
```

---

## Decision Lifecycle

```
Pending → Proposed (in PR) → Accepted (merged) → Active (in use) → Superseded (replaced)
```

All decisions must pass:
1. **Technical review** (correctness, feasibility)
2. **Spec alignment** (does it fit CLAUDE.md + SCOPE.md constraints?)
3. **Stakeholder approval** (PM, lead engineer)

---

## Superseded Decisions

- **ADR-0001** (v1 Key Decisions): Preserved for history; architecture evolved in v2 (this sprint)

---

## Key Principle

> Every decision should answer the question: **"Why this way, not that way?"**
> 
> Decisions document the trade-offs and constraints at a moment in time.
> When circumstances change, update or supersede the decision.

---

## Last Updated

**2026-06-22** — Sprint kickoff; index created with foundation ADRs.
