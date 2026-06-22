# F-010 — Specify engine (LLM spec generation, L2)

Status: ready
References: ARCHITECTURE.md#components, DATA-MODEL.md#spec-db, PRD.md#fr-f, INTEGRATIONS.md#3-llm-provider

## Intent

The Specify engine reads a region of the L1 code graph (a focal node + its neighbors) and uses the LLM to generate a structured, schema-validated spec (purpose, inputs/outputs, dependencies, invariants, side effects, failure modes). This is where static structure is transformed into semantic understanding. Specs are the bridge between raw code and the higher-level reasoning layers.

Every field in a spec must carry provenance: the source spans (`file:start_line:end_line`) that justify the claim. This grounds the spec in reality and enables the verifier (F-012) to check it later.

## Contract

**Input:**
- A focal node ID (a function, class, or module) from the L1 graph.
- The focal node's details: qualified_name, signature, docstring, file/line span.
- The focal node's neighbors (imports, calls, inherits, defines) — up to ~20 nodes to stay within LLM context budgets.
- Optional: a hint string (e.g., "this is an auth system") for guided spec generation (v1 ignores hints; future work).

**Output:**
- A structured `Spec` object with schema (validated by JSON Schema):
  ```json
  {
    "purpose": "string",
    "inputs": [{"name": "string", "type": "string", "description": "string"}],
    "outputs": [{"name": "string", "type": "string", "description": "string"}],
    "dependencies": ["component_ref", ...],
    "invariants": ["string with claim", ...],
    "side_effects": ["string", ...],
    "failure_modes": ["string", ...]
  }
  ```
- Provenance: each field is paired with a list of `{file, start_line, end_line}` spans that justify it.
- Status: `"draft"` (generated, not yet verified by F-012).

**LLM call:**
- Prompt: introduce the focal node (name, signature, docstring), show the relevant subgraph (neighbor nodes, imports, calls), ask the LLM to fill the schema.
- Model: `LLMProvider` (defaulting to Gemini free; can be overridden by config).
- Retry: use the provider's built-in retry/backoff (INTEGRATIONS.md#3, F-000 LLMProvider contract).
- Response validation: parse the LLM's JSON response, validate against the schema, raise if invalid.

**Idempotency:**
- Re-generating a spec for the same focal node at the same commit should yield identical or very similar output (fake provider is deterministic; real provider may vary due to temperature).
- The Spec DB (F-011) handles versioning; F-010 just generates.

## Acceptance criteria

- [x] (mapped to PRD FR-F1) Generate a structured spec (purpose, inputs, outputs, dependencies, invariants, side effects, failure modes) from an L1 node + subgraph.
- [x] (mapped to PRD FR-F2) Validate the spec against a fixed JSON Schema; raise if invalid.
- [x] (mapped to PRD FR-F3) Carry provenance for each field (file, start_line, end_line).
- [x] (mapped to NFR.md cost) No cost: uses the configured LLM provider (fake offline, or free Gemini).
- [x] (mapped to testing-standard) Contract tests: generate a spec for a focal function via the fake LLM provider (with a canned response); verify the schema is valid and provenance is attached.

## Out of scope

- Iterative refinement (asking the LLM for clarifications); specs are single-pass.
- Multi-modal specs (images, external links); text only.
- Automatic spec verification (F-012 does that separately).
- Caching spec results (F-011 handles versioning and deduplication; F-010 is stateless).

## Tasks

### T-010.1 — JSON Schema for specs + validation
Status: ready · Depends on: [F-000 (all done)] · Reads: [DATA-MODEL.md#spec-db, PRD.md#fr-f2, skills: testing-standard]
Owns: [src/spec_atlas/specify/schema.py, tests/specify/test_schema.py]
Contract: `SpecSchema` module:
  - Defines a JSON Schema (dict) for a spec: required/optional fields, types, constraints.
  - `validate_spec(spec_obj: dict) -> dict` — validate `spec_obj` against the schema; raise `ValidationError` if invalid; return the valid spec.
  - Include constraints: `purpose` is non-empty string; `inputs`/`outputs` are lists of objects with name/type/description; `dependencies` is a list of strings (component_refs); `invariants`/`side_effects`/`failure_modes` are lists of non-empty strings.
DoD: unit test: valid specs pass; invalid specs (missing required field, wrong type, empty string where required) are rejected; error message is helpful.

### T-010.2 — Prompt engineering + LLM call
Status: ready · Depends on: [T-010.1] · Reads: [INTEGRATIONS.md#3-llm-provider, ARCHITECTURE.md#components, skills: testing-standard]
Owns: [src/spec_atlas/specify/engine.py, tests/specify/test_engine.py]
Contract: `SpecifyEngine` class:
  - `generate(focal_node: Node, neighbors: list[Node], edges: list[Edge], session: LLMProvider) -> (Spec, Provenance)` — construct a prompt that describes the focal node + subgraph, call `session.complete()` with a JSON schema for the spec, parse and validate the response, return the validated spec + provenance dict.
  - Prompt structure: (1) "Generate a spec for the following symbol:"; (2) show focal node (qualified_name, signature, docstring, file/line); (3) show neighbors (calls, imports, classes it extends, etc.); (4) request JSON output matching the schema.
  - Provenance construction: map each field in the output to source spans (e.g., "purpose" comes from the focal node's docstring → `{file, start_line, end_line}` of the docstring; "dependencies" comes from import edges → spans of the import statements).
  - Use `LLMProvider.complete(messages, schema=spec_schema_json)` for structured output.
DoD: unit test with the fake LLM provider (inject a canned spec JSON response); verify the engine parses it, validates it, returns the spec with provenance; test error case (invalid JSON, LLM failure, validation error).

### T-010.3 — Provenance tracking per spec field
Status: ready · Depends on: [T-010.2] · Reads: [DATA-MODEL.md#spec-db, skills: testing-standard]
Owns: [src/spec_atlas/specify/provenance.py, tests/specify/test_provenance.py]
Contract: `ProvenanceTracker` class:
  - `link_spec_field(spec_field_name: str, source_nodes: list[Node], source_edges: list[Edge]) -> list[{file, start_line, end_line}]` — given a spec field name (e.g., "purpose", "dependencies", "invariants"), map it to the source spans in the focal node and neighbors that justify it.
  - Rules:
    - "purpose" → focal node's docstring span (if available; else focal node's definition span).
    - "inputs" → focal node's signature span (extracted from function params).
    - "outputs" → focal node's signature span or docstring (if return type mentioned).
    - "dependencies" → import edges' definition spans + called functions' definition spans.
    - "invariants" / "side_effects" → docstring of the focal node or its callees (heuristic; low confidence).
    - "failure_modes" → docstring + any error handling in the focal node.
  - Return a list of spans that cover the claimed source (may be multiple spans per field).
DoD: unit test: construct a focal node + neighbors with known spans; call link_spec_field for each field; verify the returned spans are correct (e.g., "purpose" points to docstring, "dependencies" points to imports).

## HANDOFF / STATUS

### T-010.1 — JSON Schema validation (DONE 2026-06-20)
**Implementation:** Pydantic models for specs (InputSpec, OutputSpec, Spec).
- Spec: purpose (required), inputs/outputs/dependencies/invariants/side_effects/failure_modes (optional lists)
- Validation: required fields non-empty, empty strings filtered from lists
- `validate_spec(dict) → dict`: validates and returns sanitized spec
- `spec_json_schema() → dict`: returns JSON schema for LLM structured output

**Tests:** 23 tests covering InputSpec, OutputSpec, Spec validation, schema generation.

**Key files:** `src/spec_atlas/specify/schema.py` (94 loc), `tests/specify/test_schema.py` (169 loc).

---

### T-010.2 — Specify engine + LLM call (DONE 2026-06-20)
**Implementation:** SpecifyEngine.generate(focal_node, neighbors, edges, llm_provider) → (spec_dict, provenance_dict).
- Prompt: describes focal node (qualified_name, signature, docstring) + neighbors + edges
- LLM call: uses LLMProvider.complete() with spec JSON schema for structured output
- Validation: parse response, validate against schema, raise ValueError if invalid
- Provenance: maps each field to source spans (preliminary mapping)

**Prompt structure:**
  - Focal component (name, kind, language, file/line, signature, docstring)
  - Related components (up to 20 neighbors)
  - Relationships (edge kinds + confidence)
  - Request JSON spec matching schema

**Tests:** 9 tests covering valid/invalid LLM responses, provenance generation, error handling, edge cases.

**Key files:** `src/spec_atlas/specify/engine.py` (138 loc), `tests/specify/test_engine.py` (213 loc).

---

### T-010.3 — Provenance tracking + binding (DONE 2026-06-20)
**Implementation:** ProvenanceTracker for mapping spec fields → source spans.
- SourceSpan: {file, start_line, end_line, confidence}
- link_spec_field(field_name, focal_node, neighbors, edges) → list of spans
  - purpose: focal docstring (high conf), or definition
  - inputs/outputs: focal signature (1.0 conf)
  - dependencies: import/call edges (edge confidence)
  - invariants/side_effects/failure_modes: focal/neighbor docstrings (0.9/0.5 conf)
- validate_spans(list): check span structure, line order, types

**Tests:** 14 tests covering all field types, validation rules, edge cases.

**Key files:** `src/spec_atlas/specify/provenance.py` (133 loc), `tests/specify/test_provenance.py` (189 loc).

---

**F-010 status:** ✅ **COMPLETE** (all 3 tasks done)
- 46 total tests passing for F-010
- Spec generation is end-to-end functional (focal node → LLM → validated spec + provenance)
- Ready for F-011 (spec persistence)
- 169 total project tests passing
