#!/usr/bin/env python3
"""
Root-level backend starter.
Run from repo root with: uv run python start_backend.py
"""
import subprocess
import sys
import os

def main():
    # Determine the backend directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(script_dir, "backend")
    
    if not os.path.isdir(backend_dir):
        print(f"Error: backend directory not found at {backend_dir}")
        sys.exit(1)
    
    print(f"Starting backend from {backend_dir}...")
    print()
    
    # Run serve.py from the backend directory
    result = subprocess.run(
        [sys.executable, "serve.py"],
        cwd=backend_dir
    )
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
