-- Migration: Add audit_logs forensic fields and main_vault encrypted_fhir_json_id
-- Date: 2026-05-17
-- Purpose: Support Module 4 - Admin Resolution & Cryptographic Commit

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create audit_logs table if missing with forensic fields
CREATE TABLE IF NOT EXISTS audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tx_id uuid NOT NULL DEFAULT gen_random_uuid(),
  staging_id uuid,
  admin_id varchar,
  action text,
  old_value jsonb,
  new_value jsonb,
  secret_id uuid,
  reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- If table pre-exists, add missing columns safely
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS tx_id uuid DEFAULT gen_random_uuid();
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS staging_id uuid;
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS admin_id varchar;
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS action text;
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS old_value jsonb;
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS new_value jsonb;
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS secret_id uuid;
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS reason text;
ALTER TABLE audit_logs
  ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();

-- Ensure main_vault has encrypted_fhir_json_id
ALTER TABLE main_vault
  ADD COLUMN IF NOT EXISTS encrypted_fhir_json_id uuid;

-- Indexes for performance and lookups
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at desc);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tx_id ON audit_logs(tx_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_staging_id ON audit_logs(staging_id);
CREATE INDEX IF NOT EXISTS idx_main_vault_encrypted_id ON main_vault(encrypted_fhir_json_id);

COMMIT;
