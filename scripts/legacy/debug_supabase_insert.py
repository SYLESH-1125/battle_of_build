"""Debug: Test direct Supabase insert to staging_vault"""
import sys
from supabase import create_client

SUPABASE_URL = "https://cdgcmcznmqykmzyovnmn.supabase.co"
SUPABASE_SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E"

print("Attempting direct insert to staging_vault...")
try:
    sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
    data = {
        "patient_id": "PT-DEBUG-001",
        "raw_payload": {"test": "data"},
        "status": "pending",
        "fallback_reason": "redis_unavailable",
        "attempts": 0,
    }
    result = sb.table("staging_vault").insert(data).execute()
    print(f"✓ Insert successful!")
    print(f"  Response: {result.data}")
except Exception as e:
    print(f"✗ Insert failed!")
    print(f"  Error: {e}")
    print(f"  Error type: {type(e)}")
    sys.exit(1)

# Query back
print("\nQuerying back...")
try:
    result = sb.table("staging_vault").select("*").eq("patient_id", "PT-DEBUG-001").execute()
    print(f"✓ Query successful!")
    print(f"  Data: {result.data}")
except Exception as e:
    print(f"✗ Query failed!")
    print(f"  Error: {e}")
    sys.exit(1)
