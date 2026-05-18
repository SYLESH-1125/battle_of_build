# 🚀 Memory Vault - Quick Start Reference

## The Three Services

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| **Frontend** | 3000 | Next.js UI (Dashboard + Admin) | ✅ Ready |
| **Backend** | 8000 | FastAPI Gateway | ✅ Ready |
| **Worker** | N/A | Python AI Processing | ✅ Ready |

---

## Fastest Way to Start (3 Commands, 3 Terminals)

### Terminal 1: Backend
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
python run_backend.py
```
✅ Expect: `INFO: Application startup complete`

### Terminal 2: Frontend
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend
npm run dev
```
✅ Expect: `✓ Ready in XXXX ms`

### Terminal 3: Worker
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
python run_worker.py
```
✅ Expect: `Starting AI Worker process...`

---

## Access Points

Once all 3 services are running:

- **Dashboard UI**: http://localhost:3000/dashboard
- **Admin Panel**: http://localhost:3000/admin
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## What's New: Complete Startup Documentation

I've created comprehensive documentation in your project:

### 📄 Files Added:

1. **`STARTUP_GUIDE.md`** (400+ lines)
   - Complete installation instructions with `uv`
   - Detailed troubleshooting guide
   - Environment setup checklist
   - Automated startup script
   - Production deployment guide

2. **`verify_startup.py`**
   - Automated health check script
   - Verifies all 3 services start correctly
   - Monitors process health
   - Auto-cleanup on error

---

## Environment Constraints Verified

✅ **DOUBLE FALLBACK MODE** - All features working:
- ❌ NO REDIS → Falls back to `staging_vault` polling
- ❌ NO LOCAL LLM → Falls back to Cloud LLM (Groq)
- ✅ Cloud LLM → Fully operational
- ✅ Supabase → REST API confirmed working

---

## Migration Status

✅ **Audit Logs Migration Applied**
- `audit_logs` table schema fully updated
- Fields added: `action`, `old_value`, `new_value`, `admin_id`
- Encryption support active in Supabase Vault

---

## Next Steps

### Option A: Automated Startup
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
python verify_startup.py
```

### Option B: Manual Startup (Recommended)
1. Follow the "Fastest Way to Start" section above
2. Open 3 PowerShell terminals
3. Run one command in each terminal
4. Wait 10 seconds for full startup

### Option C: Read Full Guide
```
cat STARTUP_GUIDE.md
```

---

## Ready for Phase 1-3 Testing?

Once all services are confirmed running on ports 3000, 8000, and worker active, proceed to:

**PHASE 1: ACT I - THE GENESIS ENCOUNTER** (New Patient Workflow)

Requirements:
- ✅ Frontend running (http://localhost:3000)
- ✅ Backend running (http://localhost:8000)
- ✅ Worker running (processing staging_vault)
- ✅ Supabase connected
- ✅ Groq API configured in .env

---

**Last Updated:** 2026-05-17  
**Document Status:** ✅ Complete and Ready for Testing
