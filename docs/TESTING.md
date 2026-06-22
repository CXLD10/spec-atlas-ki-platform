# TESTING.md — Definition of Done & Testing Strategy

**Version**: 2.0  
**Phase Scope**: 0–4 (20-hour sprint)  
**Purpose**: Clarify what "tested" and "complete" mean for each task

---

## Definition of Done (ALL TASKS)

A task is done when ALL of the following are true:

### Code Quality
- [ ] Code passes linting (black, flake8, mypy for backend; eslint, TypeScript for frontend)
- [ ] No secrets committed (checked via `detect-secrets`)
- [ ] Imports are organized (sorted, no unused)
- [ ] Comments are minimal and explain WHY (not WHAT)

### Testing
- [ ] Unit tests written for new functions/components
- [ ] Tests pass OFFLINE (`LLM_PROVIDER=fake EMBED_PROVIDER=fake pytest`)
- [ ] Tests pass ONLINE (if applicable; with real LLM/embeddings)
- [ ] Integration tests added for new workflows
- [ ] Coverage not decreased (target: ≥80% for new code)

### Documentation
- [ ] Function/class docstrings updated (short, explain purpose)
- [ ] API endpoints documented in API_CONTRACT.md
- [ ] New modules linked from specs/features/F-*.md
- [ ] Feature story marked "in_progress" → "done" in tasks/BOARD.md
- [ ] Handoff note written in docs/HANDOFFS.md

### Provenance & Spec-Driven
- [ ] Citations are correct (file, line, page, bbox)
- [ ] No uncited LLM-generated claims
- [ ] Offline tests validate provenance
- [ ] Code follows CLAUDE.md rules (no vendor SDK, LLMProvider abstraction)
- [ ] No paid dependencies added without ADR

### Git & PR
- [ ] Feature branch merged to main via PR
- [ ] PR reviewed by another engineer
- [ ] No merge conflicts
- [ ] Commit messages follow spec-driven style ("feat:", "fix:", "refactor:")
- [ ] All CI checks pass

---

## Testing Strategy by Phase

### Phase 0: Stabilize the Seam

**What to test**:
- Backend app startup: no import errors, all routers mounted
- Frontend routes load: no 404s, UI renders
- End-to-end ingest + ask: small test project (e.g., 5 Python files, 1 PDF)

**Test Command**:
```bash
# Offline (fake LLM/embeddings)
export LLM_PROVIDER=fake EMBED_PROVIDER=fake
pytest tests/integration/test_phase0_e2e.py -v

# Online (optional; validates real LLM)
export OPENAI_API_KEY=$(cat .env.local | grep OPENAI_API_KEY | cut -d= -f2)
pytest tests/integration/test_phase0_e2e.py::test_real_llm -v
```

**Success Criteria**:
- ✓ Backend boots in <5s
- ✓ Frontend loads without 404
- ✓ Ingest completes in <30s on test project
- ✓ Ask returns answer with ≥1 citation

---

### Phase 1: Multi-Source Ingestion

**What to test**:
- SourceUnit adapter registration
- PDF extraction (text + metadata)
- Mixed-source embedding
- Ask returns both code + PDF citations

**Test Command**:
```bash
export LLM_PROVIDER=fake EMBED_PROVIDER=fake
pytest tests/phase1/ -v

# Specific test
pytest tests/phase1/test_pdf_adapter.py::test_pdf_citation_bbox -v
```

**Success Criteria**:
- ✓ PDF adapter extracts text + preserves page/bbox
- ✓ SourceUnit normalizes code + PDF metadata
- ✓ Ask returns mixed citations (code + PDF)
- ✓ Frontend renders both citation types

---

### Phase 2: Graph + Specify

**What to test**:
- Spec generation (LLM): code → markdown
- Spec persistence (store + version)
- 3-layer graph API
- L3 clustering
- Frontend graph renderer

**Test Command**:
```bash
export LLM_PROVIDER=fake EMBED_PROVIDER=fake
pytest tests/phase2/ -v

# Graph rendering (frontend)
npm test -- tests/phase2/Graph.test.ts --watch
```

**Success Criteria**:
- ✓ Spec generated with inline citations
- ✓ Spec stored + retrieved; version incremented
- ✓ Graph API returns L1, L2, L3 nodes + edges
- ✓ Frontend renders graph (zoom, pan, click-through)
- ✓ Click node → ask workflow works

---

### Phase 3: Breadth + Persistence

**What to test**:
- Excel/Markdown adapter (if in scope)
- Conversation memory schema + retrieval
- Memory facts correctly extracted + reused
- (Stretch) MCP server endpoints

**Test Command**:
```bash
export LLM_PROVIDER=fake EMBED_PROVIDER=fake
pytest tests/phase3/ -v

# Memory persistence
pytest tests/phase3/test_conversation_memory.py -v

# (Stretch) MCP server
curl http://localhost:9001/mcp/ask -d '{"project_id":"proj_test","query":"..."}'
```

**Success Criteria**:
- ✓ Excel/Markdown files ingest + embed
- ✓ Memory facts persist across sessions
- ✓ Ask in session 2 retrieves + uses memory facts
- ✓ Frontend shows memory in conversation sidebar

---

### Phase 4: Harden + Record

**What to test**:
- Golden demo project: ingest → ask → answer (no timeouts)
- All 5 phases working together
- Recording/deliverables (video, deck, diagrams)

**Test Command**:
```bash
# Demo dry run
bash scripts/demo-golden.sh

# Validate output
ls -la output/
  - architecture-diagram.png
  - demo-video.mp4
  - demo-deck.pptx
  - README-demo.md
```

**Success Criteria**:
- ✓ Demo runs end-to-end without human intervention (or with scripted steps)
- ✓ All answers correctly cited
- ✓ Video/diagram/deck ready for stakeholders

---

## Offline Testing (CRITICAL)

**All tests must pass OFFLINE:**

```bash
export LLM_PROVIDER=fake
export EMBED_PROVIDER=fake

# Full test suite
pytest tests/

# Must pass before committing
```

**Why**:
- Ensures zero cost (no API calls in CI)
- Validates provenance independently (fake LLM uses mock data)
- Fast feedback loop (no network latency)
- Reproducible (same results every time)

**How it works**:
- `LLMProvider` returns fake responses (e.g., mock specs)
- `EmbeddingProvider` returns random vectors
- Citations are pre-populated in mock data
- Tests validate that output + citations match

---

## Testing Levels

### Unit Tests
- **What**: Single function (e.g., parse symbol, embed vector)
- **Where**: `tests/unit/`
- **Example**: `test_parse_python_class()`, `test_normalize_source_unit()`
- **Coverage Target**: ≥85%

### Integration Tests
- **What**: Multiple modules working together (e.g., ingest → graph → ask)
- **Where**: `tests/integration/`
- **Example**: `test_end_to_end_ingest()`, `test_pdf_to_spec_flow()`
- **Coverage Target**: ≥70%

### Feature Tests
- **What**: Full feature end-to-end (user-facing workflow)
- **Where**: `tests/features/`
- **Example**: `test_phase1_multi_source_ask()`
- **Coverage Target**: ≥50%

### Manual/E2E Tests
- **What**: Browser-based flow (only if frontend changes)
- **Where**: `docs/TESTING.md` (this file) + test scripts
- **Example**: Run golden demo, verify answer appears
- **Frequency**: Before PR merge, before each phase gate

---

## Provenance Validation (Offline)

Every generated spec/answer must be validated:

```python
def test_spec_provenance():
    """Spec must cite code lines."""
    spec = generate_spec(node_id="node_abc")
    
    # Extract citations
    citations = parse_citations(spec.content)
    
    # Validate each citation
    for cite in citations:
        assert os.path.exists(cite.file), f"File not found: {cite.file}"
        assert cite.start_line < cite.end_line
        assert 1 <= cite.start_line <= max_lines(cite.file)
```

**Rule**: No spec/answer should be generated without citations.

---

## Checklist Before Gate

Each gate (G0–G4) requires:

```
Gate G0: Stabilize Seam
- [ ] Backend app starts, all routers mount
- [ ] Frontend routes load (no 404s)
- [ ] End-to-end ingest + ask works (with fake LLM)
- [ ] All tests pass offline
- [ ] Handoff note written in docs/HANDOFFS.md

Gate G1: Multi-Source Ingestion
- [ ] SourceUnit abstraction complete
- [ ] PDF adapter working
- [ ] Mixed citations in ask responses
- [ ] Frontend source manager UI
- [ ] All tests pass offline

Gate G2: Graph + Specify
- [ ] Specs generated + persisted
- [ ] 3-layer graph renders
- [ ] L3 clustering works
- [ ] Click-through workflow (graph → ask)
- [ ] All tests pass offline

Gate G3: Breadth + Persistence
- [ ] ≥3 source adapters (PDF, Markdown, Excel)
- [ ] Memory persistence working
- [ ] Memory retrieved in next session
- [ ] (Stretch) MCP server running
- [ ] All tests pass offline

Gate G4: Harden + Record
- [ ] Demo runs flawlessly (3+ rehearsals)
- [ ] All deliverables exported
- [ ] Video + deck ready
- [ ] All tests pass (offline + online)
```

---

## Running Tests

### Quick Test (before commit)
```bash
# Lint + offline tests
black --check src/
flake8 src/
mypy src/
pytest tests/ -x  # exit on first failure
```

### Full Test (before PR)
```bash
# Build Docker image
docker build -t spec-atlas:test .

# Run full suite inside container
docker run --rm -e LLM_PROVIDER=fake -e EMBED_PROVIDER=fake \
  spec-atlas:test \
  pytest tests/ --cov=src --cov-report=html
```

### CI/CD (on push)
```yaml
# .github/workflows/test.yml
- run: pytest tests/ -v --cov
- run: black --check src/
- run: flake8 src/
- run: mypy src/
```

---

## Known Test Gaps

As of Phase 0:

| Gap | Why | Plan |
|-----|-----|------|
| Frontend E2E | Hard to automate without browser | Phase 2: add Playwright/Cypress tests |
| Performance | No baseline yet | Phase 4: benchmark ingest + ask latency |
| Security | No auth tested | Phase 4: add auth + RBAC tests |

---

## Last Updated

**2026-06-22** — Phase 0–4 testing strategy; Definition of Done; offline-fakes validated.
