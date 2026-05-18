#!/usr/bin/env python3
"""Quick query to check staging_vault status for chaos test."""
import os
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

base_dir = Path(__file__).resolve().parents[0]
load_dotenv(base_dir / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    result = supabase.table("staging_vault").select("id,patient_id,status,fallback_reason,attempts,fhir_json,ai_warning_msg,model").eq(
        "patient_id", "PT-GRAND-CHAOS-99"
    ).execute()
    
    if result.data:
        for row in result.data:
            print(f"✅ Found record in staging_vault:")
            print(f"   ID: {row.get('id')}")
            print(f"   Patient: {row.get('patient_id')}")
            print(f"   Status: {row.get('status')}")
            print(f"   Fallback Reason: {row.get('fallback_reason')}")
            print(f"   Attempts: {row.get('attempts')}")
            print(f"   Model: {row.get('model')}")
            print(f"   FHIR JSON present: {bool(row.get('fhir_json'))}")
            print(f"   AI Warning: {row.get('ai_warning_msg')}")
    else:
        print("❌ No records found in staging_vault for PT-GRAND-CHAOS-99")
except Exception as e:
    print(f"❌ Error querying Supabase: {e}")
