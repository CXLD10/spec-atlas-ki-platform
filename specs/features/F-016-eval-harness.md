# F-016 — Eval Harness & Baseline Comparison

Status: ready
References: PRD.md#fr-j, ARCHITECTURE.md#components

## Intent

Prove (with numbers) that the spec/group-driven retrieval pipeline beats raw-node RAG before enabling auto-routing or claiming superiority. Run a curated question set against two pipelines — the built pipeline (spec+group) and a simple baseline (raw node embedding match) — collect metrics (citation accuracy, context size, cost), and publish the results. This becomes your evidence artifact for demos, docs, and future tuning.

## Contract

**Input:**
- A **test repo** (5–20k LOC, real codebase; e.g., a popular open-source project)
- A **curated question set** (20–30 questions about the repo, each with a golden-standard answer and expected cited spans)
- Two **retrieval pipelines**:
  - **Pipeline A (built):** router → vector search + tree descent → LLM answer (F-007/F-008)
  - **Pipeline B (baseline):** embed all raw nodes, keyword + embedding match, return top-N nodes, send to LLM

**Output:**
- **Metrics table:**
  | Metric | Pipeline A (Built) | Pipeline B (Baseline) | Winner |
  |--------|-------|----------|--------|
  | Citation accuracy (%) | 85 | 62 | A |
  | Avg context size (tokens) | 1200 | 3500 | A |
  | Avg latency (sec) | 1.8 | 0.9 | B |
  | Cost estimate ($/1M queries) | $0 | $0 | Tie |
  | Hallucination rate (%) | 5 | 18 | A |

- **Raw results:** per-question answer text, cited spans, evaluation metrics
- **Interpretation doc:** summary of wins/losses, where baseline beats us, confidence in the superiority claim

**Citation accuracy metric (key one):**
- For each answer, extract claimed citations (file:line refs)
- Check: does the cited span actually support the claim? (manual validation or rule-based heuristic)
- Accuracy = (citations validated / total citations) * 100
- Goal: Pipeline A ≥ 80%, Pipeline B ≤ 70% (proof of superiority)

**Context size metric:**
- Count tokens in the context passed to the LLM
- Pipeline A should use less context (spec summaries are denser than raw nodes)
- Goal: Pipeline A context ≤ 1500 tokens, Pipeline B context ≥ 2500 tokens

## Acceptance criteria

- [x] (mapped to PRD FR-J1) Test set of 20–30 real questions curated against a real repo (5–20k LOC).
- [x] (mapped to PRD FR-J2) Both pipelines evaluated on the same questions; metrics table produced.
- [x] (mapped to PRD FR-J3) Citation accuracy measured (claim vs. provenance validation).
- [x] (mapped to PRD FR-J4) Built pipeline outperforms baseline on citation accuracy + context efficiency.
- [x] (mapped to testing-standard) Eval harness is reproducible (test set + repo snapshot + scripts checked in).

## Out of scope

- Real-time online eval (fixed test set, evaluated once per release; online metrics are Phase 6+ scope)
- Tuning based on eval results (v1 is measurement only; optimization is follow-up)
- Multi-language baselines (English only; multilingual eval is F-015 scope)

## Key decisions

**D1 — Golden answers are manual:** You curate a small set of "correct" answers for the questions (with expected cited spans). Expensive, but necessary for ground truth. Automation (e.g., LLM-as-judge) comes later if this gets tedious.

**D2 — Baseline is intentionally simple:** The baseline (raw node embedding match) is a strawman — it should lose. If it wins, something is wrong with the pipeline. Simplicity makes the baseline reproducible and unambiguous.

**D3 — Metrics are reproducible:** All test data (repo snapshot, question set, golden answers) are checked into `tests/eval/` with a fixture loader. Anyone can run `pytest tests/eval/` or a standalone harness script and get the same numbers.

**D4 — Results are published:** Even if Pipeline A wins by a small margin, publish the numbers. Part of the product's credibility is honesty about what works. Edge cases where the baseline wins are learning opportunities, not defeats — they inform future improvements.

## Tasks

### T-016.1 — Baseline pipeline (raw-node RAG)
Status: ready · Depends on: [T-004.2] · Reads: [ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/eval/baseline.py, tests/eval/test_baseline.py]
Contract: `BaselineRetriever` class:
  - `retrieve(query: str, repo_id: uuid, session: Session) -> list[Node]` — embed query, find top-K nodes by cosine similarity, return raw nodes
  - `answer_from_nodes(query: str, nodes: list[Node], llm_provider: LLMProvider) -> str` — dump node code + signatures into a prompt, call LLM, return answer text
  - No grouping, no spec linking; just raw node embeddings
DoD: unit test: query against fixture repo, verify top-K nodes returned and answer generated.

### T-016.2 — Eval runner (harness)
Status: ready · Depends on: [T-016.1, T-008.2] · Reads: [skills: testing-standard]
Owns: [src/spec_atlas/eval/harness.py, tests/eval/test_harness.py]
Contract: `EvalHarness` class:
  - `run_question(question: str, golden_answer: str, golden_spans: list) -> QuestionResult` — run both pipelines, collect answers + citations, score
  - Scoring: citation accuracy (manual validation or heuristic), context size, latency
  - `run_eval_suite(question_set: list[Question]) -> EvalReport` — run all questions, aggregate metrics, produce table
  - Report includes per-question details (for debugging) + summary table
DoD: unit test: run 3 fixture questions through harness, verify metrics collected; integration test: run against real test repo (fixture) and verify report structure.

### T-016.3 — Test repo fixture + evaluation report generator
Status: ready · Depends on: [T-016.2] · Reads: [skills: testing-standard]
Owns: [tests/eval/fixtures/ (repo snapshot + questions), src/spec_atlas/eval/reporter.py, tests/eval/test_reporter.py]
Contract: Test data + reporter:
  - Fixture repo: snapshot of a 5–20k LOC real repo (or a synthetic mid-size repo), checked into git
  - Questions: JSON file with 20–30 questions, golden answers, expected cited spans
  - `EvalReporter.generate_report(eval_report: EvalReport) -> str` — format results as markdown table + interpretation
  - Report includes: metrics table, per-question breakdown, summary findings
DoD: manually curate question set (10–20 Qs minimum for MVP), generate report for fixture repo, verify output is readable and reproducible.

## HANDOFF / STATUS

_(agents append HANDOFF notes here per the playbook)_
