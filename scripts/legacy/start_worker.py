#!/usr/bin/env python
"""Start worker with proper module path"""

import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Now import and run
if __name__ == "__main__":
    try:
        print("Starting worker...")
        from ai_workers.worker import main
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
