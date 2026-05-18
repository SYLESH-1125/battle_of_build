import asyncio
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
import os
os.chdir(str(project_root))

from ai_workers.router import infer_with_router

async def run():
    tests = [
        ("Patient has penicillin allergy. Prescribed Amoxicillin.", []),
        ("Patient is new. Prescribed Paracetamol 500mg for fever.", []),
        ("Patient SSN: 123-45-6789. Needs checkup.", []),
    ]
    for text, history in tests:
        print('\nINPUT:', text)
        res = await infer_with_router(text, history)
        print('RESULT:', res)

if __name__ == '__main__':
    asyncio.run(run())
