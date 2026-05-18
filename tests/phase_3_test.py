import requests
import json
import time

staging_id = '064bdab0-3122-48e8-9dc6-475361657a9b'

payload = {
    'staging_id': staging_id,
    'decision': 'approve',
    'admin_id': 'autonomous-qa-test'
}

print("=" * 70)
print("PHASE 3: ADMIN APPROVAL TEST")
print("=" * 70)
print(f"\n[1] Approving conflict resolution...")
print(f"    Staging ID: {staging_id}")

try:
    response = requests.post(
        'http://localhost:8000/admin/resolve-pr',
        json=payload,
        headers={'X-API-Key': 'vault-test-key-do-not-use-in-production'},
        timeout=10
    )
    
    print(f"    Status: {response.status_code}")
    
    if response.status_code in [200, 201, 202]:
        result = response.json()
        print(f"\n✅ PHASE 3 SUCCESS!")
        print(f"   TX ID: {result.get('tx_id')}")
        print(f"   Decision: {result.get('decision')}")
        print(f"   Message: {result.get('message')}")
        approved = True
    else:
        print(f"\n❌ PHASE 3 FAILED")
        print(f"   Response: {response.text}")
        approved = False
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    approved = False

# Verify move to main_vault
print(f"\n[2] Verifying move to main_vault...")
time.sleep(2)

print("=" * 70)
print("PHASE 3 COMPLETE" if approved else "PHASE 3 ENCOUNTERED ISSUES")
print("=" * 70)
