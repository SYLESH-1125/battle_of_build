# ⚡ Quick Start: Test the Production Auth System

**You've successfully upgraded to production Supabase Auth! Here's how to test it immediately.**

---

## 🚀 In 5 Minutes

### 1. Create Test Users

Go to [Supabase Dashboard](https://app.supabase.com):

1. Select your project
2. Click **Authentication** → **Users**
3. Click **Create user**
4. Create these 3 users:

**User 1: Doctor**
- Email: `doctor@hospital.com`
- Password: Leave empty
- User Metadata:
  ```json
  { "role": "doctor" }
  ```

**User 2: Admin**
- Email: `admin@hospital.com`
- Password: Leave empty
- User Metadata:
  ```json
  { "role": "admin" }
  ```

**User 3: Patient**
- Email: `patient@hospital.com`
- Password: Leave empty
- User Metadata:
  ```json
  { "role": "patient" }
  ```

### 2. Start Your Servers

```bash
# Terminal 1: Backend
cd backend
python run_backend.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 3. Test Login

Open http://localhost:3000

**Test Flow:**
```
1. Enter: doctor@hospital.com
2. Select: Doctor / Clinician
3. Click: Send Secure OTP
4. Check your email for 6-digit PIN
5. Enter PIN
6. Press: Verify PIN
7. Should redirect to: /dashboard
```

---

## ✅ Expected Results

### Test User: Doctor

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Visit `/` | See login page |
| 2 | Enter `doctor@hospital.com` | Email field populated |
| 3 | Select "Doctor / Clinician" | Role dropdown shows selection |
| 4 | Click "Send Secure OTP" | See message "PIN sent to..." |
| 5 | Enter 6-digit PIN | Enable "Verify PIN" button |
| 6 | Click "Verify PIN" | Redirect to `/dashboard` |
| 7 | Refresh page | Remain on `/dashboard` (session persists) |

### Test User: Admin

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as `admin@hospital.com` | Redirect to `/admin` |
| 2 | Try accessing `/dashboard` | Redirect to `/unauthorized` |
| 3 | Try accessing `/patient` | Redirect to `/unauthorized` |

### Test User: Patient

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Login as `patient@hospital.com` | Redirect to `/patient` |
| 2 | Try accessing `/admin` | Redirect to `/unauthorized` |
| 3 | Try accessing `/dashboard` | Redirect to `/unauthorized` |

---

## 🔍 Key Test Scenarios

### Scenario 1: Correct Role Access ✅
```
Doctor visits /dashboard → Should show dashboard
Doctor has doctor role → Middleware allows access
```

### Scenario 2: Unauthorized Access ❌
```
Patient visits /admin → Middleware checks role
Patient has patient role, route needs admin → Redirect to /unauthorized
```

### Scenario 3: Session Persistence ✅
```
Doctor logs in → Session created
Doctor refreshes page → Middleware finds session
Middleware queries user_roles → Finds doctor role
Doctor stays on /dashboard
```

### Scenario 4: Login Failure ❌
```
User enters wrong PIN → Show error "Invalid PIN"
User enters invalid email → Show error "Invalid email format"
User enters non-existent email → Supabase returns error
```

---

## 📚 Detailed Docs

For more details, see:

- **User Provisioning**: `/frontend/docs/USER_PROVISIONING_GUIDE.md`
- **Architecture**: `/AUTHENTICATION_UPGRADE_COMPLETE.md`
- **Phase 3 Details**: `/PHASE_3_COMPLETION_REPORT.md`

---

## 🆘 Troubleshooting

### Problem: "User not found" when trying to login
**Solution**: User must exist in Supabase. Create them in Dashboard (see step 1 above).

### Problem: PIN not arriving in email
**Solution**: Check spam folder. If still not there, check Supabase Auth SMTP settings.

### Problem: Logged in but redirected to /unauthorized
**Solution**: Check that user_roles table has an entry for this user. See USER_PROVISIONING_GUIDE.md.

### Problem: Refreshing page logs me out
**Solution**: Session might be stored only in memory. Check browser console for errors.

---

## 🎯 Next Actions

1. ✅ **Now**: Create 3 test users
2. ✅ **Now**: Test each login scenario
3. ✅ **Now**: Verify role-based access
4. 📋 **Later**: Test with real email addresses (OTP actually sent)
5. 📋 **Later**: Deploy to staging environment
6. 📋 **Later**: Set up production SMTP configuration

---

## 🏁 Done!

You now have a production-grade authentication system with:

✅ Passwordless Email OTP  
✅ Role-Based Access Control  
✅ Automatic User Provisioning  
✅ Session Management  
✅ Route Protection  
✅ Healthcare-Compliant User Model  

**Test it out! Visit http://localhost:3000**

