#!/usr/bin/env python3
"""
PHASE 3: Admin Portal - Conflict Resolution & Override Approval
Test the admin endpoint to approve the conflicting prescription.
"""

import requests
import json
from supabase import create_client

# Initialize Supabase
supabase_url = "https://cdgcmcznmqykmzyovnmn.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk0NzQ4NDMsImV4cCI6MjA1NTA1MDg0M30.x6P8zKqzJKlnWdZC8B2-Yxxb7E2uNEddAbfJMfAIvRQ"

supabase = create_client(supabase_url, supabase_key)

print("\n=== PHASE 3: ADMIN PORTAL ===")
print("Objective: Review conflicting prescription and approve override")
print()

# Get the staging record for PT-OMNI-MASTER-99
try:
    response = supabase.table("staging_vault").select("id, patient_id, status, conflict_flag").eq("patient_id", "PT-OMNI-MASTER-99").order("processed_at", desc=True).limit(1).execute()
    records = response.data
    
    if not records:
        print("❌ No staging record found for PT-OMNI-MASTER-99")
        exit(1)
    
    record = records[0]
    staging_id = record["id"]
    
    print(f"✅ Found staging record: {staging_id}")
    print(f"   Patient: {record['patient_id']}")
    print(f"   Status: {record['status']}")
    print(f"   Conflict Flag: {record['conflict_flag']}")
    print()
    
except Exception as e:
    print(f"❌ Error querying staging_vault: {e}")
    exit(1)

# Call the admin approval endpoint
print("📝 Sending admin approval request...")
print(f"   Endpoint: http://localhost:8000/admin/resolve-pr")
print(f"   Staging ID: {staging_id}")
print()

payload = {
    "staging_id": staging_id,
    "decision": "approve",
    "admin_id": "admin-test-user-phase3",
    "reason": "Approved medication override for Amoxicillin despite Penicillin allergy (clinical judgment override)"
}

headers = {
    "Content-Type": "application/json",
    "X-API-Key": "vault-test-key-do-not-use-in-production"
}

try:
    response = requests.post(
        "http://localhost:8000/admin/resolve-pr",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        tx_id = data.get("tx_id")
        print(f"✅ ADMIN APPROVAL SUCCESSFUL")
        print(f"   TX ID: {tx_id}")
        print(f"   Record moved to main_vault with override flag")
        print()
        print("✅ PHASE 3 COMPLETE: Admin approved medication override")
    else:
        print(f"❌ Admin approval failed with status {response.status_code}")
        print(f"   Error: {response.text}")
        
except Exception as e:
    print(f"❌ Request error: {e}")
    exit(1)
