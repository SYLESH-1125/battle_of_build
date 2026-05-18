# Backend Startup Guide

## Quick Start (Once Python is Fixed)

After `cd` to this directory, run the backend with:

```bash
# Option 1: Direct Python (recommended)
uv run python serve.py

# Option 2: Via task wrapper (Windows)
task serve
.\task.cmd serve

# Option 3: Direct uvicorn
uv run python -m uvicorn main:app --reload
```

## Files

- **serve.py**: Main entry point that imports FastAPI app and runs Uvicorn with hot reload
- **task**: Unix/Linux/Mac wrapper script (calls serve.py)
- **task.cmd**: Windows batch wrapper (calls serve.py)

## Environment Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Run the backend:
   ```bash
   uv run python serve.py
   ```

3. Access the app at: http://127.0.0.1:8000

## Known Issues

- **System Python encodings error**: The current environment has a broken Python install (missing `encodings` module). Once repaired, all commands above will work.
- **uv run task serve**: This will work once the `task` executable can be discovered properly in the system PATH or uv configuration is updated.

## Troubleshooting

If you see `ModuleNotFoundError: No module named 'encodings'`:
- Your Python installation is incomplete. Consider reinstalling Python 3.13.

If `task serve` or `task.cmd serve` doesn't work:
- Ensure you're in the `backend/` directory.
- On Windows, run `task.cmd serve` explicitly.
- Alternatively, use `uv run python serve.py` directly.
