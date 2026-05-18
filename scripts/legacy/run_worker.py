#!/usr/bin/env python3
import sys
import os
import asyncio

# Set PYTHONPATH
os.environ["PYTHONPATH"] = "."
sys.path.insert(0, ".")

# Now start worker
if __name__ == "__main__":
    try:
        from ai_workers.worker import main
        
        print("Worker module imported successfully")
        print("Starting AI Worker process...")
        print("=" * 60)
        
        asyncio.run(main())
    except ImportError as e:
        print(f"Import error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
