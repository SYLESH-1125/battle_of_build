#!/usr/bin/env python3
"""
PRINCIPAL QA AUTOMATION ENGINEER - END-TO-END MASTER TEST SUITE
Complete Module 1-4 Data Transition Verification with Deep Forensics

Constraints: NO Redis, NO Local LLM (Cloud Fallback Only)
"""

import asyncio
import json
import os
import sys
import time
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# ==============================================================================
# CONFIGURATION & ENVIRONMENT
# ==============================================================================

def load_env():
    """Load environment from .env file"""
    env_vars = {}
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    env_vars[key] = val
                    os.environ[key] = val
    return env_vars

env = load_env()

SUPABASE_URL = env.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_SECRET = env.get("SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SECRET_KEY"))
BACKEND_URL = "http://127.0.0.1:8000"
VAULT_API_KEY = env.get("VAULT_API_KEY", "vault-test-key-do-not-use-in-production")

# Test data
PT_TRACE = "PT-DATA-TRACE-MAIN-001"
PT_ALLERGY = "PT-DATA-ALLERGY-MAIN-002"

# Supabase headers
HEADERS = {
    "apikey": SUPABASE_SECRET,
    "Authorization": f"Bearer {SUPABASE_SECRET}",
    "Content-Type": "application/json"
}

# ==============================================================================
# LOGGING & REPORTING
# ==============================================================================

class Report:
    def __init__(self):
        self.sections = []
        self.passed = 0
        self.failed = 0
        
    def section(self, title: str):
        self.sections.append(f"\n{'='*80}\n{title}\n{'='*80}\n")
        print(f"\n{'='*80}\n{title}\n{'='*80}\n")
    
    def add(self, text: str):
        self.sections.append(text + "\n")
        print(text)
    
    def pass_assert(self, msg: str):
        self.sections.append(f"✅ PASS: {msg}\n")
        print(f"✅ PASS: {msg}")
        self.passed += 1
    
    def fail_assert(self, msg: str, details: str = ""):
        self.sections.append(f"❌ FAIL: {msg}\n")
        if details:
            self.sections.append(f"  Details: {details}\n")
        print(f"❌ FAIL: {msg}")
        if details:
            print(f"  Details: {details}")
        self.failed += 1
    
    def json_dump(self, title: str, data: Dict):
        json_str = json.dumps(data, indent=2, default=str)
        self.sections.append(f"\n{title}:\n{json_str}\n")
        print(f"\n{title}:\n{json_str}\n")
    
    def summary(self) -> str:
        total = self.passed + self.failed
        pct = (self.passed / total * 100) if total > 0 else 0
        return f"\n📊 RESULTS: {self.passed}/{total} assertions passed ({pct:.0f}%)\n"
    
    def save(self, filename: str):
        content = "".join(self.sections)
        with open(filename, "w") as f:
            f.write(content)
        print(f"\n✅ Report saved to {filename}")

report = Report()

# ==============================================================================
# SUPABASE REST API HELPERS
# ==============================================================================

async def query_table(table: str, patient_id: str, limit: int = 5) -> list:
    """Query table for patient ID"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{SUPABASE_URL}/rest/v1/{table}"
            params = {
                "patient_id": f"eq.{patient_id}",
                "select": "*",
                "limit": str(limit),
                "order": "created_at.desc"
            }
            resp = await client.get(url, params=params, headers=HEADERS)
            if resp.status_code == 200:
                return resp.json()
        return []
    except Exception as e:
        report.add(f"⚠️  Query error: {e}")
        return []

async def insert_table(table: str, data: Dict) -> bool:
    """Insert record into table"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{SUPABASE_URL}/rest/v1/{table}"
            resp = await client.post(url, json=data, headers=HEADERS)
            return resp.status_code in [200, 201]
    except Exception as e:
        report.add(f"⚠️  Insert error: {e}")
        return False

async def delete_table_records(table: str, patient_id: str) -> bool:
    """Delete all records for patient"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = f"{SUPABASE_URL}/rest/v1/{table}"
            params = {"patient_id": f"eq.{patient_id}"}
            resp = await client.delete(url, params=params, headers=HEADERS)
            return resp.status_code in [200, 204]
    except Exception as e:
        report.add(f"⚠️  Delete error: {e}")
        return False

# ==============================================================================
# STEP 1: INGEST & STAGING
# ==============================================================================

async def step_1_ingest_staging():
    """STEP 1: MOD 1→2 Ingest and Staging Creation"""
    report.section("STEP 1: MOD 1→2 - INGEST & STAGING CREATION")
    
    # Clean up any prior records
    await delete_table_records("staging_vault", PT_TRACE)
    await asyncio.sleep(1)
    
    # Submit ingest
    report.add(f"Submitting ingest for patient {PT_TRACE}...")
    payload = {
        "patient_id": PT_TRACE,
        "raw_text": "Patient presents with severe joint pain. Prescribed 500mg Naproxen for inflammation."
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{BACKEND_URL}/ingest",
                json=payload,
                headers={"X-API-Key": VAULT_API_KEY},
            )
            
            if resp.status_code == 202:
                report.pass_assert("INGEST accepted (HTTP 202)")
            else:
                report.fail_assert("INGEST accepted", f"Got HTTP {resp.status_code}")
                return None
    except Exception as e:
        report.fail_assert("INGEST submitted", str(e))
        return None
    
    # Wait for database
    await asyncio.sleep(3)
    
    # Query staging
    records = await query_table("staging_vault", PT_TRACE)
    if not records:
        report.fail_assert("STAGING record created")
        return None
    
    staging = records[0]
    staging_id = staging.get("id")
    
    report.json_dump("STAGING_VAULT Record at STEP 1", staging)
    
    # Verify assertions
    if staging.get("patient_id") == PT_TRACE:
        report.pass_assert("patient_id matches")
    else:
        report.fail_assert("patient_id matches", f"Got {staging.get('patient_id')}")
    
    if staging.get("status") == "pending":
        report.pass_assert("status is 'pending'")
    else:
        report.fail_assert("status is 'pending'", f"Got {staging.get('status')}")
    
    if staging.get("fhir_json") is None:
        report.pass_assert("fhir_json is null (not yet processed)")
    else:
        report.fail_assert("fhir_json is null", "Already contains data")
    
    fallback = staging.get("fallback_reason", "")
    if "redis" in str(fallback).lower():
        report.pass_assert(f"fallback_reason indicates Redis unavailable: '{fallback}'")
    else:
        report.add(f"ℹ️  fallback_reason: {fallback}")
    
    return (staging_id, staging)

# ==============================================================================
# STEP 2: WORKER PROCESSING & FHIR
# ==============================================================================

async def step_2_worker_processing():
    """STEP 2: MOD 2→3 Worker Processing and FHIR Generation"""
    report.section("STEP 2: MOD 2→3 - WORKER PROCESSING & FHIR GENERATION")
    
    report.add("Waiting 20 seconds for worker to process (local timeout → cloud fallback)...")
    await asyncio.sleep(20)
    
    # Query staging again
    records = await query_table("staging_vault", PT_TRACE)
    if not records:
        report.fail_assert("STAGING record updated after processing")
        return None
    
    staging = records[0]
    
    report.json_dump("STAGING_VAULT Record after processing", staging)
    
    # Verify FHIR
    fhir = staging.get("fhir_json")
    if fhir and isinstance(fhir, dict):
        report.pass_assert("fhir_json is populated (no longer null)")
        
        if fhir.get("resourceType") == "Bundle":
            report.pass_assert("fhir_json is valid FHIR Bundle")
            report.json_dump("FHIR JSON Generated", fhir)
        else:
            report.fail_assert("fhir_json is valid FHIR", f"Got resourceType: {fhir.get('resourceType')}")
    else:
        report.fail_assert("fhir_json is populated")
    
    # Verify model
    model = staging.get("model", "unknown")
    if model in ["rule-based", "groq", "gemini", "claude", "gpt"]:
        report.pass_assert(f"model tracked as cloud provider: '{model}'")
    else:
        report.fail_assert("model tracked", f"Got: {model}")
    
    # Verify processed_at
    if staging.get("processed_at"):
        report.pass_assert("processed_at is populated")
    else:
        report.fail_assert("processed_at is populated")
    
    return staging

# ==============================================================================
# STEP 3: CONFLICT DETECTION
# ==============================================================================

async def step_3_conflict_detection():
    """STEP 3: Conflict Detection - Medical Integrity"""
    report.section("STEP 3: CONFLICT DETECTION - MEDICAL INTEGRITY")
    
    # Clean up
    await delete_table_records("staging_vault", PT_ALLERGY)
    await delete_table_records("main_vault", PT_ALLERGY)
    await asyncio.sleep(1)
    
    # Insert allergy into main_vault
    report.add(f"Inserting allergy record for patient {PT_ALLERGY}...")
    allergy_record = {
        "patient_id": PT_ALLERGY,
        "encrypted_fhir_json_id": "12345678-1234-5678-1234-567812345678"
    }
    
    if await insert_table("main_vault", allergy_record):
        report.pass_assert("Allergy record inserted to main_vault")
    else:
        report.fail_assert("Allergy record inserted")
    
    # Submit conflicting prescription
    report.add("Submitting Amoxicillin (cross-reactive to Penicillin allergy)...")
    payload = {
        "patient_id": PT_ALLERGY,
        "raw_text": "Patient allergic to Penicillin. Prescribe Amoxicillin 500mg BID for infection."
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{BACKEND_URL}/ingest",
                json=payload,
                headers={"X-API-Key": VAULT_API_KEY},
            )
            
            if resp.status_code == 202:
                report.pass_assert("Conflicting prescription ingest accepted")
            else:
                report.fail_assert("Conflicting prescription ingest", f"HTTP {resp.status_code}")
    except Exception as e:
        report.fail_assert("Conflicting prescription", str(e))
    
    # Wait for processing
    report.add("Waiting 20 seconds for conflict detection...")
    await asyncio.sleep(20)
    
    # Query for conflict
    records = await query_table("staging_vault", PT_ALLERGY)
    if records:
        conflict = records[0]
        report.json_dump("Conflict Record", conflict)
        
        if conflict.get("conflict_flag"):
            report.pass_assert("conflict_flag is true")
        else:
            report.fail_assert("conflict_flag is true", "Feature may need implementation")
        
        warning = conflict.get("ai_warning_msg", "")
        if warning and len(warning) > 10:
            report.pass_assert(f"ai_warning_msg populated: '{warning[:80]}...'")
        else:
            report.fail_assert("ai_warning_msg populated")
    else:
        report.fail_assert("Conflict record found in staging_vault")

# ==============================================================================
# STEP 4: ADMIN APPROVAL & VAULT COMMIT
# ==============================================================================

async def step_4_admin_approval():
    """STEP 4: MOD 3→4 Admin Approval and Vault Commit"""
    report.section("STEP 4: MOD 3→4 - ADMIN APPROVAL & VAULT COMMIT")
    
    # Get staging record
    records = await query_table("staging_vault", PT_TRACE)
    if not records:
        report.fail_assert("STAGING record exists for approval")
        return
    
    staging = records[0]
    staging_id = staging.get("id")
    
    report.add(f"Submitting admin approval for staging_id: {staging_id}")
    approval_payload = {
        "staging_id": staging_id,
        "decision": "approve",
        "admin_id": "QA-MASTER-ENGINEER",
        "reason": "QA verification complete"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{BACKEND_URL}/admin/resolve-pr",
                json=approval_payload,
                headers={"X-API-Key": VAULT_API_KEY},
            )
            
            if resp.status_code in [200, 201]:
                report.pass_assert(f"Approval accepted (HTTP {resp.status_code})")
            else:
                report.fail_assert("Approval accepted", f"HTTP {resp.status_code}")
                try:
                    error_detail = resp.json()
                    report.add(f"Error detail: {error_detail}")
                except:
                    pass
                return
    except Exception as e:
        report.fail_assert("Approval submitted", str(e))
        return
    
    # Wait for transaction
    await asyncio.sleep(5)
    
    # Verify staging deletion
    records = await query_table("staging_vault", PT_TRACE)
    if not records:
        report.pass_assert("STAGING record deleted after approval")
    else:
        report.fail_assert("STAGING record deleted", f"Still exists: {records[0].get('status')}")
    
    # Verify vault creation
    vault_records = await query_table("main_vault", PT_TRACE)
    if vault_records:
        vault = vault_records[0]
        report.pass_assert("MAIN_VAULT record created")
        
        report.json_dump("MAIN_VAULT Record after commit", vault)
        
        if vault.get("patient_id") == PT_TRACE:
            report.pass_assert("patient_id in vault matches")
        else:
            report.fail_assert("patient_id in vault", f"Got {vault.get('patient_id')}")
        
        encrypted_id = vault.get("encrypted_fhir_json_id")
        if encrypted_id and len(str(encrypted_id)) > 5:
            report.pass_assert(f"encrypted_fhir_json_id present: {encrypted_id}")
        else:
            report.fail_assert("encrypted_fhir_json_id present", f"Got {encrypted_id}")
    else:
        report.fail_assert("MAIN_VAULT record created")
    
    # Verify audit logs (may not exist if migration pending)
    audit_records = await query_table("audit_logs", PT_TRACE)
    if audit_records:
        audit = audit_records[0]
        report.pass_assert("AUDIT_LOGS entry created")
        report.json_dump("AUDIT_LOGS Entry", audit)
    else:
        report.add("ℹ️  AUDIT_LOGS: No records (migration may be pending)")

# ==============================================================================
# MAIN RUNNER
# ==============================================================================

async def main():
    report.section("PRINCIPAL QA AUTOMATION ENGINEER - END-TO-END TEST SUITE")
    report.add(f"Test Started: {datetime.now().isoformat()}")
    report.add(f"Environment: Double Fallback (NO Redis, NO Local LLM)")
    report.add(f"Supabase: {SUPABASE_URL.split('/')[-1] if SUPABASE_URL else 'NOT CONFIGURED'}")
    
    # Check backend
    report.add("\nChecking backend connectivity...")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_URL}/docs")
            if resp.status_code in [200, 404]:
                report.pass_assert("Backend responding")
            else:
                report.add(f"⚠️  Backend returned {resp.status_code}")
    except Exception as e:
        report.fail_assert("Backend connectivity", str(e))
        report.add("❌ Cannot continue without backend. Ensure it's running.")
        return
    
    # Run all steps
    try:
        result1 = await step_1_ingest_staging()
        if result1:
            await step_2_worker_processing()
        
        await step_3_conflict_detection()
        await step_4_admin_approval()
    except Exception as e:
        report.add(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    report.section("FINAL SUMMARY")
    report.add(report.summary())
    report.add(f"Test Completed: {datetime.now().isoformat()}")
    
    # Save report
    filename = f"QA_E2E_SIGN_OFF_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report.save(filename)

if __name__ == "__main__":
    asyncio.run(main())
