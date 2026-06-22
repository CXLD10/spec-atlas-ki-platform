# Eval Harness Test Fixture

## Test Repository: `requests` (Python HTTP Library)

**Source:** https://github.com/psf/requests  
**Snapshot Date:** 2026-06-19  
**Size:** ~6.4k LOC across 19 files  

### Why requests?

✅ Real production Python library (widely-used, well-maintained)  
✅ Medium-sized (5–20k LOC target for eval harness)  
✅ Well-documented (clear purpose, good docstrings, test coverage)  
✅ Good for curating questions (multiple modules, clear responsibilities)  
✅ Diverse component types (functions, classes, modules, decorators)  

### Key modules:

- `requests/api.py`: High-level API functions (get, post, etc.)
- `requests/sessions.py`: Session class (core orchestrator)
- `requests/models.py`: Request/Response objects
- `requests/adapters.py`: HTTP adapters (mounting mechanism)
- `requests/auth.py`: Authentication handlers
- `requests/cookies.py`: Cookie management
- `requests/hooks.py`: Event hooks mechanism
- `requests/structures.py`: CaseInsensitiveDict, etc.

### Question set (curated, with golden answers)

**Q1: How does the requests library handle HTTP GET requests?**
- **Expected answer:** Via the `get()` function in `api.py`, which calls `request()` with method='GET'; internally uses Session class to manage the request.
- **Expected citations:** requests/api.py:55-60 (get function), requests/sessions.py:400-420 (Session.request method)
- **Strategy:** vector_search (conceptual, big-picture)

**Q2: What authentication mechanisms does requests support?**
- **Expected answer:** Built-in support for HTTP Basic Auth (BasicAuth class), Digest Auth (HTTPDigestAuth), plus extensible auth handler interface (auth parameter)
- **Expected citations:** requests/auth.py:20-50 (auth classes), requests/models.py:100-110 (auth application)
- **Strategy:** vector_search

**Q3: How do mounted adapters work in requests?**
- **Expected answer:** Session has a mount() method registering protocol-specific adapters (HTTP, HTTPS). Adapters are looked up by URL prefix when a request is made, enabling custom transports.
- **Expected citations:** requests/sessions.py:300-350 (mount method), requests/adapters.py:1-30 (adapter base class)
- **Strategy:** vector_search

**Q4: What does the Session class do?**
- **Expected answer:** Manages persistent HTTP connections, cookies, auth, default headers, and request/response hooks. Re-uses TCP connections across requests for efficiency.
- **Expected citations:** requests/sessions.py:200-250 (Session class docstring)
- **Strategy:** vector_search

**Q5: How are cookies persisted across requests in a session?**
- **Expected answer:** Session stores cookies in a CookieJar object (from http.cookiejar), updated after each response. Cookies are automatically included in subsequent requests.
- **Expected citations:** requests/sessions.py:400-450 (cookie handling), requests/cookies.py:10-50 (cookie jar integration)
- **Strategy:** vector_search

[Add 15+ more questions in this format]

### Ingestion checklist (for T-016.1/2/3):

- [ ] Clone requests repo to fixtures/requests-lib/ (ignore for now; use external clone)
- [ ] Run ingest pipeline on requests repo
- [ ] Verify nodes extracted: ~100-150 top-level functions/classes
- [ ] Verify edges: ~50-100 intra-module call/import edges
- [ ] Extract golden answers (manual curation; 1-2 hours of work)
- [ ] Define metrics for each Q (expected citations, success criteria)
- [ ] Implement BaselineRetriever pipeline
- [ ] Run eval harness on both pipelines
- [ ] Produce metrics table + report

### Metrics (expected, from master plan):

| Metric | Built Pipeline | Baseline | Target |
|--------|---|---|---|
| Citation Accuracy | 80%+ | 60%- | A > B |
| Avg Context Size (tokens) | 1200 | 3500 | A < B |
| Avg Latency (sec) | 1.8 | 0.9 | N/A (A may be slower due to LLM) |
| Hallucination Rate | 5% | 18% | A < B |

### Next steps:

1. Commit this fixture doc
2. In T-016.1, implement BaselineRetriever
3. In T-016.2, run both pipelines on requests repo
4. In T-016.3, produce final eval report

---

**Note for local testing:** Clone requests repo manually:
```bash
git clone https://github.com/psf/requests.git /tmp/requests-eval --depth 1
cd /tmp/requests-eval
# Then ingest via the Spec-Atlas ingest pipeline (requires Postgres, not in-memory SQLite)
```
