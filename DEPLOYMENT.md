# Deployment Guide — Spec-Atlas Multi-User SaaS

**Zero-cost hosting on Railway (backend) + Vercel (frontend) with automatic session cleanup and Groq rate-limit handling.**

---

## Quick Start (5 minutes)

### Backend (Railway)

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Create Railway Project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Find `spec-atlas-ki-platform`
   - Authorize

3. **Configure Environment Variables**
   Railway Dashboard → Variables:
   ```
   GROQ_API_KEYS=gsk_xxx,gsk_yyy,gsk_zzz,gsk_www
   ANALYSIS_DB_URL=postgresql://...
   SPEC_DB_URL=postgresql://...
   PYTHONUNBUFFERED=1
   ```
   **Get keys from**: https://console.groq.com/keys (comma-separated, no spaces)

4. **Auto-deployment**
   - Dockerfile runs `alembic upgrade head` → migrations applied
   - Starts uvicorn on port 8000
   - Health check at `/health` validates

### Frontend (Vercel)

1. **Connect Vercel**
   - https://vercel.com
   - "New Project" → select GitHub repo
   - Framework: React
   - Root: `frontend/`

2. **Set Env Vars**
   ```
   VITE_API_URL=https://spec-atlas-backend-xxxxx.railway.app
   ```

3. **Deploy** (auto on GitHub push)

---

## Architecture

- **User**: Browser → Session ID (cookie)
- **Frontend**: Vercel (React + Vite)
- **Backend**: Railway (FastAPI + SQLAlchemy)
- **Database**: PostgreSQL (Railway)
- **LLM**: Groq (4 keys, round-robin)

## Features Deployed

✅ **Multi-user isolation**: session_id on all tables
✅ **2-hour auto-delete**: CleanupJob runs every 15 min
✅ **Groq multi-key rotation**: 4 keys, 429 fallback to fake LLM
✅ **3-repo limit**: enforced per session
✅ **Delete controls**: repo delete + clear all data buttons
✅ **Privacy banner**: shown to all users
✅ **Zero setup**: no login, auto session on first visit

## Cost: $0

- Railway free: 500MB RAM
- Vercel free: unlimited deploys
- Groq free: 4 keys × 30 req/min
- PostgreSQL free: 5GB

## Next: Push & Deploy

```bash
git push origin main
# Then follow Quick Start above
```

🚀 **Live in 5 minutes**
