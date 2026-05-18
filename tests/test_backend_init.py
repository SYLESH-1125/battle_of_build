"""Test backend Supabase initialization matches our debug script"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Match backend initialization exactly
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "mock")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY", "mock-key")

print(f"SUPABASE_URL: {SUPABASE_URL[:30]}...")
print(f"SUPABASE_KEY: {SUPABASE_KEY[:30]}...")

if SUPABASE_URL == "mock":
    print("ERROR: SUPABASE_URL is still 'mock'!")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Try same insert as backend
try:
    data = {
        "patient_id": "PT-BACKEND-TEST-001",
        "raw_payload": {"test": "from_backend_init"},
        "status": "pending",
        "fallback_reason": "redis_unavailable",
        "attempts": 0,
    }
    result = supabase.table("staging_vault").insert(data).execute()
    print(f"✓ Insert successful: {result.data[0]['id']}")
except Exception as e:
    print(f"✗ Insert failed: {e}")
    exit(1)
