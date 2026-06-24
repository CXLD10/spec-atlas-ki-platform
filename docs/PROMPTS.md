# PROMPTS.md — LLM Instruction Templates

**Version**: 2.0  
**Purpose**: Canonical prompts for spec generation, answering, and agent integration  
**Status**: Living; updated as phases progress

---

## Overview

Spec-Atlas uses LLMs for:
1. **Spec Generation**: Turn code/docs into structured specs (Phase 2)
2. **Answer Generation**: Ground answers in retrieved specs/code (Phase 0+)
3. **Memory Synthesis**: Extract durable facts from conversations (Phase 3)
4. **Graph Interpretation**: Suggest relationships and clusters (Phase 2)

All prompts follow:
- **Provenance principle**: Every claim must cite source (file, line, page, bbox)
- **Offline-safe**: Use `LLMProvider` abstraction; default to free/local (e.g., Ollama, OpenAI-fake)
- **Deterministic**: No randomness in citations; consistent across runs

---

## Spec Generation (Phase 2)

### PROMPT: Generate Module Spec

**Input**:
- Code snippet (file + lines)
- Related symbols/imports
- Conversation context (if any)

**Instruction**:
```
You are a senior code architect writing a structured specification for a module/class/function.

CODE SNIPPET:
{code_snippet}

CONTEXT:
- Module: {module_name}
- Kind: {kind} (module/class/function/type)
- Related imports: {related_imports}
- Related calls: {related_calls}

TASK:
Write a markdown spec that answers:
1. What does this do? (purpose, 1–2 sentences)
2. Key responsibilities (bullet list)
3. Input/output contracts (if applicable)
4. Dependencies (other modules/classes it relies on)
5. Known limitations or TODO items (if visible in code)

FORMAT:
Use markdown H2/H3 headers. Keep each section concise.
Every claim must cite line numbers: (file:start–end)

TONE:
Professional, precise, actionable. Assume reader is a developer.

SPEC:
```

**Output**: Markdown spec with inline citations

---

### PROMPT: Cluster Specs into Groups (L3)

**Input**:
- List of spec_id + titles
- Graph edges (what relates to what)

**Instruction**:
```
You are clustering related specs into semantic groups.

SPECS TO CLUSTER:
{specs_list}

GRAPH EDGES:
{edges}

TASK:
Identify 3–7 thematic clusters. For each:
- Name: short identifier (e.g., "Core Graph Builder", "RAG Pipeline")
- Description: what unites these specs
- Member spec_ids: which specs belong

RATIONALE:
Explain why these belong together.

CLUSTERS:
```

**Output**: Cluster JSON:
```json
{
  "clusters": [
    {
      "cluster_id": "grp_graph",
      "name": "Graph Construction",
      "description": "Specs for L1 graph parsing and edge extraction",
      "member_specs": ["spec_001", "spec_003", "spec_005"]
    }
  ]
}
```

---

## Answer Generation (Phase 0+)

### PROMPT: Ground Answer in Specs/Code

**Input**:
- User query
- Retrieved specs (top-K by relevance)
- Retrieved code snippets
- Conversation memory (Phase 3+)

**Instruction**:
```
You are answering a developer question about a codebase.

QUERY:
{query}

RETRIEVED SPECS:
{specs}

RETRIEVED CODE:
{code_snippets}

MEMORY:
{memory_facts}

TASK:
Generate a conversational answer that:
1. Directly addresses the query
2. Grounds every claim in specs/code via citations
3. Acknowledges memory context if relevant
4. Suggests next steps or related questions

CITATION FORMAT:
- For code: [snippet](file:start–end)
- For PDF: [excerpt](source: pdf_name, page N)
- For memory: [fact] (recalled from prior session)

TONE:
Helpful, conversational, but precise. Assume intermediate developer knowledge.

ANSWER:
```

**Output**: Markdown answer with citations

---

### PROMPT: Extract Memory Facts

**Input**:
- Ask query + answer + citations
- Prior conversation context

**Instruction**:
```
Extract 2–5 durable facts from this Q&A that should persist to the next session.

QUERY:
{query}

ANSWER:
{answer}

CITATIONS:
{citations}

FACTS:
Each fact should be:
- Specific and verifiable (not vague)
- Sourced (which file/page/spec?)
- Relevant to future asks about this project

EXAMPLE:
- "Parser module in parser.py:10–50 extracts symbols for Python files" (source: code parser.py)
- "Architecture diagram on architecture.pdf:15 shows 3-layer RAG flow" (source: PDF)

OUTPUT JSON:
{
  "facts": [
    {
      "fact": "...",
      "sources": ["code", "pdf", "memory"],
      "relevance": 0.95
    }
  ]
}
```

**Output**: JSON facts for storage

---

## Retrieval Routing (Phase 1+)

### PROMPT: Classify Query as Spec-Based vs Code-Based

**Input**:
- User query
- Project metadata (sources available)

**Instruction**:
```
Classify this query to route to the right retrieval strategy.

QUERY:
{query}

PROJECT SOURCES:
- Code: {code_languages}
- Docs: {doc_types}
- Other: {other_sources}

TASK:
Decide: Does this query need:
A) Specs + architectural docs (high-level design)?
B) Code snippets (implementation details)?
C) Both?

ROUTING:
Return one of: "spec", "code", "mixed"

EXPLANATION:
Briefly explain why.

JSON:
{
  "routing": "spec|code|mixed",
  "reason": "..."
}
```

**Output**: Routing decision (used in retrieval.py)

---

## Graph Interpretation (Phase 2)

### PROMPT: Suggest Graph Edges & Relationships

**Input**:
- L1 code graph (nodes + existing edges)
- Retrieved specs

**Instruction**:
```
Analyze the code graph and suggest semantic relationships.

NODES:
{nodes}

EXISTING EDGES:
{edges}

SPECS:
{specs}

TASK:
Identify 2–5 missing or implicit relationships:
1. Semantic similarity (should these be in same cluster?)
2. Control flow (does A invoke B indirectly?)
3. Spec correlation (do A's spec relate to B's spec?)

SUGGESTION:
For each relationship:
- Source & target nodes
- Edge kind: "clusters", "correlates", "controls"
- Confidence: 0.0–1.0
- Rationale: why this matters

JSON:
{
  "suggested_edges": [
    {
      "source_id": "...",
      "target_id": "...",
      "kind": "clusters",
      "confidence": 0.87,
      "rationale": "Both handle embedding logic"
    }
  ]
}
```

**Output**: Suggested edges for graph enrichment

---

## Deployment & Security (Phase 4)

### PROMPT: Generate Security & Deployment Checklist

**Input**:
- Project metadata (sources, data sensitivity)
- Deployment target (local, cloud, restricted)

**Instruction**:
```
Generate a security & deployment checklist for this Spec-Atlas deployment.

PROJECT:
{project_metadata}

DEPLOYMENT TARGET:
{target}

CONSIDERATIONS:
- Data sensitivity (PII, secrets, proprietary code?)
- Access control (who can ask questions?)
- API rate limits & logging
- Prompt injection risks (user queries as part of prompt?)

CHECKLIST:
For each consideration, provide 1–2 actionable items.

MARKDOWN CHECKLIST:
- [ ] ...
- [ ] ...
```

**Output**: Markdown checklist for deployment review

---

## Implementation Notes

### Usage via LLMProvider Abstraction

```python
from spec_atlas.llm import LLMProvider

llm = LLMProvider.get()  # reads LLM_PROVIDER env var

# Spec generation
spec = llm.generate(
    template="PROMPT_SPEC_GENERATION",
    context={
        "code_snippet": "...",
        "module_name": "parser",
        "kind": "module"
    }
)

# Answer with citations
answer = llm.generate(
    template="PROMPT_GROUND_ANSWER",
    context={
        "query": "How does ingest work?",
        "specs": retrieved_specs,
        "code_snippets": retrieved_code
    }
)
```

### Offline Testing (TESTS MUST PASS)

```bash
export LLM_PROVIDER=fake
export EMBED_PROVIDER=fake

pytest tests/  # all tests must pass offline
```

---

## Provenance Validation

Every generated spec/answer is validated:

```python
def validate_provenance(output: str, citations: List[Citation]) -> bool:
    """Ensure all claims are cited."""
    # 1. Extract claims (sentences not in code/specs)
    # 2. Verify citations exist in codebase
    # 3. Reject output if uncited claims found
    pass
```

---

## Updating Prompts

Prompts are living documents. When:
1. A prompt consistently fails or produces poor specs
2. A new phase requires new retrieval logic
3. A user reports citation inaccuracies

→ Create an ADR in `docs/decisions/` and update this file.

---

## Reference

- See `specs/features/F-010-specify.md` for spec generation implementation
- See `specs/features/F-007-retrieval.md` for retrieval routing
- See `specs/features/F-008-answerer.md` for answer generation
- See `docs/decisions/` for ADRs on LLM provider strategy
