import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
import os
os.chdir(str(project_root))
from backend.config import apply_privacy_filter

tests = [
    "Patient SSN: 123-45-6789. Needs checkup.",
    "",
    "Random note with no PHI.",
    "Patient SSN:123-45-6789",
]

for t in tests:
    print(repr(t), '->', apply_privacy_filter(t))
