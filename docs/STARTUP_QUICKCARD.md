# 🎯 3-TERMINAL STARTUP QUICK CARD

## Copy & Paste These Commands

### Terminal 1: Backend ✅ (RUNNING NOW)
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
✅ **Keep this terminal open - Backend running on port 8000**

---

### Terminal 2: Frontend (COPY & PASTE THIS)
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\frontend
npm run dev
```
✅ **Frontend will run on port 3000**

---

### Terminal 3: Worker (COPY & PASTE THIS)
```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python run_worker.py
```
✅ **Worker will process records in background**

---

## 🌐 Access Points

Once all three terminals show successful startup:

- **Dashboard:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **Admin Panel:** http://localhost:3000/admin

---

## ✅ Verification

Check all three are working:

```powershell
# Backend health
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000

# Run test
uv run python full_lifecycle_test.py
```

Expected: All respond with 200 OK and test shows 11/11 passed ✅

---

## 🧪 Test Full Lifecycle

```powershell
cd C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono
uv run python full_lifecycle_test.py
```

Expected output:
```
✅ PHASE 1: Patient Genesis - PASSED (6/6)
✅ PHASE 2: Conflict Detection - PASSED (3/3)
✅ PHASE 3: Admin Override - PASSED (2/2)

OVERALL: 11/11 assertions passed ✅
```

---

## 🛑 Stopping Everything

To stop all services:
- Terminal 1: Press `Ctrl+C` 
- Terminal 2: Press `Ctrl+C`
- Terminal 3: Press `Ctrl+C`

---

**Status:** Backend ✅ RUNNING  
**Next:** Open Terminal 2 and Terminal 3, then paste the commands above

All files ready in:  
`C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono\`
