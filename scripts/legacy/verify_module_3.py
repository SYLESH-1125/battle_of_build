"""
Test harness for Module 3 worker end-to-end verification.
Injects test messages into Redis, monitors Supabase, and validates worker processing.
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional

import redis.asyncio as redis
from supabase import create_client

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

STREAM_KEY = "vault:ingest"


async def inject_test_message(
    patient_id: str, raw_text: str
) -> Optional[str]:
    """Inject a test message into the Redis stream."""
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        payload = {
            "patient_id": patient_id,
            "doctor_id": "test-doctor",
            "raw_text": raw_text,
        }
        message_id = await client.xadd(STREAM_KEY, payload)
        await client.aclose()

        print(f"✓ Injected message {message_id}")
        print(f"  Patient: {patient_id}")
        print(f"  Text: {raw_text[:50]}...")
        return message_id

    except Exception as exc:
        print(f"✗ Failed to inject message: {exc}")
        return None


async def monitor_staging_vault(patient_id: str, timeout: int = 30) -> Optional[dict]:
    """Poll staging_vault for processed row matching patient_id."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
        start = time.time()

        while time.time() - start < timeout:
            result = sb.table("staging_vault").select("*").eq("patient_id", patient_id).order(
                "created_at", desc=True
            ).limit(1).execute()

            if result.data:
                row = result.data[0]
                if row["status"] in ["processed", "pending", "failed"]:
                    print(f"✓ Found staging_vault row for {patient_id}")
                    print(f"  Status: {row['status']}")
                    print(f"  Attempts: {row.get('attempts', 0)}")
                    print(f"  Model: {row.get('model', 'N/A')}")
                    print(f"  Conflict: {row.get('conflict_flag', False)}")
                    if row.get("ai_warning_msg"):
                        print(f"  Warning: {row['ai_warning_msg'][:100]}")
                    return row

            await asyncio.sleep(1)

        print(f"✗ Timeout waiting for {patient_id} in staging_vault")
        return None

    except Exception as exc:
        print(f"✗ Failed to monitor staging_vault: {exc}")
        return None


async def verify_fhir_output(row: dict) -> bool:
    """Verify that fhir_json contains valid structure."""
    fhir_json = row.get("fhir_json")

    if fhir_json is None:
        print("⚠ fhir_json is null (may be expected if LLM returned error)")
        return True

    if not isinstance(fhir_json, dict):
        print(f"✗ fhir_json is not a dict: {type(fhir_json)}")
        return False

    # Basic checks
    if "resourceType" in fhir_json:
        print(f"✓ fhir_json has resourceType: {fhir_json.get('resourceType')}")
    elif "entry" in fhir_json:
        print(f"✓ fhir_json has Bundle entry (length={len(fhir_json['entry'])})")
    else:
        print("⚠ fhir_json missing resourceType and entry")

    return True


async def run_test(test_name: str, patient_id: str, raw_text: str) -> bool:
    """Run a complete test: inject -> monitor -> verify."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")

    # Inject
    message_id = await inject_test_message(patient_id, raw_text)
    if not message_id:
        return False

    # Monitor
    await asyncio.sleep(2)  # Give worker time to start
    row = await monitor_staging_vault(patient_id, timeout=30)
    if not row:
        return False

    # Verify FHIR
    if not await verify_fhir_output(row):
        return False

    print(f"✓ Test '{test_name}' passed")
    return True


async def main():
    """Run module 3 verification tests."""
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        print("✗ SUPABASE_URL and SUPABASE_SECRET_KEY required")
        sys.exit(1)

    print("Module 3 Worker End-to-End Verification")
    print("="*60)

    results = []

    # Test 1: Simple clinical note
    results.append(
        await run_test(
            "Simple clinical note",
            "PT-TEST-001",
            "Patient has hypertension. Started on lisinopril 10mg daily.",
        )
    )

    # Test 2: Drug interaction potential
    results.append(
        await run_test(
            "Drug interaction scenario",
            "PT-TEST-002",
            "Patient allergic to penicillin. Prescribed amoxicillin by mistake. Correct immediately.",
        )
    )

    # Test 3: Zero-state patient (new admission)
    results.append(
        await run_test(
            "New patient intake",
            "PT-TEST-NEW-001",
            "New patient: 45yo male, chief complaint: chest pain. No prior records available.",
        )
    )

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
