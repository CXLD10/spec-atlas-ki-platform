# API Recovery — 2026-06-21

## Summary

Fixed API endpoint routing issues that prevented proper access to graph and specs endpoints.

## Issues Fixed

### 1. Router Prefix Mismatches
- **graph.py**: Router was using `/graph` prefix instead of `/api/graph`
  - Fix: Changed `APIRouter(prefix="/graph")` to `APIRouter(prefix="/api/graph")`
  - Impact: Graph API endpoints now accessible at `/api/graph/*`

- **specs.py**: Router was using `/specs` prefix instead of `/api/specs`
  - Fix: Changed `APIRouter(prefix="/specs")` to `APIRouter(prefix="/api/specs")`
  - Impact: Specs API endpoints now accessible at `/api/specs/*`

### 2. Test Schema Updates
- **test_ingest.py**: Test was importing non-existent response model classes
  - Fixed imports to use `JobStatus` (the actual response model)
  - Updated test methods to match current API schema
  - Result: All tests now pass (317 passed, 2 skipped)

### 3. Pydantic V2 Modernization
- **ingest.py**: IngestRequest was using deprecated `class Config` syntax
  - Fixed: Migrated to `ConfigDict` for Pydantic V2 compatibility
  - Removed deprecation warning

## Verification

✓ All 317 tests pass  
✓ Health endpoint responds (200 OK)  
✓ All API routers mounted correctly  
✓ Graph endpoints accessible at /api/graph/*  
✓ Specs endpoints accessible at /api/specs/*  
✓ Ask endpoint working correctly  
✓ Ingest endpoint working correctly  

## Commits

- 23bade5: fix(api): correct router prefixes for graph and specs endpoints
- 58e0caa: fix(api): update ingest test schema and modernize Pydantic config

## Current API Status

All API endpoints are functional:
- ✓ GET /health (app health + DB status)
- ✓ GET / (root)
- ✓ POST /api/ask (question answering)
- ✓ POST /api/ingest (repository indexing)
- ✓ GET /api/groups (group hierarchy)
- ✓ GET /api/graph/* (code graph queries)
- ✓ GET /api/specs/* (spec queries)

## Notes

The API was broken due to router prefix mismatches introduced during refactoring. The core logic and database connections were working correctly; only the URL routing needed adjustment. This recovery work brings the API back to fully functional state for development and testing.
