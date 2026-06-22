# HANDOFFS.md — Developer Handoff Notes

**Purpose**: Log of handoff notes from each completed task (copied from #handoff channel or PR descriptions).

Format: Task → Developer → Handoff Summary

---

## Phase 0: Stabilize the Seam

### Task: Backend App Bootstrap & Router Mounting

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: Frontend Route Wiring to API Contract

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: End-to-End Ingest + Ask Flow (Gate G0)

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

## Phase 1: Multi-Source Ingestion

### Task: SourceUnit Abstraction + PDF Adapter

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: Frontend Source Manager UI

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: Dual-Locator Citations (Code + PDF)

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

## Phase 2: Graph + Specify

### Task: Spec Generation (LLM) + Persistence

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: 3-Layer Graph API & Rendering

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: Specify Tool UX

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

## Phase 3: Breadth + Persistence

### Task: Excel / Markdown Adapters

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: Conversation Memory Persistence

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: (Stretch) MCP Server Integration

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

## Phase 4: Harden + Record

### Task: Golden Demo Setup & Rehearsal

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

### Task: Recording & Deliverables

**Assigned to**: [TBD]  
**Status**: Not started  
**Handoff Note**:
```
(To be filled when task complete)

---

## Handoff Template

When a task is complete, add a handoff note in this format:

```
### Task: [Name]

**Assigned to**: [Developer]  
**Status**: Complete  
**Handoff Note**:

**Summary**: One-sentence summary of what was built.

**Key Implementation**:
- File/module: Line range or key function
- File/module: Line range or key function

**Tests Added**:
- Test file: pytest path (e.g., `tests/test_*.py::test_*`)

**Known Limitations**:
- [If any; else: None]

**Next Task**:
- Task X is unblocked by this work
- Task Y depends on [specific file/API]

**Testing Done**:
- Manual: [what was tested]
- Automated: [tests added/passing]

**Code Review**:
- PR #NNN: [link]
```

## Success Criteria for Handoff

Before handing off, ensure:
- [ ] Code compiles/imports cleanly
- [ ] All tests pass (offline + online if applicable)
- [ ] No merge conflicts
- [ ] PR reviewed and approved
- [ ] Handoff note summarizes next team member's context
- [ ] All citations & provenance are correct

---

## How to Use This File

1. **Incoming task**: Read the prior task's handoff note
2. **Completing task**: Write a new handoff note (copy from PR description or #handoff)
3. **Moving to next phase**: Verify Gate is met; confirm all handoffs are filled

---

## Last Updated

**2026-06-22** — Template created; to be populated during sprint.
