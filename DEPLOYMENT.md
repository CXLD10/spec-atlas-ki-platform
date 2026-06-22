# Deployment Guide — Spec-Atlas Phase 2

**Date:** June 22, 2026  
**Status:** Phase 2 fixes complete and ready for production deployment  
**Test Coverage:** 318 backend tests passing, 0 TypeScript errors

---

## Pre-Deployment Checklist

- [x] All backend tests pass (318/318)
- [x] Frontend TypeScript strict mode (0 errors)
- [x] Bundle size optimized (~750KB gzip)
- [x] Three critical issues fixed:
  - [x] LLM provenance (JSON schema)
  - [x] Graph interactivity (OrbitControls)
  - [x] Documentation cleanup (emojis removed)
- [x] No breaking changes to API contracts
- [x] Backward compatible with existing data

---

## Deployment Steps

### 1. Deploy Frontend (Vercel / Netlify)

**Option A: Vercel (Recommended)**

```bash
# Install Vercel CLI (if not already installed)
npm install -g vercel

# Navigate to frontend directory
cd frontend

# Deploy
vercel --prod

# Follow prompts:
# - Link to existing project or create new
# - Set framework: Vite
# - Set root directory: .
# - Build command: npm run build
# - Output directory: dist
```

**Option B: Netlify**

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Navigate to frontend directory
cd frontend

# Deploy
netlify deploy --prod --dir=dist

# Or: Connect GitHub repo for auto-deploy
netlify init
```

**Option C: Manual (any hosting)**

```bash
cd frontend
npm run build
# Upload dist/ folder contents to your hosting provider
```

### 2. Configure Frontend Environment

After deployment, set the backend API URL:

**For Vercel:**
```
Add environment variable: VITE_API_URL=https://api.yourdomain.com
```

**For Netlify:**
```
Build & Deploy Settings → Environment
Add: VITE_API_URL=https://api.yourdomain.com
```

**In code (if needed):**
```typescript
// frontend/src/config.ts
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
```

### 3. Deploy Backend (if not already deployed)

**Recommended: Docker + Cloud Run / Heroku / Railway**

```bash
# Build Docker image
docker build -t spec-atlas-backend .

# Push to registry (e.g., GCR, Docker Hub)
docker tag spec-atlas-backend gcr.io/your-project/spec-atlas-backend
docker push gcr.io/your-project/spec-atlas-backend

# Deploy to Cloud Run
gcloud run deploy spec-atlas-backend \
  --image gcr.io/your-project/spec-atlas-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ANALYSIS_DB_URL=postgresql://... \
  --set-env-vars SPEC_DB_URL=postgresql://...
```

### 4. Configure CORS

The backend needs CORS configured to allow requests from your frontend domain.

**In backend (already configured in F-017):**
```python
# src/spec_atlas/api/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. Test Production Deployment

```bash
# Test health endpoint
curl https://api.yourdomain.com/health

# Expected response:
{
  "status": "ok",
  "analysis_db": "ok",
  "spec_db": "ok",
  "llm": {"provider": "gemini", "status": "ok"},
  "embed": {"provider": "fastembed", "status": "ok"}
}

# Test LLM endpoint (will show empty database if not indexed)
curl -X POST https://api.yourdomain.com/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this code?", "repo": "default"}'

# Expected: claims array with proper sources (if data indexed)
```

---

## Production Checklist

Before going live, verify:

- [x] Frontend deployed and accessible
- [x] Backend deployed and accessible
- [x] CORS configured correctly
- [ ] Database URLs configured (env vars)
- [ ] LLM API key configured (env vars)
- [ ] Rate limiting active (slowapi configured)
- [ ] Logging and monitoring set up
- [ ] SSL/TLS certificates valid
- [ ] Health endpoints responding

---

## Rollback Plan

If issues occur in production:

1. **Frontend:** Redeploy previous version
   ```bash
   vercel rollback  # Vercel
   # or manually deploy dist from last working build
   ```

2. **Backend:** Revert database connections to previous instance
   ```bash
   # Update env vars to point to stable backend
   ```

3. **Emergency contacts:**
   - Check logs for errors
   - Verify database connectivity
   - Confirm API rate limits not exceeded

---

## Monitoring After Deployment

**Key metrics to watch:**

- [ ] `/health` endpoint responding with 200
- [ ] `/api/ask` latency < 2 seconds (including LLM time)
- [ ] Zero 5xx errors in logs
- [ ] Frontend loads without 404s
- [ ] CORS errors not appearing in browser console

**Useful queries:**

```bash
# Check health status
curl -s https://api.yourdomain.com/health | jq .

# Monitor API errors (if using structured logging)
# e.g., in Cloud Logging: resource.type=cloud_run_revision AND severity=ERROR

# Check rate limiting
curl -s https://api.yourdomain.com/api/ask -H "Content-Type: application/json" \
  -d '{"question":"test"}' | grep -i "x-ratelimit"
```

---

## What's Deployed (Phase 2)

**Backend Changes:**
- ✅ JSON schema for LLM structured output (ANSWER_SCHEMA)
- ✅ Proper claim generation with file:line provenance
- ✅ No breaking API changes

**Frontend Changes:**
- ✅ OrbitControls for graph interactivity
- ✅ 6 decorative emojis removed
- ✅ Help text updated
- ✅ Optimized bundle (~750KB gzip)

**What's NOT deployed yet:**
- ❌ Phase 3: Spec generation pipeline (T-005, F-010, F-011)
- ❌ Phase 3: Group clustering and group.md tree
- ❌ Phase 3: Spec graph construction

---

## Post-Deployment: Phase 3 Roadmap

After Phase 2 deployment is stable:

1. **Phase 3.1:** Implement spec generation at indexing time
2. **Phase 3.2:** Build group clustering + group.md tree
3. **Phase 3.3:** Construct spec graph from code edges

Estimated duration: 2-3 days

---

## Support

**If deployment fails:**
1. Check `.env` files are not committed (should be gitignored)
2. Verify database URLs are valid
3. Confirm LLM API keys are set
4. Check rate limiting is not blocking requests
5. Review logs for specific errors

**Common issues:**
- 503 degraded status → Database not connected
- 429 Too Many Requests → Rate limit exceeded
- CORS errors → Frontend origin not in allow_origins
- TypeScript errors on deploy → Use npm run build locally first

