#!/usr/bin/env python3
"""Quick Supabase diagnostics"""

import asyncio
import json
import os
from pathlib import Path

try:
    import httpx
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

def load_env():
    env_vars = {}
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_vars[k] = v
    return env_vars

env = load_env()
SUPABASE_URL = env.get("SUPABASE_URL")
SUPABASE_SECRET = env.get("SUPABASE_SECRET_KEY")

HEADERS = {
    "apikey": SUPABASE_SECRET,
    "Authorization": f"Bearer {SUPABASE_SECRET}",
    "Content-Type": "application/json"
}

print(f"Supabase URL: {SUPABASE_URL}")
print(f"Has Secret: {bool(SUPABASE_SECRET)}\n")

async def test():
    # Test staging_vault structure
    async with httpx.AsyncClient(timeout=10) as client:
        print("1. Testing staging_vault table access...")
        url = f"{SUPABASE_URL}/rest/v1/staging_vault?limit=1"
        resp = await client.get(url, headers=HEADERS)
        print(f"   Status: {resp.status_code}")
        if resp.text:
            print(f"   Response: {resp.text[:200]}")
        
        print("\n2. Testing main_vault table access...")
        url = f"{SUPABASE_URL}/rest/v1/main_vault?limit=1"
        resp = await client.get(url, headers=HEADERS)
        print(f"   Status: {resp.status_code}")
        if resp.text:
            print(f"   Response: {resp.text[:200]}")
        
        print("\n3. Testing INSERT to staging_vault...")
        url = f"{SUPABASE_URL}/rest/v1/staging_vault"
        data = {
            "patient_id": "TEST-DEBUG-001",
            "raw_payload": json.dumps({"test": "data"}),
            "status": "pending"
        }
        resp = await client.post(url, json=data, headers=HEADERS)
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text}")
        
        print("\n4. Testing INSERT to main_vault...")
        url = f"{SUPABASE_URL}/rest/v1/main_vault"
        data = {
            "patient_id": "TEST-DEBUG-002",
            "encrypted_fhir_json_id": "test-uuid-1234"
        }
        resp = await client.post(url, json=data, headers=HEADERS)
        print(f"   Status: {resp.status_code}")
        print(f"   Response: {resp.text}")

asyncio.run(test())
