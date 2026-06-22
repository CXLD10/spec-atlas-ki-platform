# F-008 — Ask-anything answerer (grounded + provenance)

Status: ready
References: ARCHITECTURE.md#components, DATA-MODEL.md#spec-db, PRD.md#fr-f, INTEGRATIONS.md#3-llm-provider

## Intent

The final layer: take a user question, retrieve grounded context (via F-007), call the LLM with that context, and produce a grounded, cited answer. Every claim in the answer is tied to source code via provenance (`{file, start_line, end_line}`). This is the user-facing query interface.

## Contract

**Input:**
- User query string
- Retrieved context from F-007 (matched groups, specs, source spans)
- LLM provider

**Output:**
- An answer object:
  - `text`: the answer text (human-readable paragraph or list)
  - `provenance`: list of {file, start_line, end_line} receipts grounding each claim
  - `confidence`: 0–1 (how much of the answer is grounded vs. synthesized)
  - `strategy_used`: "vector_search" or "graph_query" (from router)

**Answer generation flow:**
1. Route the query (F-007 router)
2. Retrieve context (F-007 search + descent)
3. Assemble a prompt: question + context + request for grounded answer
4. Call LLM with the prompt
5. Extract claims from the answer
6. Map claims to source spans (provenance extraction)
7. Return answer + provenance

**Prompt structure (v1):**
```
You are a code-understanding assistant. A user has asked a question about a codebase.

Question: <user_query>

Retrieved context:
- Group summary: <group.md>
- Relevant specs: <list of spec purposes>
- Source spans: <file:line references>

Answer the question based on the context. If you don't know, say "I don't know" rather than guess.
Every claim must be grounded in the provided context or source code.
Include file:line receipts for each claim.

Output format:
{
  "answer": "...",
  "claims": [
    {"claim": "...", "source": "file:line"},
    ...
  ]
}
```

**Provenance extraction:**
- Parse the LLM's response (JSON claims)
- For each claim, extract the source reference (file:line)
- Validate that the span exists in the retrieved context
- If validation fails, mark claim confidence < 1.0 or omit it

**Idempotency:**
- Same question + same retrieved context → likely similar answer (LLM temp affects this)
- Provenance is deterministic (map claims → spans)

## Acceptance criteria

- [x] (mapped to PRD FR-F1) Generate an answer to a user question using retrieved context.
- [x] (mapped to PRD FR-F2) Answer is grounded: every claim has provenance {file, start_line, end_line}.
- [x] (mapped to PRD FR-F3) Route question correctly (big-picture → vector search, detail → graph query).
- [x] (mapped to PRD FR-F4) Confidence score reflects how well-grounded the answer is.
- [x] (mapped to NFR.md cost) Use configured LLM (free Gemini default; no cost).
- [x] (mapped to testing-standard) Unit tests: generate answers for fixture questions, verify provenance is present.

## Out of scope

- Answer ranking / re-ranking (single answer per question for v1)
- Interactive refinement (single-shot answer; iteration is F-016)
- Citation formatting (file:line refs; pretty HTML is UI concern, F-009)
- Answer caching (F-017 later)

## Tasks

### T-008.1 — Prompt engineering + LLM call
Status: ready · Depends on: [T-007.3] · Reads: [INTEGRATIONS.md#3-llm-provider, skills: testing-standard]
Owns: [src/spec_atlas/answer/engine.py, tests/answer/test_engine.py]
Contract: `AnswerEngine` class:
  - `answer(query: str, context: Context, llm_provider: LLMProvider) -> Answer` — assemble prompt, call LLM, parse response, return Answer.
  - Prompt: question + group summary + specs + source spans + request for grounded answer
  - LLM call: use `llm_provider.complete(messages)` with temp=0.2 (lower temp for factuality)
  - Parse response: expect JSON with `{answer, claims: [{claim, source}, ...]}` fields
  - Return Answer: text + claims (raw from LLM, not yet validated)
DoD: unit test: call engine with fixture question + context, verify answer is non-empty, verify claims are present.

### T-008.2 — Provenance extraction + validation
Status: ready · Depends on: [T-008.1] · Reads: [skills: testing-standard]
Owns: [src/spec_atlas/answer/provenance.py, tests/answer/test_provenance.py]
Contract: `AnswerProvenanceExtractor` class:
  - `extract_and_validate(answer: str, claims: list, context: Context) -> (str, list[Provenance], float)` — parse claims, validate against context, return cleaned answer + valid provenance + confidence.
  - Provenance validation: for each claim's source (file:line), check if it exists in the retrieved source_spans
  - If validation fails: mark as ungrounded (confidence 0.7); include it but flag it
  - Confidence: (count of validated claims) / (total claims), capped at 1.0
  - Return: (cleaned_answer_text, validated_provenance_list, confidence_score)
DoD: unit test: extract provenance from fixture answers + context, verify valid spans are kept, verify invalid ones are flagged, verify confidence score is calculated correctly.

## HANDOFF / STATUS

### T-008.1 HANDOFF (2026-06-19, claude)
**Delivered:** `AnswerEngine` class in src/spec_atlas/answer/engine.py.
- `answer(query, context, llm_provider)` → Answer with text, claims, strategy_used
- Assembles prompt with query, group summary, specs, source spans
- Calls LLM to generate JSON response
- Parses response to extract Answer object with Claim list
- Handles dict/string LLM responses

Dataclasses: Claim (claim text + source), Answer (text + claims + strategy).

Tests: 9 unit tests covering basic generation, specs/spans inclusion, response formats, multiple claims, malformed claims. All passing.

### T-008.2 HANDOFF (2026-06-19, claude)
**Delivered:** `AnswerProvenanceExtractor` class in src/spec_atlas/answer/provenance.py.
- `extract_and_validate(answer, context)` → (text, validated_provenance_list, confidence)
- Matches claim sources (file:line) against context source_spans
- Grounded claims: confidence 1.0; ungrounded: 0.7
- Overall confidence = grounded_count / total_claims
- Handles malformed/empty/whitespace sources gracefully

Dataclass: Provenance (file, start_line, end_line, confidence).

Tests: 9 unit tests covering grounded/ungrounded claims, multiple claims, confidence calculation, malformed sources, partial path matching. All passing.

**Status:** ✓ Phases 1-4 complete. 275 tests passing, zero cost. Answerer pipeline end-to-end working: retrieve context → generate answer → validate provenance → return grounded answer with confidence. Commit 94d7a46.

**Next:** Phase 5 (verifier, drift detection, evaluation) or answer API endpoint integration (F-009).
