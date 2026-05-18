# 🔐 User Provisioning Guide - Pre-Provisioned Model

## Architecture

This authentication system uses **Pre-Provisioned Only** model:

- ❌ NO public signup button
- ✅ Users must be manually created by administrator in Supabase
- ✅ All users (doctors, admins, patients) are created with their role pre-assigned
- ✅ Users simply login with their email using the passwordless OTP flow

---

## How to Create Test Users

### Option 1: Supabase Dashboard (Recommended for Quick Setup)

1. Go to [Supabase Dashboard](https://app.supabase.com) → Your Project
2. Navigate to **Authentication** → **Users**
3. Click **Create user**
4. Fill in the form:
   - **Email**: `doctor@hospital.com` (use unique emails)
   - **Password**: Leave empty (we use passwordless OTP)
   - **User Metadata**: Add role as JSON:
     ```json
     {
       "role": "doctor"
     }
     ```
5. Click **Create user**
6. The user can now login by entering their email on the login page and verifying the 6-digit PIN sent to their email

---

### Option 2: Supabase SQL (For Bulk User Creation)

Use the Supabase SQL Editor to insert users directly into `auth.users`:

```sql
-- Create a doctor user
INSERT INTO auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at,
  raw_user_meta_data,
  is_super_admin,
  confirmation_token,
  confirmation_sent_at,
  recovery_token,
  recovery_sent_at
) VALUES (
  '00000000-0000-0000-0000-000000000000',
  gen_random_uuid(),
  'authenticated',
  'authenticated',
  'doctor@hospital.com',
  crypt('', gen_salt('bf')),
  NOW(),
  NOW(),
  NOW(),
  jsonb_build_object('role', 'doctor'),
  FALSE,
  '',
  NULL,
  '',
  NULL
);

-- The trigger handle_new_user will automatically create a user_roles entry
-- with role='doctor' within 100ms
```

**Note**: This requires direct database access and manual UUID/hashing, so the dashboard method is usually simpler.

---

## Test User Setup (Recommended for Demo)

Create these three test users in your Supabase Dashboard:

### 1. Admin User
- **Email**: `admin@memory-vault.hospital`
- **Metadata Role**: `admin`
- **Access**: `/admin` portal

### 2. Doctor User
- **Email**: `doctor@memory-vault.hospital`
- **Metadata Role**: `doctor`
- **Access**: `/dashboard` portal

### 3. Patient User
- **Email**: `patient@memory-vault.hospital`
- **Metadata Role**: `patient`
- **Access**: `/patient` portal

---

## How the Provisioning Works

### When a User Logs In:

1. User enters email + selects role on login page
2. System sends 6-digit PIN to user's email (via Supabase Auth)
3. User verifies PIN (OTP)
4. Middleware checks:
   - Is user authenticated? ✅
   - Does user_roles table have an entry for this user? ✅ (created by trigger when user was first provisioned)
   - Does user role match required route role? ✅
5. User is routed to their portal:
   - Admin → `/admin`
   - Doctor → `/dashboard`
   - Patient → `/patient`

### Automatic Role Assignment:

When a new user is created in `auth.users`:
- PostgreSQL trigger `handle_new_user` fires automatically
- Reads `raw_user_meta_data.role` from auth.users
- Inserts entry into `user_roles` table with that role
- If role is not specified, defaults to `'patient'`

---

## Example: Creating a Test User Manually

### Step-by-Step in Supabase Dashboard:

1. Open [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to **Authentication** → **Users**
4. Click **Create user** button
5. Enter email: `testdoctor@hospital.com`
6. Leave password empty (we use OTP)
7. Click **User Metadata** tab
8. Add this JSON:
   ```json
   {
     "role": "doctor"
   }
   ```
9. Click **Create user**

### Testing the Login:

1. Open your app at `http://localhost:3000`
2. Enter email: `testdoctor@hospital.com`
3. Select role: "Doctor / Clinician"
4. Click "Send Secure OTP"
5. Check your email for the 6-digit PIN
6. Enter PIN on the verification screen
7. You should be redirected to `/dashboard`

---

## Database Schema Reference

### user_roles table

```sql
CREATE TABLE user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('doctor', 'admin', 'patient')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Trigger Function: handle_new_user()

```sql
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER SECURITY DEFINER SET search_path = public
LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO public.user_roles (user_id, role)
  VALUES (NEW.id, COALESCE(NEW.raw_user_meta_data->>'role', 'patient'));
  RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION handle_new_user();
```

---

## Troubleshooting

### User created but can't login
- ✅ Check that email is correct
- ✅ Check user_roles table has an entry for this user
- ✅ Check metadata has `"role"` field

### Middleware redirects to /unauthorized
- ✅ Check user_roles table for correct role
- ✅ Verify role matches the protected route (admin, doctor, patient)

### OTP not being sent
- ✅ Check Supabase Auth settings → SMTP Configuration
- ✅ Verify email address is valid
- ✅ Check email spam folder

### Database trigger not firing
- ✅ Run: `SELECT * FROM user_roles` to verify entries exist
- ✅ Check PostgreSQL function logs in Supabase Dashboard

---

## API Reference: User Provisioning Endpoints

Currently, this system does NOT expose user creation endpoints (pre-provisioned only).

To add users programmatically in the future, you would use Supabase Admin SDK:

```typescript
import { createClient } from '@supabase/supabase-js';

const admin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY! // Service role (server-side only)
);

// Create a new doctor user
const { data, error } = await admin.auth.admin.createUser({
  email: 'newdoctor@hospital.com',
  user_metadata: {
    role: 'doctor',
  },
  email_confirm: true, // Skip email verification
});
```

This requires backend integration (not part of frontend authentication).

---

## Security Notes

✅ **This model is secure for healthcare because:**
- No random signups (role cannot be claimed, only assigned)
- Admin fully controls who gets which access level
- All auth uses Supabase Auth (industry-standard security)
- Passwordless OTP reduces password compromise risk
- RLS policies ensure users can only see their own role

⚠️ **Production Considerations:**
- Add approval workflow for doctor/admin roles (manual review)
- Implement MFA for admin users specifically
- Add audit logging for user provisioning actions
- Use SSO integration (SAML/OpenID) for hospital AD/LDAP

---

## Next Steps

1. ✅ Create 3 test users in Supabase Dashboard
2. ✅ Test login flow with each role
3. ✅ Verify you're routed to correct portal
4. ✅ Test role-based access (try accessing /admin as patient)
5. ✅ Test logout flow

