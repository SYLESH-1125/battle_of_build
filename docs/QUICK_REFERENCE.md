# 🎯 QUICK START REFERENCE

## Start All Services (3 Terminals)

```bash
# Terminal 1: Backend
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_backend.py

# Terminal 2: Frontend  
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend
npm run dev

# Terminal 3: Worker
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_worker.py
```

---

## Access Portals

| Portal | URL | Purpose |
|--------|-----|---------|
| Doctor | http://localhost:3000/dashboard | Submit clinical notes |
| Admin | http://localhost:3000/admin | Review & approve |
| Patient | http://localhost:3000/patient | Access vault & QR |
| Backend | http://127.0.0.1:8000 | FastAPI endpoints |

---

## Test Data

**Use this Patient ID**: `PT-LIFECYCLE-MASTER-01`

**Sample Clinical Note**:
```
Chief Complaint: Hypertension follow-up
History: 56-year-old male with hypertension and type 2 diabetes
Current Meds: Lisinopril 10mg daily, Metformin 500mg BID
Plan: Increase Lisinopril to 20mg, add Amlodipine 5mg
```

---

## Run Tests

```bash
# Integration Test (Python)
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python full_lifecycle_test.py

# E2E Tests (Playwright)
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend
npx playwright test
```

---

## Key Features

✅ Real-time queue updates  
✅ AI conflict detection  
✅ QR code generation  
✅ Atomic transitions  
✅ Audit trails  
✅ Zero-knowledge security  

---

## Workflow (3-5 minutes)

1. **Doctor**: Go to `/dashboard`, submit clinical note with patient ID
2. **Wait**: 5-20 seconds (worker processing + LLM)
3. **Admin**: Go to `/admin`, see record in queue, click Approve
4. **Patient**: Go to `/patient`, enter patient ID, see QR code
5. **Download**: Click "Download QR" to save as PNG

---

## Troubleshooting

**Issue**: Worker not processing records
- Check: `npm run dev` is running frontend (worker uses it for polling)
- Check: Supabase connectivity (`uv run python test_backend_init.py`)
- Check: Redis not required (using polling fallback)

**Issue**: Admin queue empty
- Check: Patient ID matches exactly (case-insensitive)
- Check: Record status is "processed" (not "pending" or "processing")
- Refresh: Click refresh button in admin UI

**Issue**: QR not generating
- Check: Patient found in main_vault (approved records only)
- Check: `qrcode.react` installed (`npm install qrcode.react`)
- Try: Reload browser page

---

## Files to Monitor

- Backend logs: Check terminal where `uv run python run_backend.py` runs
- Worker logs: Check terminal where `uv run python run_worker.py` runs
- Frontend logs: Check terminal where `npm run dev` runs
- Database: Supabase console (https://app.supabase.com)

---

## Key Endpoints

```
POST /admin/resolve-pr        # Admin approval/rejection
GET  /main_vault (Supabase)   # Patient vault query
GET  /staging_vault (Supabase) # Admin queue
```

---

**Everything is connected. All services are monitored. Go test! 🚀**

---

## One-Minute Quick Test

```bash
# Open 3 terminals

# T1
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_backend.py

# T2
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend
npm run dev

# T3
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_worker.py

# Then visit http://localhost:3000/dashboard
# Submit a note, wait 20s, check /admin, approve, check /patient
```

---

Last Updated: 2026-05-17  
Status: ✅ Production Ready
