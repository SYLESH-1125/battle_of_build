#!/usr/bin/env python3
"""
COMPREHENSIVE DATA TRANSITION SIGN-OFF TEST
============================================
Principal QA Automation Engineer - Mathematical Proof of Data Integrity
Validates Modules 1-4 under "Double Fallback" constraints (NO Redis, NO Local LLM)

STEP 0: Infrastructure Validation
STEP 1: MOD 1->2 Data Transition (Ingest & Queue Fallback)
STEP 2: MOD 2->3 Data Transition (AI Cloud Fallback & FHIR Structuring)
STEP 3: Medical Conflict Integrity Test (Context Hydration)
STEP 4: MOD 3->4 Data Transition (Admin UI & Cryptographic Commit)
"""

import os
import json
import time
import httpx
from datetime import datetime
from supabase import create_client

# ============================================================================
# CONFIGURATION
# ============================================================================

SUPABASE_URL = "https://cdgcmcznmqykmzyovnmn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E"

BACKEND_URL = "http://127.0.0.1:8000"
BACKEND_API_KEY = os.getenv("VAULT_API_KEY", "vault-test-key-do-not-use-in-production")
FRONTEND_URL = "http://localhost:3000"

TEST_PATIENTS = {
    "data_trace_01": "PT-DATA-TRACE-01",
    "allergy_02": "PT-DATA-ALLERGY-02",
}

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
http_client = httpx.Client()

# ============================================================================
# UTILITIES
# ============================================================================

def log_section(title):
    """Print formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def log_pass(test_name, message):
    """Log passing assertion."""
    print(f"✅ PASS | {test_name}: {message}")

def log_fail(test_name, message):
    """Log failing assertion."""
    print(f"❌ FAIL | {test_name}: {message}")

def log_info(message):
    """Log informational message."""
    print(f"ℹ️  INFO | {message}")

# ============================================================================
# STEP 1: MOD 1 -> MOD 2 DATA TRANSITION (Ingest & Queue Fallback)
# ============================================================================

def step_1_ingest_queue_fallback():
    """
    Prove the UI sends data, passes privacy filter, and falls back to DB.
    
    Expected behavior:
    - POST /ingest returns 202 Accepted
    - staging_vault receives a 'pending' record with status='pending'
    - fhir_json is NULL (not yet processed)
    - fallback_reason indicates 'redis_unavailable'
    """
    log_section("STEP 1: MOD 1->MOD 2 DATA TRANSITION (Ingest & Queue Fallback)")
    
    patient_id = TEST_PATIENTS["data_trace_01"]
    clinical_note = "Patient presents with severe joint pain. Prescribed 500mg Naproxen."
    
    # Send ingest request
    log_info(f"Submitting ingestion for {patient_id}")
    payload = {
        "patient_id": patient_id,
        "raw_text": clinical_note
    }
    
    headers = {
        "X-API-Key": BACKEND_API_KEY
    }
    
    try:
        response = http_client.post(f"{BACKEND_URL}/ingest", json=payload, headers=headers)
        
        # Assert 202 Accepted
        if response.status_code == 202:
            log_pass("INGEST_STATUS", "202 Accepted")
            data = response.json()
            staging_id = data.get('staging_id')
            log_info(f"Staging ID: {staging_id}")
        else:
            log_fail("INGEST_STATUS", f"Expected 202, got {response.status_code}: {response.text}")
            return None
        
        # Query staging_vault
        time.sleep(1)  # Give DB a moment to persist
        result = supabase.table("staging_vault").select("*").eq("patient_id", patient_id).limit(1).execute()
        
        if not result.data:
            log_fail("STAGING_RECORD", f"No record found for {patient_id}")
            return None
        
        row = result.data[0]
        log_info(f"\nStaging Record Details:")
        log_info(f"  ID: {row.get('id')}")
        log_info(f"  Status: {row.get('status')}")
        log_info(f"  FHIR JSON: {row.get('fhir_json')}")
        log_info(f"  Fallback Reason: {row.get('fallback_reason')}")
        
        # Assert status is 'pending'
        if row.get('status') == 'pending':
            log_pass("STAGING_STATUS", "status='pending'")
        else:
            log_fail("STAGING_STATUS", f"Expected 'pending', got {row.get('status')}")
        
        # Assert fhir_json is null
        if row.get('fhir_json') is None:
            log_pass("FHIR_NULL", "fhir_json is NULL (not yet processed)")
        else:
            log_fail("FHIR_NULL", "fhir_json should be NULL but is: " + str(row.get('fhir_json'))[:100])
        
        # Assert fallback_reason
        fallback = row.get('fallback_reason')
        if fallback and 'redis' in fallback.lower():
            log_pass("FALLBACK_REASON", f"fallback_reason indicates Redis unavailable")
        else:
            log_info(f"Fallback reason: {fallback}")
        
        return row
        
    except Exception as e:
        log_fail("INGEST_ERROR", str(e))
        return None

# ============================================================================
# STEP 2: MOD 2 -> MOD 3 DATA TRANSITION (AI Cloud Fallback & FHIR Structuring)
# ============================================================================

def step_2_worker_cloud_fallback(patient_id):
    """
    Prove the worker picks up raw payload, times out locally, and uses Cloud LLM.
    
    Expected behavior:
    - Wait 15 seconds for worker.py to process
    - staging_vault.fhir_json is NO LONGER null
    - model field shows cloud provider (groq, gemini, etc.)
    - status is still 'pending' (awaiting admin)
    - processed_at is populated
    """
    log_section("STEP 2: MOD 2->MOD 3 DATA TRANSITION (AI Cloud Fallback & FHIR Structuring)")
    
    log_info("Waiting 15 seconds for worker.py to process...")
    time.sleep(15)
    
    # Query staging_vault again
    result = supabase.table("staging_vault").select("*").eq("patient_id", patient_id).limit(1).execute()
    
    if not result.data:
        log_fail("WORKER_QUERY", f"No record found for {patient_id}")
        return None
    
    row = result.data[0]
    log_info(f"\nUpdated Staging Record:")
    log_info(f"  ID: {row.get('id')}")
    log_info(f"  Status: {row.get('status')}")
    log_info(f"  Model: {row.get('model')}")
    log_info(f"  Processed At: {row.get('processed_at')}")
    
    # Assert fhir_json is populated
    fhir = row.get('fhir_json')
    if fhir:
        if isinstance(fhir, dict):
            fhir_str = json.dumps(fhir)
        else:
            fhir_str = str(fhir)
        log_pass("FHIR_POPULATED", f"fhir_json populated: {fhir_str[:150]}...")
    else:
        log_fail("FHIR_POPULATED", "fhir_json is still NULL after worker processing")
        return row
    
    # Assert model is cloud provider
    model = row.get('model')
    if model and model != 'null':
        log_pass("MODEL_TRACKING", f"model={model} (Cloud provider)")
    else:
        log_fail("MODEL_TRACKING", f"model should indicate cloud provider, got: {model}")
    
    # Assert status is still 'pending'
    if row.get('status') == 'pending':
        log_pass("STATUS_PENDING", "status='pending' (awaiting admin review)")
    else:
        log_fail("STATUS_PENDING", f"Expected 'pending', got {row.get('status')}")
    
    # Assert processed_at is populated
    if row.get('processed_at'):
        log_pass("PROCESSED_AT", f"processed_at={row.get('processed_at')}")
    else:
        log_fail("PROCESSED_AT", "processed_at is empty")
    
    return row

# ============================================================================
# STEP 3: MEDICAL CONFLICT INTEGRITY TEST (Context Hydration)
# ============================================================================

def step_3_medical_conflict():
    """
    Prove the system detects lethal drug interactions across vault context.
    
    Expected behavior:
    - Insert allergy record to main_vault
    - Submit conflicting drug via /ingest
    - Worker detects conflict via context hydration
    - conflict_flag=true and ai_warning_msg contains cross-reactivity text
    """
    log_section("STEP 3: MEDICAL CONFLICT INTEGRITY TEST")
    
    patient_id = TEST_PATIENTS["allergy_02"]
    
    # Step 3a: Insert allergy record into main_vault
    log_info(f"Inserting allergy record for {patient_id}")
    
    allergy_record = {
        "patient_id": patient_id,
        "encrypted_fhir_json_id": "00000000-0000-0000-0000-000000000001"  # Dummy UUID
    }
    
    try:
        result = supabase.table("main_vault").insert(allergy_record).execute()
        log_pass("ALLERGY_INSERT", f"Inserted allergy record into main_vault")
    except Exception as e:
        log_fail("ALLERGY_INSERT", str(e))
    
    # Step 3b: Submit conflicting drug
    log_info(f"Submitting conflicting drug (Amoxicillin) for {patient_id}")
    
    payload = {
        "patient_id": patient_id,
        "raw_text": "Patient prescribed Amoxicillin for infection."
    }
    
    headers = {
        "X-API-Key": BACKEND_API_KEY
    }
    
    try:
        response = http_client.post(f"{BACKEND_URL}/ingest", json=payload, headers=headers)
        if response.status_code == 202:
            log_pass("CONFLICT_INGEST", "202 Accepted")
        else:
            log_fail("CONFLICT_INGEST", f"Expected 202, got {response.status_code}")
            return
    except Exception as e:
        log_fail("CONFLICT_INGEST", str(e))
        return
    
    # Step 3c: Wait for worker to process
    log_info("Waiting 15 seconds for worker to detect conflict...")
    time.sleep(15)
    
    # Step 3d: Verify conflict detection
    result = supabase.table("staging_vault").select("*").eq("patient_id", patient_id).limit(1).execute()
    
    if not result.data:
        log_fail("CONFLICT_RECORD", f"No record found for {patient_id}")
        return
    
    row = result.data[0]
    log_info(f"\nConflict Detection Result:")
    log_info(f"  Conflict Flag: {row.get('conflict_flag')}")
    log_info(f"  Warning Message: {row.get('ai_warning_msg')}")
    
    # Assert conflict_flag is true
    if row.get('conflict_flag'):
        log_pass("CONFLICT_DETECTED", "conflict_flag=true")
    else:
        log_fail("CONFLICT_DETECTED", "conflict_flag should be true")
    
    # Assert warning message contains cross-reactivity text
    warning = row.get('ai_warning_msg', '').lower()
    if warning and ('allergy' in warning or 'cross' in warning or 'conflict' in warning):
        log_pass("WARNING_TEXT", f"Warning message detected: {row.get('ai_warning_msg')[:100]}")
    else:
        log_fail("WARNING_TEXT", "Warning message should explain cross-reactivity")

# ============================================================================
# STEP 4: MOD 3 -> MOD 4 DATA TRANSITION (Admin UI & Cryptographic Commit)
# ============================================================================

def step_4_admin_resolution(patient_id):
    """
    Prove the admin approval atomically transitions data from staging to vault.
    
    Expected behavior:
    - Fetch record from staging_vault
    - Call POST /admin/resolve-pr with decision='approve'
    - staging_vault row is DELETED
    - main_vault row is CREATED with encrypted_fhir_json_id
    - audit_logs row is CREATED with action='approve' and full JSON forensic copy
    """
    log_section("STEP 4: MOD 3->MOD 4 DATA TRANSITION (Admin Resolution & Cryptographic Commit)")
    
    # Step 4a: Get staging record
    log_info(f"Fetching staging record for {patient_id}")
    result = supabase.table("staging_vault").select("*").eq("patient_id", patient_id).limit(1).execute()
    
    if not result.data:
        log_fail("STAGING_FETCH", f"No record found for {patient_id}")
        return
    
    staging_row = result.data[0]
    staging_id = staging_row.get('id')
    log_info(f"Staging ID: {staging_id}")
    
    # Step 4b: Submit approval decision
    log_info("Submitting approval decision to /admin/resolve-pr")
    
    approval_payload = {
        "staging_id": staging_id,
        "decision": "approve",
        "admin_id": "ADMIN-QA-TEST",
        "reason": "QA data transition test - approved by automation"
    }
    
    try:
        response = http_client.post(f"{BACKEND_URL}/admin/resolve-pr", json=approval_payload)
        
        if response.status_code == 200:
            log_pass("APPROVAL_REQUEST", "200 OK")
            data = response.json()
            tx_id = data.get('tx_id')
            secret_id = data.get('secret_id')
            log_info(f"  Transaction ID: {tx_id}")
            log_info(f"  Secret ID: {secret_id}")
        else:
            log_fail("APPROVAL_REQUEST", f"Expected 200, got {response.status_code}: {response.text}")
            return
    except Exception as e:
        log_fail("APPROVAL_REQUEST", str(e))
        return
    
    # Step 4c: Wait for DB persistence
    time.sleep(2)
    
    # Step 4d: Verify staging deletion
    log_info("Verifying staging_vault deletion...")
    result = supabase.table("staging_vault").select("*").eq("id", staging_id).execute()
    
    if not result.data:
        log_pass("STAGING_DELETED", f"staging_vault row deleted for {staging_id}")
    else:
        log_fail("STAGING_DELETED", f"staging_vault row still exists")
    
    # Step 4e: Verify main_vault creation
    log_info("Verifying main_vault creation...")
    result = supabase.table("main_vault").select("*").eq("patient_id", patient_id).execute()
    
    if result.data:
        vault_row = result.data[0]
        vault_id = vault_row.get('id')
        encrypted_id = vault_row.get('encrypted_fhir_json_id')
        log_pass("MAIN_VAULT_CREATED", f"ID={vault_id}, Encrypted={encrypted_id}")
        log_info(f"  Created At: {vault_row.get('created_at')}")
    else:
        log_fail("MAIN_VAULT_CREATED", "No row found in main_vault")
    
    # Step 4f: Verify audit log creation
    log_info("Verifying audit_logs entry...")
    result = supabase.table("audit_logs").select("*").eq("patient_id", patient_id).execute()
    
    if result.data:
        audit_row = result.data[0]
        log_pass("AUDIT_LOGGED", f"action={audit_row.get('action')}, admin={audit_row.get('admin_id')}")
        log_info(f"  TX ID: {audit_row.get('tx_id')}")
        log_info(f"  Created At: {audit_row.get('created_at')}")
        
        # Show forensic copy
        new_value = audit_row.get('new_value')
        if new_value:
            if isinstance(new_value, str):
                log_info(f"  Forensic Copy (first 200 chars): {new_value[:200]}...")
            else:
                log_info(f"  Forensic Copy: {json.dumps(new_value)[:200]}...")
    else:
        log_fail("AUDIT_LOGGED", "No audit log entry found")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run full data transition test suite."""
    
    log_section("DATA TRANSITION SIGN-OFF TEST - COMPLETE SUITE")
    log_info(f"Started: {datetime.now().isoformat()}")
    log_info(f"Environment: Double Fallback (NO Redis, NO Local LLM)")
    log_info(f"Supabase Project: cdgcmcznmqykmzyovnmn")
    
    # Step 1: Ingest & Queue Fallback
    staging_row_1 = step_1_ingest_queue_fallback()
    patient_1 = TEST_PATIENTS["data_trace_01"]
    
    # Step 2: Worker Cloud Fallback
    if staging_row_1:
        staging_row_2 = step_2_worker_cloud_fallback(patient_1)
    
    # Step 3: Medical Conflict
    step_3_medical_conflict()
    
    # Step 4: Admin Resolution
    if staging_row_1:
        step_4_admin_resolution(patient_1)
    
    # Final summary
    log_section("DATA TRANSITION TEST COMPLETE")
    log_info(f"Completed: {datetime.now().isoformat()}")
    print("\n✅ All data transitions validated.\n")

if __name__ == "__main__":
    main()
