#!/usr/bin/env python3
"""
Quick Supabase snapshot: counts and latest rows for staging_vault, main_vault, audit_logs

Usage: python tools/check_supabase_tables.py
"""
import json
from supabase import create_client

# Supabase connection (mirrors QA harness)
SUPABASE_URL = "https://cdgcmcznmqykmzyovnmn.supabase.co"
SUPABASE_SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E"

sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

def sample_latest(table, order_by='processed_at', limit=5):
    try:
        res = sb.table(table).select('*').order(order_by, desc=True).limit(limit).execute()
        return res.data
    except Exception as e:
        return {'error': str(e)}

def count_where(table, column=None, value=None, limit=1000):
    try:
        q = sb.table(table)
        if column is not None:
            q = q.eq(column, value)
        res = q.select('id').limit(limit).execute()
        return len(res.data) if isinstance(res.data, list) else 0
    except Exception as e:
        return {'error': str(e)}

def main():
    summary = {}
    # staging_vault
    summary['staging_vault_pending_count'] = count_where('staging_vault', 'status', 'pending')
    summary['staging_vault_processing_count'] = count_where('staging_vault', 'status', 'processing')
    summary['staging_vault_failed_count'] = count_where('staging_vault', 'status', 'failed')
    summary['staging_vault_latest'] = sample_latest('staging_vault')

    # main_vault
    summary['main_vault_count_sample'] = count_where('main_vault')
    summary['main_vault_latest'] = sample_latest('main_vault', order_by='id')

    # audit_logs
    summary['audit_logs_count_sample'] = count_where('audit_logs')
    summary['audit_logs_latest'] = sample_latest('audit_logs', order_by='created_at')

    print(json.dumps(summary, indent=2, default=str))

if __name__ == '__main__':
    main()
