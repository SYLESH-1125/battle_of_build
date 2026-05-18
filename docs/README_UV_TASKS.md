# 🚀 QUICK START WITH UV TASKS

## Setup
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
```

## Start Services (3 Terminals)

### Terminal 1: Backend
```powershell
uv run task serve
```

### Terminal 2: Frontend
```powershell
cd frontend
npm run dev
```

### Terminal 3: Worker
```powershell
uv run task worker
```

## Access
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Available Commands

```powershell
# Backend server (FastAPI + uvicorn)
uv run task serve

# Worker (data processing)
uv run task worker

# Run lifecycle test (PHASE 1-3)
uv run task test

# Health check verification
uv run task verify

# Full orchestration (start all + test)
uv run task orchestrate
```

## What Each Service Does

**Backend (`uv run task serve`)**
- FastAPI server on port 8000
- REST API endpoints
- Handles client requests

**Frontend (`npm run dev`)**
- Next.js dashboard on port 3000
- User interface
- Admin panel

**Worker (`uv run task worker`)**
- Processes staging records
- Generates FHIR JSON
- Detects conflicts
- Falls back to Cloud LLM if needed

## Test Full Lifecycle
```powershell
uv run task test
```

This runs PHASE 1-3:
1. Patient genesis (new prescription)
2. Clinical conflict (allergy detection)
3. Admin override (audit trail)

All 11 assertions should PASS ✅

## Troubleshooting

**If `uv run task` doesn't work:**
```powershell
# Use direct commands instead
uv run python run_backend.py
uv run python run_worker.py
uv run python full_lifecycle_test.py
```

**Check logs:**
```powershell
# View terminal output for any errors
# Backend errors show in Terminal 1
# Worker logs show in Terminal 3
```

**Verify services:**
```powershell
uv run task verify
```

This checks if all ports are responding correctly.

---

**Status:** ✅ Ready for production deployment

See STARTUP_GUIDE.md for advanced configuration options.
