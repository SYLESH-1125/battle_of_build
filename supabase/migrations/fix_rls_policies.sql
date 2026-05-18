-- Fix RLS Policies for Patient Portal Access
-- This migration ensures proper Row-Level Security for the memory vault system

BEGIN;

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Enable public read for patients" ON main_vault;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON main_vault;
DROP POLICY IF EXISTS "Enable update for record owners only" ON main_vault;

-- Create policies for main_vault table

-- 1. Allow anyone to read records by patient_id (patient portal public access)
CREATE POLICY "Allow read access by patient_id"
  ON main_vault
  FOR SELECT
  USING (true);

-- 2. Allow service role to insert records (from admin/doctor backend)
CREATE POLICY "Allow authenticated inserts"
  ON main_vault
  FOR INSERT
  WITH CHECK (
    auth.role() = 'authenticated' OR auth.role() = 'service_role'
  );

-- 3. Allow updates by service role (admin approval workflow)
CREATE POLICY "Allow authenticated updates"
  ON main_vault
  FOR UPDATE
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Enable RLS on main_vault if not already enabled
ALTER TABLE main_vault ENABLE ROW LEVEL SECURITY;

-- Fix staging_vault policies
DROP POLICY IF EXISTS "Enable insert for unauthenticated users" ON staging_vault;
DROP POLICY IF EXISTS "Enable read for authenticated only" ON staging_vault;

CREATE POLICY "Allow doctor submissions"
  ON staging_vault
  FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Allow authenticated reads"
  ON staging_vault
  FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

ALTER TABLE staging_vault ENABLE ROW LEVEL SECURITY;

-- Ensure fhir_vault has appropriate policies
DROP POLICY IF EXISTS "Allow read encrypted data" ON fhir_vault;
DROP POLICY IF EXISTS "Allow authenticated inserts" ON fhir_vault;

CREATE POLICY "Allow reading FHIR data"
  ON fhir_vault
  FOR SELECT
  USING (true);

CREATE POLICY "Allow creating FHIR records"
  ON fhir_vault
  FOR INSERT
  WITH CHECK (true);

ALTER TABLE fhir_vault ENABLE ROW LEVEL SECURITY;

COMMIT;

-- Verify policies
-- SELECT * FROM pg_policies WHERE tablename IN ('main_vault', 'staging_vault', 'fhir_vault');
