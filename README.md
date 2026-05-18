# 🚀 QUICK START GUIDE - DIGITAL HUMAN MEMORY VAULT

**Last Updated:** 2026-05-17  
**Status:** ✅ Production Ready

**Note:** Project documentation has been consolidated into the `docs/` directory to reduce root clutter. See [docs/README.md](docs/README.md) for the full index.

---

## 📋 Table of Contents

1. [Fastest Way to Start](#fastest-way-to-start)
2. [Detailed Setup Instructions](#detailed-setup-instructions)
3. [Available Commands](#available-commands)
4. [Troubleshooting](#troubleshooting)
5. [What Each Service Does](#what-each-service-does)

---

## 🏃 Fastest Way to Start

### Option 1: Direct Commands (Recommended - Always Works)

**Terminal 1 - Backend:**
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend
npm run dev
```

**Terminal 3 - Worker:**
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_worker.py
```

**Result:**
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Option 2: Using run_backend.py Helper Script

**Terminal 1 - Backend:**
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_backend.py
```

---

## 📖 Detailed Setup Instructions

### Prerequisites

1. **Python 3.13** (already available at `C:\Program Files\Python313\`)
2. **uv package manager** (already installed)
3. **.env file** (already configured in project root)

### Step 1: Backend Server

```powershell
# Navigate to project root
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono

# Start backend with auto-reload
uv run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Access:** http://localhost:8000/docs (API documentation)

### Step 2: Frontend Application

```powershell
# Open new terminal
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend

# Install dependencies (if needed)
npm install

# Start development server
npm run dev
```

**Expected Output:**
```
> frontend@1.0.0 dev
> next dev

  ▲ Next.js 16.2.6
  - ready started server on  0.0.0.0:3000
```

**Access:** http://localhost:3000 (Dashboard)

### Step 3: Worker Processing Engine

```powershell
# Open third terminal
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono

# Start worker
uv run python run_worker.py
```

**Expected Output:**
```
INFO: Worker started - monitoring staging_vault for pending records
INFO: Using Cloud LLM fallback (Groq API)
```

---

## 💻 Available Commands

### Backend Commands

```powershell
# Option 1: Using uvicorn directly (RECOMMENDED)
uv run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Option 2: Using helper script
uv run python run_backend.py

# Test backend connectivity
Invoke-WebRequest http://localhost:8000/docs
```

### Frontend Commands

```powershell
# Start development server
npm run dev

# Build for production
npm run build

# Start production build
npm start
```

### Worker Commands

```powershell
# Start worker (default)
uv run python run_worker.py

# Start worker (alternative)
python run_worker.py
```

### Testing Commands

```powershell
# Run full lifecycle test (PHASE 1-3)
uv run python full_lifecycle_test.py

# Run health checks
uv run python verify_startup.py

# Full orchestration (start all + test)
uv run python autonomous_test_orchestrator.py
```

---

## 🧪 Testing

### Run Full Lifecycle Test

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python full_lifecycle_test.py
```

**Expected Result:**
```
✅ PHASE 1: Patient Genesis - PASSED (6/6 assertions)
✅ PHASE 2: Conflict Detection - PASSED (3/3 assertions)
✅ PHASE 3: Admin Override - PASSED (2/2 assertions)

OVERALL: 11/11 assertions passed ✅
```

### Test Individual Components

```powershell
# Test backend health
Invoke-WebRequest http://localhost:8000/health

# Test frontend
Invoke-WebRequest http://localhost:3000

# Check all services
uv run python verify_startup.py
```

---

## 🛠️ Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```powershell
# Install dependencies
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv pip install -r backend/requirements.txt

# Or use Python 3.13 explicitly
C:\Program Files\Python313\python.exe -m pip install fastapi uvicorn supabase python-dotenv
```

### Frontend Won't Start

**Error:** `npm: command not found` or modules missing

**Solution:**
```powershell
# Install Node.js first if needed
# Then:
cd frontend
npm install
npm run dev
```

### Worker Won't Connect to Supabase

**Error:** `Connection refused` or `Invalid API key`

**Solution:**
1. Check `.env` file exists in project root
2. Verify `SUPABASE_URL` and `SUPABASE_SECRET_KEY` are set
3. Ensure Supabase project is online
4. Run: `uv run python verify_startup.py`

### Port Already in Use

**Error:** `Address already in use: ('0.0.0.0', 8000)`

**Solution:**
```powershell
# Find process on port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or use different port
uv run python -m uvicorn backend.main:app --port 8001
```

### Tests Fail

**Error:** Assertions failing or timeout

**Solution:**
```powershell
# Check all services are running in other terminals first
# Then run test with verbose output
uv run python full_lifecycle_test.py

# Or check individual service health
uv run python verify_startup.py
```

---

## 🎯 What Each Service Does

### Backend (Port 8000)
- **Framework:** FastAPI with Uvicorn
- **Purpose:** REST API for client requests
- **Key Endpoints:**
  - `POST /api/ingest` - Ingest patient data
  - `GET /api/patient/{id}` - Retrieve patient
  - `POST /api/approve` - Admin approval

### Frontend (Port 3000)
- **Framework:** Next.js 16 with Webpack
- **Purpose:** User dashboard and admin panel
- **Features:**
  - Patient search interface
  - Conflict resolution panel
  - Audit trail viewer

### Worker (Background Process)
- **Framework:** Python asyncio
- **Purpose:** Process staging records and generate FHIR
- **Features:**
  - Polls `staging_vault` every 5 seconds
  - Falls back to Cloud LLM if local unavailable
  - Detects clinical conflicts
  - Records audit trails

---

## 📊 Environment Variables

The `.env` file should contain:

```env
SUPABASE_URL=https://cdgcmcznmqykmzyovnmn.supabase.co
SUPABASE_SECRET_KEY=****
GROQ_API_KEY=****
DATABASE_URL=postgresql://...
```

---

## ✅ Verification Checklist

- [ ] Terminal 1: Backend running on port 8000
- [ ] Terminal 2: Frontend running on port 3000
- [ ] Terminal 3: Worker processing records
- [ ] Can access http://localhost:3000
- [ ] Can access http://localhost:8000/docs
- [ ] Full lifecycle test passes (11/11 assertions)

---

## 🚀 Next Steps

1. **Verify all services start correctly** using the commands above
2. **Run the full lifecycle test** to confirm system works
3. **Access the dashboard** at http://localhost:3000
4. **Review logs** in each terminal for any errors

---

## 📞 Support

If you encounter issues:

1. Check this troubleshooting section
2. Review logs in each terminal
3. Run `uv run python verify_startup.py` for diagnostics
4. Check `.env` file configuration

---

**Status:** ✅ All services ready for production deployment

**Date:** 2026-05-17  
**Version:** 1.0.0  
**Last Updated:** 2026-05-17 02:18:00 UTC
