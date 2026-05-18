"""Configuration loader for the Vault Privacy Filter and Redis settings."""
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

def load_privacy_filter():
    try:
        base_dir = os.path.dirname(__file__)
        with open(os.path.join(base_dir, "vault_ignore.json"), "r") as f:
            patterns = json.load(f)
        return [re.compile(p, re.IGNORECASE) for p in patterns]
    except Exception as e:
        print(f"Failed to load vault_ignore.json: {e}")
        return []

PRIVACY_PATTERNS = load_privacy_filter()

def apply_privacy_filter(text: str) -> bool:
    """Return False if pattern matches (blocked), True if clean."""
    # Block empty or whitespace-only payloads explicitly
    if not text or text.strip() == "":
        return False

    for pattern in PRIVACY_PATTERNS:
        try:
            if pattern.search(text):
                return False
        except Exception:
            # If a pattern is malformed for some reason, skip it.
            continue

    return True

# Redis Configuration (Module 2)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# API Security (Module 2)
API_KEY = os.environ.get("VAULT_API_KEY", "vault-test-key-do-not-use-in-production")

