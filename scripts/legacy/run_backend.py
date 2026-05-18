#!/usr/bin/env python3
import sys
import os

# Set PYTHONPATH
os.environ["PYTHONPATH"] = "."
sys.path.insert(0, ".")

# Now start backend
if __name__ == "__main__":
    try:
        from backend.main import app
        from uvicorn import run
        
        print("✅ Backend module imported successfully")
        print("Starting FastAPI server on http://127.0.0.1:8000")
        print("=" * 60)
        
        run(
            app,
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
