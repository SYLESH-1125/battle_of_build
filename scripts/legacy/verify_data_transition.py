#!/usr/bin/env python3
"""Verify data transitions between modules."""
import json
import os
from supabase import create_client

SUPABASE_URL = "https://cdgcmcznmqykmzyovnmn.supabase.co"
SUPABASE_KEY = os.getenv('SUPABASE_SECRET_KEY') or os.getenv('SUPABASE_KEY') or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

patient_id = "PT-CHAOS-E2E-FINAL"

print("\n" + "="*80)
print("DATA TRANSITION VERIFICATION REPORT")
print("="*80)

# STEP 1: Check staging_vault
print(f"\n📍 STAGING_VAULT RECORDS FOR {patient_id}:")
try:
    result = supabase.table("staging_vault").select("*").eq("patient_id", patient_id).execute()
    staging_rows = result.data if result.data else []
    print(f"   Total rows: {len(staging_rows)}")
    
    if staging_rows:
        row = staging_rows[0]
        print(f"\n   First Record:")
        print(f"     ID: {row.get('id')}")
        print(f"     Status: {row.get('status')}")
        print(f"     Model: {row.get('model')}")
        print(f"     Fallback Reason: {row.get('fallback_reason')}")
        
        fhir = row.get('fhir_json')
        if fhir:
            if isinstance(fhir, dict):
                fhir_str = json.dumps(fhir)
            else:
                fhir_str = str(fhir)
            print(f"     FHIR JSON (first 200 chars): {fhir_str[:200]}...")
        else:
            print(f"     FHIR JSON: None")
except Exception as e:
    print(f"   ERROR: {e}")

# STEP 2: Check main_vault
print(f"\n✅ MAIN_VAULT RECORDS FOR {patient_id}:")
try:
    result = supabase.table("main_vault").select("*").eq("patient_id", patient_id).execute()
    main_rows = result.data if result.data else []
    print(f"   Total rows: {len(main_rows)}")
    
    if main_rows:
        for i, row in enumerate(main_rows):
            print(f"\n   Record {i+1}:")
            print(f"     ID: {row.get('id')}")
            print(f"     Patient ID: {row.get('patient_id')}")
            print(f"     Encrypted FHIR ID: {row.get('encrypted_fhir_json_id')}")
            print(f"     Created At: {row.get('created_at')}")
except Exception as e:
    print(f"   ERROR: {e}")

# STEP 3: Check audit_logs
print(f"\n📋 AUDIT_LOGS FOR {patient_id}:")
try:
    result = supabase.table("audit_logs").select("*").eq("patient_id", patient_id).execute()
    audit_rows = result.data if result.data else []
    print(f"   Total rows: {len(audit_rows)}")
    
    if audit_rows:
        for i, row in enumerate(audit_rows):
            print(f"\n   Record {i+1}:")
            print(f"     TX ID: {row.get('tx_id')}")
            print(f"     Action: {row.get('action')}")
            print(f"     Admin ID: {row.get('admin_id')}")
            print(f"     Created At: {row.get('created_at')}")
            
            new_val = row.get('new_value')
            if new_val:
                if isinstance(new_val, str):
                    new_val_str = new_val
                else:
                    new_val_str = json.dumps(new_val)
                print(f"     New Value (first 150 chars): {new_val_str[:150]}...")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "="*80)
print("CONCLUSION:")
print(f"  Staging records: {len(staging_rows)}")
print(f"  Main vault records: {len(main_rows)}")
print(f"  Audit log records: {len(audit_rows)}")
print("="*80 + "\n")
