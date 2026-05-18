from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_KEY')
client = create_client(SUPABASE_URL, SUPABASE_KEY)

def print_row(patient_id):
    try:
        res = client.table('staging_vault').select('*').eq('patient_id', patient_id).order('processed_at', desc=True).limit(10).execute()
    except Exception:
        res = client.table('staging_vault').select('*').eq('patient_id', patient_id).limit(10).execute()
    print('Results for', patient_id)
    for r in res.data:
        print(r)

if __name__ == '__main__':
    # Default patient to inspect; override by editing or importing
    print_row('PT-MULTI-02')
