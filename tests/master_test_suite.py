#!/usr/bin/env python3
"""
PRINCIPAL QA AUTOMATION ENGINEER - COMPREHENSIVE MASTER TEST SUITE
Complete End-to-End Data Transition Verification (Modules 1-4)

This script:
1. Validates infrastructure and environment
2. Runs STEP 1: Ingest → Staging verification  
3. Runs STEP 2: Worker → FHIR generation
4. Runs STEP 3: Conflict detection
5. Runs STEP 4: Admin approval → Vault commit
6. Generates comprehensive sign-off report
"""

import asyncio
import json
import os
import sys
import time
import subprocess
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Load environment
env_vars = {}
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env_vars[k] = v
                os.environ[k] = v

SUPABASE_URL = env_vars.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = env_vars.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
SUPABASE_SECRET = env_vars.get("SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SECRET_KEY"))
BACKEND_API_KEY = env_vars.get("VAULT_API_KEY", "vault-test-key-do-not-use-in-production")

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"

# Test patient IDs
PT_TRACE = "PT-DATA-TRACE-MASTER-01"
PT_ALLERGY = "PT-DATA-ALLERGY-MASTER-02"

# Headers for Supabase REST API
SUPABASE_HEADERS = {
    "apikey": SUPABASE_SECRET or SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_SECRET or SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Test results tracking
test_results = {
    "step1": {"pass": 0, "fail": 0, "assertions": []},
    "step2": {"pass": 0, "fail": 0, "assertions": []},
    "step3": {"pass": 0, "fail": 0, "assertions": []},
    "step4": {"pass": 0, "fail": 0, "assertions": []},
}

# ==============================================================================
# LOGGING
# ==============================================================================

class Log:
    @staticmethod
    def section(title: str):
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}")
    
    @staticmethod
    def info(msg: str):
        print(f"ℹ️  {msg}")
    
    @staticmethod
    def pass_assert(step: str, assertion: str):
        print(f"✅ PASS | {assertion}")
        test_results[step]["pass"] += 1
        test_results[step]["assertions"].append(f"✅ {assertion}")
    
    @staticmethod
    def fail_assert(step: str, assertion: str, details: str = ""):
        print(f"❌ FAIL | {assertion}")
        if details:
            print(f"     {details}")
        test_results[step]["fail"] += 1
        test_results[step]["assertions"].append(f"❌ {assertion}")

# ==============================================================================
# SUPABASE REST API QUERIES
# ==============================================================================

async def query_table(table: str, patient_id: str) -> Optional[Dict[str, Any]]:
    """Query any table for patient"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{SUPABASE_URL}/rest/v1/{table}"
            params = {"patient_id": f"eq.{patient_id}", "select": "*", "limit": "1"}
            resp = await client.get(url, params=params, headers=SUPABASE_HEADERS)
            
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[-1]  # Latest record
        return None
    except Exception as e:
        Log.info(f"Query error: {e}")
        return None

async def insert_record(table: str, record: Dict) -> bool:
    """Insert record into table"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{SUPABASE_URL}/rest/v1/{table}"
            resp = await client.post(url, json=record, headers=SUPABASE_HEADERS)
            return resp.status_code in [200, 201]
    except Exception as e:
        Log.info(f"Insert error: {e}")
        return False

def print_json(data: Dict, title: str):
    """Print JSON pretty"""
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, default=str))

# ==============================================================================
# STEP 1: INGEST & STAGING
# ==============================================================================

async def step1_ingest_staging():
    """STEP 1: Verify ingest and staging creation"""
    Log.section("STEP 1: MOD 1→2 - INGEST & STAGING CREATION")
    
    step = "step1"
    
    # Submit ingestion
    Log.info(f"Submitting ingestion for {PT_TRACE}...")
    payload = {
        "patient_id": PT_TRACE,
        "raw_text": "Patient presents with severe joint pain. Prescribed 500mg Naproxen for inflammation treatment."
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/ingest",
                json=payload,
                headers={"X-API-Key": BACKEND_API_KEY},
                timeout=10
            )
            
            if resp.status_code == 202:
                Log.pass_assert(step, f"INGEST_ACCEPTED (HTTP {resp.status_code})")
            else:
                Log.fail_assert(step, f"INGEST_ACCEPTED", f"Got HTTP {resp.status_code}")
                return None
    except Exception as e:
        Log.fail_assert(step, "INGEST_SUBMITTED", str(e))
        return None
    
    # Wait for DB insert
    await asyncio.sleep(3)
    
    # Query staging
    staging = await query_table("staging_vault", PT_TRACE)
    if not staging:
        Log.fail_assert(step, "STAGING_CREATED", "Record not found")
        return None
    
    print_json(staging, "STAGING_VAULT RECORD AT STEP 1")
    
    staging_id = staging.get("id")
    
    # Verify assertions
    if staging.get("patient_id") == PT_TRACE:
        Log.pass_assert(step, "PATIENT_ID_MATCHES")
    else:
        Log.fail_assert(step, "PATIENT_ID_MATCHES")
    
    if staging.get("status") == "pending":
        Log.pass_assert(step, "STATUS_PENDING")
    else:
        Log.fail_assert(step, "STATUS_PENDING", f"Got: {staging.get('status')}")
    
    if staging.get("fhir_json") is None:
        Log.pass_assert(step, "FHIR_NULL_BEFORE_PROCESSING")
    else:
        Log.fail_assert(step, "FHIR_NULL_BEFORE_PROCESSING")
    
    if "redis_unavailable" in str(staging.get("fallback_reason", "")):
        Log.pass_assert(step, "FALLBACK_REASON_REDIS")
    else:
        Log.fail_assert(step, "FALLBACK_REASON_REDIS", f"Got: {staging.get('fallback_reason')}")
    
    return (staging_id, staging)

# ==============================================================================
# STEP 2: WORKER PROCESSING
# ==============================================================================

async def step2_worker_processing():
    """STEP 2: Verify worker processing and FHIR generation"""
    Log.section("STEP 2: MOD 2→3 - WORKER PROCESSING & FHIR GENERATION")
    
    step = "step2"
    
    Log.info(f"Waiting 15 seconds for worker processing (3s local timeout → cloud fallback)...")
    await asyncio.sleep(15)
    
    # Query staging again
    staging = await query_table("staging_vault", PT_TRACE)
    if not staging:
        Log.fail_assert(step, "STAGING_UPDATED", "Record disappeared")
        return None
    
    print_json(staging, "STAGING_VAULT RECORD AFTER PROCESSING")
    
    # Verify FHIR
    fhir = staging.get("fhir_json")
    if fhir is not None and isinstance(fhir, dict):
        Log.pass_assert(step, "FHIR_JSON_POPULATED")
        
        if fhir.get("resourceType") == "Bundle" and "entry" in fhir:
            Log.pass_assert(step, "FHIR_BUNDLE_VALID")
        else:
            Log.fail_assert(step, "FHIR_BUNDLE_VALID", f"Got: {fhir.get('resourceType')}")
    else:
        Log.fail_assert(step, "FHIR_JSON_POPULATED")
    
    # Verify model
    model = staging.get("model")
    if model in ["rule-based", "groq", "gemini"]:
        Log.pass_assert(step, f"MODEL_TRACKING ({model})")
    else:
        Log.fail_assert(step, "MODEL_TRACKING", f"Got: {model}")
    
    # Verify processed_at
    if staging.get("processed_at"):
        Log.pass_assert(step, "PROCESSED_AT_POPULATED")
    else:
        Log.fail_assert(step, "PROCESSED_AT_POPULATED")
    
    # Status check (may be 'pending' or 'processed')
    status = staging.get("status")
    if status in ["pending", "processed"]:
        Log.pass_assert(step, f"STATUS_READY_FOR_REVIEW ({status})")
    else:
        Log.fail_assert(step, "STATUS_READY_FOR_REVIEW", f"Got: {status}")
    
    return staging

# ==============================================================================
# STEP 3: CONFLICT DETECTION
# ==============================================================================

async def step3_conflict_detection():
    """STEP 3: Verify conflict detection"""
    Log.section("STEP 3: CONFLICT DETECTION - MEDICAL INTEGRITY")
    
    step = "step3"
    
    # Insert allergy
    Log.info(f"Inserting allergy record for {PT_ALLERGY}...")
    allergy_record = {
        "patient_id": PT_ALLERGY,
        "encrypted_fhir_json_id": "00000000-0000-0000-0000-000000000001"
    }
    
    if await insert_record("main_vault", allergy_record):
        Log.pass_assert(step, "ALLERGY_INSERTED")
    else:
        Log.fail_assert(step, "ALLERGY_INSERTED")
    
    # Submit conflicting prescription
    Log.info("Submitting Amoxicillin (cross-reactive with Penicillin)...")
    payload = {
        "patient_id": PT_ALLERGY,
        "raw_text": "Patient prescribed Amoxicillin 500mg. Patient allergic to Penicillin."
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/ingest",
                json=payload,
                headers={"X-API-Key": BACKEND_API_KEY},
                timeout=10
            )
            
            if resp.status_code == 202:
                Log.pass_assert(step, "CONFLICT_INGEST_ACCEPTED")
            else:
                Log.fail_assert(step, "CONFLICT_INGEST_ACCEPTED", f"Got HTTP {resp.status_code}")
    except Exception as e:
        Log.fail_assert(step, "CONFLICT_INGEST_SUBMITTED", str(e))
    
    # Wait for processing
    Log.info("Waiting 15 seconds for conflict detection...")
    await asyncio.sleep(15)
    
    # Query for conflict
    conflict_record = await query_table("staging_vault", PT_ALLERGY)
    if conflict_record:
        print_json(conflict_record, "CONFLICT DETECTION RECORD")
        
        if conflict_record.get("conflict_flag"):
            Log.pass_assert(step, "CONFLICT_FLAG_SET")
        else:
            Log.fail_assert(step, "CONFLICT_FLAG_SET", "Flag is false (feature incomplete)")
        
        warning = conflict_record.get("ai_warning_msg", "")
        if "cross" in warning.lower() or "allergy" in warning.lower():
            Log.pass_assert(step, "WARNING_SPECIFIC")
        else:
            Log.fail_assert(step, "WARNING_SPECIFIC", "Message is generic")
    else:
        Log.fail_assert(step, "CONFLICT_RECORD_FOUND")

# ==============================================================================
# STEP 4: ADMIN APPROVAL & VAULT COMMIT
# ==============================================================================

async def step4_admin_approval():
    """STEP 4: Verify admin approval and vault commit"""
    Log.section("STEP 4: MOD 3→4 - ADMIN APPROVAL & VAULT COMMIT")
    
    step = "step4"
    
    # Get staging record
    staging = await query_table("staging_vault", PT_TRACE)
    if not staging:
        Log.fail_assert(step, "STAGING_FETCH_FOR_APPROVAL")
        return
    
    staging_id = staging.get("id")
    
    # Submit approval
    Log.info("Submitting admin approval decision...")
    approval_payload = {
        "staging_id": staging_id,
        "decision": "approve",
        "admin_id": "ADMIN-QA-MASTER",
        "reason": "QA verification complete"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/admin/resolve-pr",
                json=approval_payload,
                headers={"X-API-Key": BACKEND_API_KEY},
                timeout=10
            )
            
            if resp.status_code in [200, 201]:
                Log.pass_assert(step, f"APPROVAL_ACCEPTED (HTTP {resp.status_code})")
            else:
                Log.fail_assert(step, f"APPROVAL_ACCEPTED", f"Got HTTP {resp.status_code}")
                return
    except Exception as e:
        Log.fail_assert(step, "APPROVAL_SUBMITTED", str(e))
        return
    
    # Wait for transaction
    await asyncio.sleep(5)
    
    # Verify staging deletion
    staging_after = await query_table("staging_vault", PT_TRACE)
    if staging_after is None:
        Log.pass_assert(step, "STAGING_DELETED")
    else:
        Log.fail_assert(step, "STAGING_DELETED", f"Still exists: {staging_after.get('status')}")
    
    # Verify vault creation
    vault = await query_table("main_vault", PT_TRACE)
    if vault:
        Log.pass_assert(step, "MAIN_VAULT_CREATED")
        
        print_json(vault, "MAIN_VAULT RECORD AFTER COMMIT")
        
        if vault.get("patient_id") == PT_TRACE:
            Log.pass_assert(step, "PATIENT_ID_IN_VAULT")
        else:
            Log.fail_assert(step, "PATIENT_ID_IN_VAULT")
        
        encrypted_id = vault.get("encrypted_fhir_json_id")
        if encrypted_id and len(str(encrypted_id)) > 10:
            Log.pass_assert(step, f"ENCRYPTED_ID_VALID ({encrypted_id})")
        else:
            Log.fail_assert(step, "ENCRYPTED_ID_VALID", f"Got: {encrypted_id}")
        
        if vault.get("created_at"):
            Log.pass_assert(step, "CREATED_AT_POPULATED")
        else:
            Log.fail_assert(step, "CREATED_AT_POPULATED")
    else:
        Log.fail_assert(step, "MAIN_VAULT_CREATED")
    
    # Verify audit logs
    audit = await query_table("audit_logs", PT_TRACE)
    if audit:
        Log.pass_assert(step, "AUDIT_LOGS_CREATED")
        print_json(audit, "AUDIT LOG ENTRY")
    else:
        Log.fail_assert(step, "AUDIT_LOGS_CREATED", "Migration may be pending")

# ==============================================================================
# MAIN RUNNER
# ==============================================================================

async def main():
    Log.section("PRINCIPAL QA AUTOMATION ENGINEER - MASTER TEST SUITE")
    Log.info(f"Started: {datetime.now().isoformat()}")
    Log.info(f"Environment: Double Fallback (NO Redis, NO Local LLM)")
    Log.info(f"Supabase: {SUPABASE_URL.split('/')[-1]}")
    
    try:
        # Check backend connectivity
        Log.info("Checking backend connectivity...")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{BACKEND_URL}/docs", follow_redirects=True)
                if resp.status_code == 200:
                    Log.info("✅ Backend responding")
                else:
                    Log.info(f"⚠️  Backend returned {resp.status_code}")
        except:
            Log.info("⚠️  Backend may not be running - check manually")
        
        # Run all steps
        staging_result = await step1_ingest_staging()
        if staging_result:
            step2_result = await step2_worker_processing()
        
        await step3_conflict_detection()
        
        await step4_admin_approval()
        
        # Print summary
        Log.section("TEST SUMMARY")
        
        total_pass = sum(r["pass"] for r in test_results.values())
        total_fail = sum(r["fail"] for r in test_results.values())
        total = total_pass + total_fail
        pct = (total_pass / total * 100) if total > 0 else 0
        
        print(f"\n📊 OVERALL RESULT: {total_pass}/{total} assertions passed ({pct:.0f}%)")
        
        for step, result in test_results.items():
            step_total = result["pass"] + result["fail"]
            step_pct = (result["pass"] / step_total * 100) if step_total > 0 else 0
            status = "✅" if result["fail"] == 0 else "❌"
            print(f"\n{status} {step.upper()}: {result['pass']}/{step_total} ({step_pct:.0f}%)")
            for assertion in result["assertions"][:3]:  # Show first 3
                print(f"   {assertion}")
        
        Log.info(f"Completed: {datetime.now().isoformat()}")
        
    except Exception as e:
        Log.info(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
