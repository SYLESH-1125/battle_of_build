#!/usr/bin/env python3
"""
Serve the FastAPI application with Uvicorn.

Run with:
  uv run python serve.py
  or: python serve.py

This script uses Uvicorn's CLI interface (via subprocess) to enable
hot reload and other advanced features.
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    # Use uvicorn CLI for proper reload support
    # This calls: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
    script_dir = Path(__file__).resolve().parent
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=str(script_dir),
    )
    sys.exit(result.returncode)
