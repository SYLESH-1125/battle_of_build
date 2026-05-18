#!/usr/bin/env python3
"""Module 4 Admin Resolution Test - Double Fallback Chaos Scenario."""
import os
import json
import requests
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

base_dir = Path(__file__).resolve().parents[0]
load_dotenv(base_dir / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
BACKEND_URL = "http://localhost:8000"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Step 1: Query for processed records ready for admin review
print("\n=== MODULE 4 ADMIN RESOLUTION TEST ===\n")
print("Step 1: Finding processed records for PT-GRAND-CHAOS-99...")
result = supabase.table("staging_vault").select("*").eq(
    "patient_id", "PT-GRAND-CHAOS-99"
).eq("status", "processed").limit(1).execute()

if not result.data:
    print("❌ No processed records found. Creating one...")
    # Fallback: query any processed record
    result = supabase.table("staging_vault").select("*").eq(
        "status", "processed"
    ).limit(1).execute()

if result.data:
    record = result.data[0]
    staging_id = record['id']
    patient_id = record['patient_id']
    print(f"✅ Found record ID: {staging_id}")
    print(f"   Patient: {patient_id}")
    print(f"   Status: {record['status']}")
    print(f"   FHIR JSON present: {bool(record.get('fhir_json'))}")
    
    # Step 2: Test GET /admin/resolve/:staging_id (fetch context for diff viewer)
    print(f"\nStep 2: Fetching diff context via GET /admin/resolve/{staging_id}...")
    try:
        response = requests.get(
            f"{BACKEND_URL}/admin/resolve/{staging_id}",
            headers={"X-API-Key": "vault-test-key-do-not-use-in-production"},
            timeout=5
        )
        if response.status_code == 200:
            context = response.json()
            print(f"✅ Context fetched (HTTP 200)")
            print(f"   Staging JSON keys: {list(context.get('staging_json', {}).keys())}")
            print(f"   Current main data: {context.get('current_main_data')}")
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Step 3: Test POST /admin/resolve-pr (approve with optional override)
    print(f"\nStep 3: Posting APPROVE decision to /admin/resolve-pr...")
    approval_payload = {
        "staging_id": staging_id,
        "decision": "approve",
        "admin_id": "admin-chaos-test",
        "reason": "Double Fallback Chaos Test - Approved by QA",
        "override_fhir_json": None  # Use original FHIR JSON
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/admin/resolve-pr",
            json=approval_payload,
            headers={"X-API-Key": "vault-test-key-do-not-use-in-production"},
            timeout=10
        )
        print(f"Response: HTTP {response.status_code}")
        print(f"Body: {response.json()}")
        
        if response.status_code == 200:
            result_data = response.json()
            tx_id = result_data.get('tx_id')
            secret_id = result_data.get('secret_id')
            print(f"\n✅ APPROVE successful!")
            print(f"   TX ID: {tx_id}")
            print(f"   Secret ID: {secret_id}")
            
            # Step 4: Verify DB state after resolution
            print(f"\nStep 4: Verifying DB state after approval...")
            
            # Check staging_vault - should be DELETED
            staging_result = supabase.table("staging_vault").select("*").eq(
                "id", staging_id
            ).execute()
            if not staging_result.data:
                print(f"✅ staging_vault row DELETED (as expected)")
            else:
                print(f"❌ staging_vault row still exists: {staging_result.data}")
            
            # Check main_vault - should have new row with encrypted_fhir_json_id
            main_result = supabase.table("main_vault").select("*").eq(
                "patient_id", patient_id
            ).order("created_at", desc=True).limit(1).execute()
            if main_result.data:
                main_row = main_result.data[0]
                print(f"✅ main_vault row created")
                print(f"   ID: {main_row.get('id')}")
                print(f"   Patient: {main_row.get('patient_id')}")
                print(f"   Encrypted secret ID: {main_row.get('encrypted_fhir_json_id')}")
            else:
                print(f"❌ No main_vault row found for patient {patient_id}")
            
            # Check audit_logs - may not exist if migration not applied
            try:
                audit_result = supabase.table("audit_logs").select("*").eq(
                    "staging_id", staging_id
                ).execute()
                if audit_result.data:
                    audit_row = audit_result.data[0]
                    print(f"✅ audit_logs entry created")
                    print(f"   Action: {audit_row.get('action')}")
                    print(f"   Admin: {audit_row.get('admin_id')}")
                    print(f"   TX ID: {audit_row.get('tx_id')}")
                else:
                    print(f"⚠️  No audit_logs entry found (migration may not be applied)")
            except Exception as e:
                print(f"⚠️  audit_logs table not ready: {e}")
                
        else:
            print(f"❌ Approval failed")
            
    except Exception as e:
        print(f"❌ Error posting approval: {e}")

else:
    print("❌ No processed records found in staging_vault")

print("\n=== MODULE 4 TEST COMPLETE ===\n")
