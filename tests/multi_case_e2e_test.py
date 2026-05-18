"""
Comprehensive E2E Test Suite: Ingestion, Fallback, AI/LLM, DLQ
Tests multiple diverse scenarios for Memory Vault (no Redis required)
"""
import requests
import time
from supabase import create_client

BACKEND_URL = "http://127.0.0.1:8000"
SUPABASE_URL = "https://cdgcmcznmqykmzyovnmn.supabase.co"
SUPABASE_SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E"
VAULT_API_KEY = "vault-test-key-do-not-use-in-production"

sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

TEST_CASES = [
    # Zero-state patient
    {
        "desc": "Zero-state patient, clean note",
        "patient_id": "PT-MULTI-01",
        "doctor_id": "DOC-01",
        "raw_text": "Patient is new. Prescribed Paracetamol 500mg for fever.",
        "expect_conflict": False,
    },
    # Allergy history, conflicting medication
    {
        "desc": "Allergy history, conflicting medication",
        "patient_id": "PT-MULTI-02",
        "doctor_id": "DOC-02",
        "raw_text": "Patient has penicillin allergy. Prescribed Amoxicillin.",
        "expect_conflict": True,
    },
    # Privacy filter block
    {
        "desc": "Privacy filter block",
        "patient_id": "PT-MULTI-03",
        "doctor_id": "DOC-03",
        "raw_text": "Patient SSN: 123-45-6789. Needs checkup.",
        "expect_blocked": True,
    },
    # Large note
    {
        "desc": "Large note",
        "patient_id": "PT-MULTI-04",
        "doctor_id": "DOC-04",
        "raw_text": "Patient presents with symptoms of flu. " * 100,
        "expect_conflict": False,
    },
    # Edge: Empty note
    {
        "desc": "Empty note",
        "patient_id": "PT-MULTI-05",
        "doctor_id": "DOC-05",
        "raw_text": "",
        "expect_blocked": True,
    },
]

def post_ingest(tc):
    payload = {
        "patient_id": tc["patient_id"],
        "doctor_id": tc["doctor_id"],
        "raw_text": tc["raw_text"],
    }
    headers = {"X-API-Key": VAULT_API_KEY, "Content-Type": "application/json"}
    r = requests.post(f"{BACKEND_URL}/ingest", json=payload, headers=headers)
    return r.status_code, r.text

def query_staging(patient_id, wait=30):
    """Poll staging_vault until a row exists and appears processed or wait expires.

    Returns the most recent row for the patient (or None).
    """
    last_row = None
    for _ in range(wait):
        result = sb.table("staging_vault").select("*").eq("patient_id", patient_id).order("processed_at", desc=True).limit(1).execute()
        if result.data:
            row = result.data[0]
            last_row = row
            # Consider processed if processed_at set or status != pending
            if row.get("processed_at") or row.get("status") != "pending" or row.get("fhir_json"):
                return row
        time.sleep(1)
    return last_row

def run_tests():
    print("\n==== MULTI-CASE E2E TEST SUITE ====")
    for tc in TEST_CASES:
        print(f"\n--- {tc['desc']} ---")
        code, resp = post_ingest(tc)
        print(f"POST /ingest: {code} {resp[:80]}")
        if tc.get("expect_blocked"):
            if code == 403:
                print("✓ Privacy filter correctly blocked request.")
            else:
                print("✗ Privacy filter did NOT block as expected!")
            continue
        if code != 202:
            print("✗ /ingest did not accept request!")
            continue
        row = query_staging(tc["patient_id"])
        if not row:
            print("✗ No record found in staging_vault!")
            continue
        print(f"✓ Record found: status={row.get('status')}, model={row.get('model')}, conflict_flag={row.get('conflict_flag')}, ai_warning_msg={row.get('ai_warning_msg')}")
        if tc.get("expect_conflict") is not None:
            if row.get("conflict_flag") == tc["expect_conflict"]:
                print("✓ Conflict flag as expected.")
            else:
                print("✗ Conflict flag mismatch!")
        if row.get("ai_warning_msg"):
            print(f"⚠ AI warning: {row['ai_warning_msg']}")
        if row.get("fhir_json"):
            print(f"✓ FHIR JSON present.")
        else:
            print(f"⚠ FHIR JSON missing.")
        if row.get("processed_at"):
            print(f"✓ Processed at: {row['processed_at']}")
        else:
            print(f"⚠ Not marked processed.")

if __name__ == "__main__":
    run_tests()
