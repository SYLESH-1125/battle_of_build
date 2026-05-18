"""Wrapper to run the AI worker with correct project path when using `uv run`.

Usage:
    uv run python run_worker_uv.py
"""
from pathlib import Path
import sys
import os
import runpy

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

if __name__ == "__main__":
    # Run the worker as a module so relative imports like `from .router` succeed.
    runpy.run_module("ai_workers.worker", run_name="__main__")
