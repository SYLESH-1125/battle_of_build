"""Wrapper to run the FastAPI app with correct project path when using `uv run`.

Usage:
    uv run python run_backend_uv.py
"""
from pathlib import Path
import sys
import os

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

# Importing backend.main will load configuration and app
from backend.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
