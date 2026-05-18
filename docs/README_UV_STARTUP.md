# Digital Human Memory Vault - UV-Only Startup Guide

## System Architecture

The Memory Vault is a 3-tier system:

```
Frontend (Next.js 16, Port 3000, npm)
         ↓
Backend (FastAPI 8000, uv) → Supabase REST API
         ↓
Worker (Python AI Processing, uv)
```

**Environment: DOUBLE FALLBACK (NO Redis, NO Local LLM, Cloud LLM Groq)**

---

## Prerequisites

### Required Tools
- **Node.js**: v18+ (for frontend npm packages)
- **Python**: 3.11+ 
- **`uv`**: Fast Python package manager - ONLY Python package tool
- **`npm`**: v9+ (for frontend only)

### Install uv (Windows)
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify
uv --version
```

---

## Step 1: Environment Setup

### 1.1 Create `.env` File

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
```

Create `.env`:

```env
SUPABASE_URL=https://cdgcmcznmqykmzyovnmn.supabase.co
SUPABASE_SECRET_KEY=<your-secret-key>
SUPABASE_ANON_KEY=<your-anon-key>
GROQ_API_KEY=<your-groq-key>
REDIS_URL=redis://localhost:6379
BACKEND_PORT=8000
BACKEND_HOST=127.0.0.1
WORKER_POLL_INTERVAL=5
LOCAL_LLM_TIMEOUT=3
```

---

## Step 2: Backend Setup (FastAPI + uv ONLY)

### 2.1 Install Dependencies with uv

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono

# ONLY uv command - NO pip
uv pip install -r backend/requirements.txt
```

**Verify:**
```powershell
uv pip list | Select-String "fastapi|supabase|redis"
```

### 2.2 Start Backend

```powershell
python run_backend.py
```

**Expected:** `INFO: Application startup complete`

---

## Step 3: Frontend Setup (npm ONLY)

### 3.1 Install Dependencies

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend
npm ci
```

### 3.2 Start Frontend

```powershell
npm run dev
```

**Expected:** `✓ Ready in XXXX ms`

---

## Step 4: Worker Setup (uv ONLY)

### 4.1 Start Worker

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
python run_worker.py
```

**Expected:** `Starting AI Worker process...`

---

## Three-Terminal Startup

| Terminal | Command | Port |
|----------|---------|------|
| 1 | `cd mono && python run_backend.py` | 8000 |
| 2 | `cd frontend && npm run dev` | 3000 |
| 3 | `cd mono && python run_worker.py` | N/A |

---

## Using `uv` (Python Package Manager ONLY)

```powershell
# Install packages
uv pip install -r backend/requirements.txt

# Add new package
uv pip install httpx

# Update all
uv pip install --upgrade -r backend/requirements.txt

# List packages
uv pip list

# Force reinstall
uv pip install --force-reinstall -r backend/requirements.txt
```

**CRITICAL:** Never use `pip` directly. Always use `uv pip`.

---

## Quick Health Checks

```powershell
# Backend
Invoke-WebRequest http://127.0.0.1:8000/docs

# Frontend  
Invoke-WebRequest http://127.0.0.1:3000

# uv verification
uv pip list | findstr fastapi
```

---

## Troubleshooting

**Port Already in Use:**
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**uv Not Found:**
```powershell
uv --version
# If fails, reinstall: irm https://astral.sh/uv/install.ps1 | iex
```

**Module Import Error:**
```powershell
$env:PYTHONPATH = "C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono"
python run_backend.py
```

**Missing Dependencies:**
```powershell
uv pip install --force-reinstall -r backend/requirements.txt
```

---

## Status: ✅ Ready for Full Lifecycle Test

Once all 3 services running:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- Worker: Check terminal logs

Execute: `python full_lifecycle_test.py`

---

**Last Updated:** 2026-05-17  
**Python Package Manager:** `uv` ONLY  
**Frontend Package Manager:** `npm` ONLY
