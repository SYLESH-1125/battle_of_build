import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
import os
os.chdir(str(project_root))
from ai_workers.router import simple_rule_infer

tests = [
    "Patient has penicillin allergy. Prescribed Amoxicillin.",
    "Patient is new. Prescribed Paracetamol 500mg for fever.",
    "Patient SSN: 123-45-6789. Needs checkup.",
    "",
]
for t in tests:
    print('INPUT:', t)
    print('OUTPUT:', simple_rule_infer(t, True))
    print('---')
