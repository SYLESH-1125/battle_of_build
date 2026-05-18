-- Migration: Add conflict detection fields to staging_vault, fhir_json to main_vault
-- Date: 2026-05-18

BEGIN;

-- staging_vault: conflict detection fields
ALTER TABLE staging_vault
  ADD COLUMN IF NOT EXISTS conflict_flag boolean DEFAULT false;

ALTER TABLE staging_vault
  ADD COLUMN IF NOT EXISTS ai_warning_msg text;

-- staging_vault: processed_at timestamp for admin queue ordering
ALTER TABLE staging_vault
  ADD COLUMN IF NOT EXISTS processed_at timestamptz DEFAULT now();

-- main_vault: store actual FHIR JSON for context hydration
ALTER TABLE main_vault
  ADD COLUMN IF NOT EXISTS fhir_json jsonb;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_staging_vault_conflict ON staging_vault(conflict_flag) WHERE conflict_flag = true;
CREATE INDEX IF NOT EXISTS idx_main_vault_patient_fhir ON main_vault(patient_id, created_at DESC);

COMMIT;
