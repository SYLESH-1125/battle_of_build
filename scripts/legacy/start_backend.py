#!/usr/bin/env python
"""Start backend server with proper module path"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now import and run
if __name__ == "__main__":
    try:
        from backend.main import app
        from uvicorn import run
        
        print("Starting FastAPI server on http://127.0.0.1:8000")
        run(app, host="127.0.0.1", port=8000, reload=False, log_level="info")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
