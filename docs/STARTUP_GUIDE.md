# Digital Human Memory Vault - Complete Startup Guide

## System Architecture

The Memory Vault is a 3-tier system:

```
Frontend (Next.js 16, Port 3000)
         ↓
Backend (FastAPI 8000) → Supabase REST API
         ↓
Worker (Python AI Processing)
```

**Environment Constraints (DOUBLE FALLBACK):**
- ❌ NO REDIS: System degrades to direct `staging_vault` polling
- ❌ NO LOCAL LLM: Worker uses Cloud LLM (Groq/Gemini)
- ✅ Cloud LLM: Groq API configured in `.env`
- ✅ Supabase: Project `cdgcmcznmqykmzyovnmn.supabase.co` fully operational

---

## Prerequisites

### Required Tools
- **Node.js**: v18+ (for frontend)
- **Python**: 3.11+ (for backend & worker)
- **uv**: Fast Python package manager (https://astral.sh/uv) - ONLY Python package manager used
- **npm**: v9+ (for frontend)

### Installation & Verification

```powershell
# Verify uv is installed
uv --version

# Verify Python via uv
uv python --version

# Verify npm
npm --version
```

**Note:** We use `uv run` for all Python commands. No `pip` is needed.

---

## Step 1: Environment Setup

### 1.1 Create `.env` File

Navigate to the project root and create `.env`:

```bash
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
```

Create `.env` with these values (contact DevOps for secrets):

```env
# Supabase Configuration
SUPABASE_URL=https://cdgcmcznmqykmzyovnmn.supabase.co
SUPABASE_SECRET_KEY=<your-secret-key-here>
SUPABASE_ANON_KEY=<your-anon-key-here>

# LLM Configuration (Cloud Fallback)
GROQ_API_KEY=<your-groq-key-here>
GEMINI_API_KEY=<optional-gemini-key>

# Redis (Optional - Not required for DOUBLE FALLBACK)
REDIS_URL=redis://localhost:6379

# Backend Configuration
BACKEND_PORT=8000
BACKEND_HOST=127.0.0.1

# Worker Configuration
WORKER_POLL_INTERVAL=5
LOCAL_LLM_TIMEOUT=3
```

**Verification:**
```powershell
# Verify .env is readable
Get-Content .env | Select-String "SUPABASE_URL"
```

---

## Step 2: Backend Setup (FastAPI + uv)

### 2.1 Install Backend Dependencies Using `uv`

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono

# Using uv (ONLY method - FastAPI, Supabase, Redis)
uv pip install -r backend/requirements.txt
```

**Verify Installation:**
```powershell
uv pip list | Select-String "fastapi|supabase|redis"
# Expected: fastapi, supabase, redis[hiredis] listed
```

### 2.2 Start Backend Server

**Using uv to run the startup script:**

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_backend.py
```

**Expected Output:**
```
✅ Backend module imported successfully
Starting FastAPI server on http://127.0.0.1:8000
======================================================
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

**Verify Backend is Running (New Terminal):**
```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/docs' -TimeoutSec 5
# Expected: Status 200
```

**API Documentation (Auto-generated):**
- OpenAPI/Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## Step 3: Frontend Setup (Next.js + npm)

### 3.1 Install Frontend Dependencies

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend

# Using npm (Node.js packages - separate from Python uv)
npm ci
```

**Note on Windows Issues:**
If you encounter `Turbopack` errors (common on Windows):
- Next.js automatically falls back to Webpack
- Performance is acceptable
- No action needed

### 3.2 Create Frontend `.env.local`

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://cdgcmcznmqykmzyovnmn.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key-here>
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_APP_NAME=Memory Vault
```

### 3.3 Start Frontend Server

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend

# Development mode (Webpack on Windows)
npm run dev

# Or explicitly with Webpack (if needed)
npm run dev -- --webpack
```

**Expected Output:**
```
> frontend@0.1.0 dev
> next dev

▲ Next.js 16.2.6 (webpack)
- Local:         http://localhost:3000
- Network:       http://192.168.0.137:3000
✓ Ready in 1200ms
```

**Access Frontend:**
- Dashboard: http://localhost:3000/dashboard
- Admin Panel: http://localhost:3000/admin

---

## Step 4: Worker Setup (Python AI Processing)

### 4.1 Verify Worker Dependencies (Installed with Backend via uv)

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono

# Verify via uv:
uv run python -c "import redis; import asyncio; print('✅ Worker dependencies OK')"
```

### 4.2 Start Worker Process

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_worker.py
```

**Expected Output:**
```
✅ Worker module imported successfully
Starting AI Worker process...
======================================================
2026-05-17 02:30:15 [vault-worker] INFO: Connecting to Redis...
2026-05-17 02:30:15 [vault-worker] INFO: Redis connection failed; using staging_vault polling
2026-05-17 02:30:15 [vault-worker] INFO: Starting consumer loop: stream=vault:ingest
2026-05-17 02:30:15 [vault-worker] INFO: Checking staging_vault for pending rows...
```

**Note:** Worker gracefully operates without Redis (DOUBLE FALLBACK mode).

---

## Complete Startup Checklist (Using uv)

### Terminal 1: Backend Server
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_backend.py
# Keep this terminal open
```

### Terminal 2: Frontend Server
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend
npm run dev
# Keep this terminal open
```

### Terminal 3: Worker Process
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_worker.py
# Keep this terminal open
```

### Terminal 4: Run Full Lifecycle Test
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono

# Execute full lifecycle test (PHASE 1-3)
uv run python full_lifecycle_test.py
```

---

## Verification Tests

### 1. Frontend Health Check
```powershell
$response = Invoke-WebRequest -Uri 'http://localhost:3000' -TimeoutSec 5
if ($response.StatusCode -eq 200) {
    Write-Host "✅ Frontend (Port 3000): RUNNING"
} else {
    Write-Host "❌ Frontend (Port 3000): FAILED"
}
```

### 2. Backend Health Check
```powershell
$response = Invoke-WebRequest -Uri 'http://localhost:8000/docs' -TimeoutSec 5
if ($response.StatusCode -eq 200) {
    Write-Host "✅ Backend (Port 8000): RUNNING"
} else {
    Write-Host "❌ Backend (Port 8000): FAILED"
}
```

### 3. Worker Health Check
```powershell
# Check if worker process is running and polling
# Look for "Checking staging_vault for pending rows..." in worker terminal output
```

### 4. Supabase Connectivity Check
```powershell
python -c "
from supabase import create_client
import os
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_SECRET_KEY')
client = create_client(url, key)
result = client.table('staging_vault').select('count', count='exact').execute()
print(f'✅ Supabase Connected: {result.count} records in staging_vault')
"
```

---

## Troubleshooting

### Issue: Port Already in Use

**Backend (Port 8000):**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

**Frontend (Port 3000):**
```powershell
# Find process using port 3000
netstat -ano | findstr :3000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

### Issue: Redis Connection Errors
**Expected in DOUBLE FALLBACK mode.** Worker will automatically:
1. Try to connect to Redis
2. Timeout after 5 seconds
3. Fall back to polling `staging_vault` directly
4. Continue processing normally ✅

### Issue: LLM Timeout Errors
**Expected in DOUBLE FALLBACK mode.** Worker will:
1. Attempt local LLM (llama.cpp)
2. Timeout after 3 seconds
3. Fall back to Cloud LLM (Groq)
4. Process successfully ✅

### Issue: Module Import Errors

**Python Import Error:**
```powershell
# Set PYTHONPATH explicitly
$env:PYTHONPATH = "C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono"
python run_backend.py
```

**Missing Dependencies:**
```powershell
# Use uv to reinstall cleanly
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv pip install --force-reinstall -r backend/requirements.txt
```

**Python Not Found:**
```powershell
# Verify uv is installed and working
uv --version
# Should show: uv X.X.X
```

---

## Using `uv` - Complete Reference

### Why `uv`?
- **10-100x faster** than pip
- **Parallel dependency resolution**
- **Deterministic builds**
- **Better Windows support**
- **NO pip required**

### Common `uv` Commands

```powershell
# Sync dependencies (recommended)
uv sync

# Run Python scripts
uv run python script.py

# Run with arguments
uv run python run_backend.py --port 8001

# Check Python version
uv python --version

# List installed packages
uv pip list

# Verify dependencies
uv pip check
```

---

## Full Startup Script (Automated - Using uv)

Save this as `start_all.ps1`:

```powershell
# start_all.ps1
$projectRoot = "C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono"

Write-Host "🚀 Starting Digital Human Memory Vault (uv)..." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# Check if .env exists
if (-not (Test-Path "$projectRoot\.env")) {
    Write-Host "❌ ERROR: .env file not found in $projectRoot" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Environment file verified" -ForegroundColor Green

# Start Backend in new window (using uv)
Write-Host "📝 Starting Backend (Port 8000) with uv..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; uv run python run_backend.py"
Start-Sleep -Seconds 3

# Start Frontend in new window
Write-Host "🎨 Starting Frontend (Port 3000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot\frontend'; npm run dev"
Start-Sleep -Seconds 3

# Start Worker in new window (using uv)
Write-Host "⚙️  Starting Worker with uv..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$projectRoot'; uv run python run_worker.py"
Start-Sleep -Seconds 2

Write-Host "`n✅ All services starting!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "📊 Frontend:  http://localhost:3000" -ForegroundColor Yellow
Write-Host "📊 Backend:   http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "⚙️  Worker:    Check worker terminal for logs" -ForegroundColor Yellow
Write-Host "`nPress CTRL+C in any terminal to stop services" -ForegroundColor Gray
```

**Usage:**
```powershell
./start_all.ps1
```

---

## Next Steps: Running Full Lifecycle Test

Once all services are running, proceed to **PHASE 1: ACT I - THE GENESIS ENCOUNTER**

See `FULL_LIFECYCLE_TEST_GUIDE.md` for the complete patient journey test.

---

## Production Deployment

For production deployment:

1. **Set `reload=False`** in `run_backend.py`
2. **Use a process manager** (PM2, supervisor, systemd)
3. **Enable HTTPS** with valid certificates
4. **Configure database backups** in Supabase
5. **Enable monitoring** and alerting
6. **Document API keys** securely

---

**Last Updated:** 2026-05-17  
**Maintained By:** Principal QA Automation Engineer  
**Status:** ✅ Production Ready
