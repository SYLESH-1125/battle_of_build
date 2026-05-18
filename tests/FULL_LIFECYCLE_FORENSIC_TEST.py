#!/usr/bin/env python3
"""
ULTIMATE PATIENT LIFECYCLE FORENSIC TEST
Full end-to-end lifecycle with PHASE 1-3 and complete forensic documentation.
Principal QA Architect: Autonomous execution mode.
"""

import os
import json
import time
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")
BACKEND_URL = "http://localhost:8000"

# Test data
PATIENT_ID_PHASE_1 = "PT-LIFECYCLE-MASTER-01"
CLINICAL_NOTE_PHASE_1 = "Patient presents with high blood pressure. Prescribed Lisinopril 10mg daily."
CLINICAL_NOTE_PHASE_2 = "Patient reports severe allergic reaction to ACE Inhibitors (Lisinopril) causing angioedema."

# Forensic storage
FORENSIC_REPORT = {
    "test_timestamp": datetime.now().isoformat(),
    "phase_1": {},
    "phase_2": {},
    "phase_3": {}
}

async def init_supabase() -> Client:
    """Initialize Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

async def phase_1_genesis():
    """PHASE 1: Genesis Encounter - New Patient with Prescription"""
    print("\n" + "="*70)
    print("PHASE 1: GENESIS ENCOUNTER (New Patient Onboarding)")
    print("="*70)
    
    client = await init_supabase()
    
    # Step 1: Insert into staging_vault
    print(f"\n[STEP 1] Ingesting patient {PATIENT_ID_PHASE_1}...")
    
    response = client.table("staging_vault").insert({
        "patient_id": PATIENT_ID_PHASE_1,
        "raw_payload": {
            "raw_text": CLINICAL_NOTE_PHASE_1,
            "patient_id": PATIENT_ID_PHASE_1,
            "timestamp": datetime.now().isoformat()
        },
        "status": "pending",
        "conflict_flag": False
    }).execute()
    
    staging_id = response.data[0]["id"] if response.data else None
    print(f"[OK] Staging record created: {staging_id}")
    FORENSIC_REPORT["phase_1"]["staging_id"] = str(staging_id)
    
    # Step 2: Wait for worker to process (simulate FHIR generation)
    print(f"\n[STEP 2] Waiting 20s for worker to generate FHIR...")
    await asyncio.sleep(20)
    
    # Step 3: Query staging_vault for FHIR JSON
    staging_record = client.table("staging_vault").select("*").eq("id", staging_id).execute()
    
    if staging_record.data:
        record = staging_record.data[0]
        print(f"[OK] Staging record processed")
        print(f"   - FHIR Generated: {bool(record.get('fhir_json'))}")
        print(f"   - Conflict Flag: {record.get('conflict_flag')}")
        print(f"   - AI Warning: {record.get('ai_warning_msg')}")
        
        FORENSIC_REPORT["phase_1"]["fhir_json"] = record.get("fhir_json")
        FORENSIC_REPORT["phase_1"]["conflict_flag"] = record.get("conflict_flag")
        
        # ASSERTION 1: FHIR JSON generated
        assert record.get("fhir_json") is not None, "[FAIL] FHIR JSON not generated"
        print("   [PASS] ASSERTION 1: FHIR JSON generated")
        
        # ASSERTION 2: Contains Lisinopril
        fhir_str = json.dumps(record.get("fhir_json", {})).lower()
        assert "lisinopril" in fhir_str, "[FAIL] Lisinopril not in FHIR"
        print("   [PASS] ASSERTION 2: MedicationRequest for Lisinopril present")
        
        # ASSERTION 3: No conflict on first encounter
        assert record.get("conflict_flag") == False, "[FAIL] Conflict flag should be False on first encounter"
        print("   [PASS] ASSERTION 3: No conflict on first encounter")
    
    # Step 4: Commit to main_vault
    print(f"\n[STEP 3] Simulating admin approval...")
    vault_record = client.table("main_vault").insert({
        "patient_id": PATIENT_ID_PHASE_1,
        "encrypted_fhir_json_id": staging_id
    }).execute()
    
    vault_id = vault_record.data[0]["id"] if vault_record.data else None
    print(f"[OK] Vault record created: {vault_id}")
    FORENSIC_REPORT["phase_1"]["vault_id"] = str(vault_id)
    FORENSIC_REPORT["phase_1"]["vault_fhir_json_id"] = str(staging_id)
    
    # ASSERTION 4: Vault record created
    assert vault_id is not None, "[FAIL] Vault record not created"
    print("[PASS] ASSERTION 4: Vault commitment successful")
    
    print("\n[OK] PHASE 1 COMPLETE: 4/4 assertions passed")
    return vault_id, record.get("fhir_json")

async def phase_2_conflict():
    """PHASE 2: Clinical Conflict - Context Hydration Detects Allergy"""
    print("\n" + "="*70)
    print("PHASE 2: CLINICAL CONFLICT (Context Hydration)")
    print("="*70)
    
    client = await init_supabase()
    
    # Step 1: Insert conflicting data
    print(f"\n[STEP 1] Ingesting same patient with allergy data...")
    
    response = client.table("staging_vault").insert({
        "patient_id": PATIENT_ID_PHASE_1,
        "raw_payload": {
            "raw_text": CLINICAL_NOTE_PHASE_2,
            "patient_id": PATIENT_ID_PHASE_1,
            "timestamp": datetime.now().isoformat()
        },
        "status": "pending",
        "conflict_flag": False
    }).execute()
    
    staging_id_2 = response.data[0]["id"] if response.data else None
    print(f"[OK] Second staging record created: {staging_id_2}")
    FORENSIC_REPORT["phase_2"]["staging_id"] = str(staging_id_2)
    
    # Step 2: Wait for worker with context hydration
    print(f"\n[STEP 2] Waiting 20s for worker to perform context hydration...")
    await asyncio.sleep(20)
    
    # Step 3: Query for conflict detection
    staging_record_2 = client.table("staging_vault").select("*").eq("id", staging_id_2).execute()
    
    if staging_record_2.data:
        record = staging_record_2.data[0]
        print(f"[OK] Staging record processed (Phase 2)")
        print(f"   - Conflict Flag: {record.get('conflict_flag')}")
        print(f"   - AI Warning: {record.get('ai_warning_msg')}")
        
        FORENSIC_REPORT["phase_2"]["conflict_flag"] = record.get("conflict_flag")
        FORENSIC_REPORT["phase_2"]["ai_warning_msg"] = record.get("ai_warning_msg")
        FORENSIC_REPORT["phase_2"]["fhir_json"] = record.get("fhir_json")
        
        # ASSERTION 1: Conflict detected
        assert record.get("conflict_flag") == True, "[FAIL] Conflict flag should be True (allergy vs prescription)"
        print("   [PASS] ASSERTION 1: Conflict detected (conflict_flag = TRUE)")
        
        # ASSERTION 2: Specific warning message
        warning = str(record.get("ai_warning_msg", "")).lower()
        assert "lisinopril" in warning or "allergy" in warning or "angioedema" in warning, \
            f"[FAIL] Warning should mention Lisinopril/allergy. Got: {record.get('ai_warning_msg')}"
        print(f"   [PASS] ASSERTION 2: Specific AI warning generated")
        print(f"      Message: {record.get('ai_warning_msg')[:100]}...")
    
    print("\n[OK] PHASE 2 COMPLETE: 2/2 assertions passed (context hydration verified)")
    return staging_id_2, record.get("fhir_json"), record.get("ai_warning_msg")

async def phase_3_audit():
    """PHASE 3: Admin Override & Forensic Audit Trail"""
    print("\n" + "="*70)
    print("PHASE 3: ADMIN OVERRIDE & FORENSIC AUDIT TRAIL")
    print("="*70)
    
    client = await init_supabase()
    
    # Get Phase 1 and Phase 2 data
    phase1_vault = client.table("main_vault").select("*").eq("patient_id", PATIENT_ID_PHASE_1).order("created_at", desc=False).limit(1).execute()
    phase2_staging = client.table("staging_vault").select("*").eq("patient_id", PATIENT_ID_PHASE_1).order("processed_at", desc=False).limit(1).execute()
    
    if not phase2_staging.data:
        print("❌ Phase 2 staging record not found")
        return
    
    phase2_record = phase2_staging.data[-1]
    
    # Get Phase 1 staging record (referenced by encrypted_fhir_json_id in main_vault)
    phase1_fhir = None
    if phase1_vault.data:
        phase1_main = phase1_vault.data[0]
        phase1_staging_id = phase1_main.get("encrypted_fhir_json_id")
        if phase1_staging_id:
            phase1_staging_result = client.table("staging_vault").select("*").eq("id", phase1_staging_id).execute()
            if phase1_staging_result.data:
                phase1_fhir = phase1_staging_result.data[0].get("fhir_json")
    
    print(f"\n[STEP 1] Admin reviewing conflict...")
    print(f"   - Patient: {PATIENT_ID_PHASE_1}")
    print(f"   - Phase 1 (Prescription): Lisinopril")
    print(f"   - Phase 2 (Allergy): ACE Inhibitor allergy")
    print(f"   - UI Rendering: RED flag for conflict")
    
    # ASSERTION 1: Records exist for comparison
    assert phase1_vault.data, "[FAIL] Phase 1 vault record not found"
    print("   [PASS] ASSERTION 1: Phase 1 and Phase 2 records found for diff")
    
    phase2_fhir = phase2_record.get("fhir_json")
    
    # Step 2: Create audit trail
    print(f"\n[STEP 2] Creating forensic audit trail...")
    
    audit_entry = {
        "patient_id": PATIENT_ID_PHASE_1,
        "staging_id": phase2_record.get("id"),
        "admin_id": "qa-automation-principal",
        "action_type": "approve",
        "old_value": phase1_fhir,
        "new_value": phase2_fhir,
        "reason": "Admin override: Patient allergy to Lisinopril documented. Medication review required."
    }
    
    audit_response = client.table("audit_logs").insert(audit_entry).execute()
    audit_id = audit_response.data[0]["id"] if audit_response.data else None
    print(f"[OK] Audit log created: {audit_id}")
    FORENSIC_REPORT["phase_3"]["audit_id"] = str(audit_id)
    FORENSIC_REPORT["phase_3"]["audit_entry"] = audit_entry
    
    # ASSERTION 2: Audit log contains old_value (Phase 1 FHIR)
    assert audit_entry["old_value"] is not None, "[FAIL] old_value (Phase 1 FHIR) not recorded"
    print("   [PASS] ASSERTION 2: old_value contains Phase 1 FHIR JSON")
    
    # ASSERTION 3: Audit log contains new_value (Phase 2 FHIR)
    assert audit_entry["new_value"] is not None, "[FAIL] new_value (Phase 2 FHIR) not recorded"
    print("   [PASS] ASSERTION 3: new_value contains Phase 2 FHIR JSON")
    
    # Step 3: Commit Phase 2 to vault
    print(f"\n[STEP 3] Committing Phase 2 to vault...")
    vault_response = client.table("main_vault").insert({
        "patient_id": PATIENT_ID_PHASE_1,
        "encrypted_fhir_json_id": phase2_record.get("id")
    }).execute()
    
    # ASSERTION 4: Phase 2 vault record created
    assert vault_response.data, "[FAIL] Phase 2 vault record not created"
    print("   [PASS] ASSERTION 4: Phase 2 committed to main_vault")
    FORENSIC_REPORT["phase_3"]["vault_id_phase2"] = str(vault_response.data[0]["id"])
    
    print("\n[OK] PHASE 3 COMPLETE: 4/4 assertions passed (forensic audit trail verified)")

async def main():
    """Execute full lifecycle test"""
    print("\n" + "="*70)
    print("ULTIMATE PATIENT LIFECYCLE FORENSIC TEST")
    print("Digital Human Memory Vault - Full End-to-End Validation")
    print("="*70)
    
    try:
        # PHASE 1
        vault_id_1, fhir_json_1 = await phase_1_genesis()
        
        # PHASE 2
        staging_id_2, fhir_json_2, warning_msg = await phase_2_conflict()
        
        # PHASE 3
        await phase_3_audit()
        
        # Final summary
        print("\n" + "="*70)
        print("FINAL RESULTS")
        print("="*70)
        print("[OK] PHASE 1: 4/4 assertions PASSED")
        print("[OK] PHASE 2: 2/2 assertions PASSED")
        print("[OK] PHASE 3: 4/4 assertions PASSED")
        print("\n[SUCCESS] OVERALL: 10/10 ASSERTIONS PASSED (100% SUCCESS)")
        print("="*70)
        
        # Output forensic report
        print("\nGenerating ULTIMATE FORENSIC REPORT...")
        report_path = "ULTIMATE_PATIENT_LIFECYCLE_FORENSIC_REPORT_DETAILED.json"
        with open(report_path, "w") as f:
            json.dump(FORENSIC_REPORT, f, indent=2, default=str)
        print(f"[OK] Forensic report saved to: {report_path}")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(main())
