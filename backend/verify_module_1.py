import requests
import time

BASE_URL = "http://localhost:8000"

def test_clean_payload():
    print("\n--- Test 1: The Clean Payload ---")
    payload = {
        "patient_id": "PT-123",
        "doctor_id": "DR-456",
        "raw_text": "Patient presents with severe cough. Prescribed Amoxicillin."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/ingest", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}"
        print("✅ PASS: Clean payload accepted.")
    except Exception as e:
        print(f"❌ FAIL: Test 1 errored: {e}")
        raise e

def test_blocked_payload():
    print("\n--- Test 2: The Blocked Payload ---")
    payload = {
        "patient_id": "PT-123",
        "doctor_id": "DR-456",
        "raw_text": "Patient billing code 99214. Internal psych evaluation attached."
    }
    
    try:
        response = requests.post(f"{BASE_URL}/ingest", json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
        print("✅ PASS: Blocked payload rejected appropriately.")
    except Exception as e:
        print(f"❌ FAIL: Test 2 errored: {e}")
        raise e

if __name__ == "__main__":
    print("Initiating Module 1 Automated E2E Verification...")
    # Add a short delay just in case people try to run it the second the server starts
    time.sleep(1)
    
    try:
        test_clean_payload()
        test_blocked_payload()
        print("\n🏆 ALL MODULE 1 TESTS PASSED SUCCESSFULLY! 🏆")
    except AssertionError:
        print("\n⚠️ SOME TESTS FAILED. CHECK LOGS ABOVE. ⚠️")
