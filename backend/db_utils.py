"""Database utilities for vault operations and transaction management."""
import os
import json
import uuid
import asyncpg
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

DB_URL = os.environ.get('SUPABASE_DB_URL')

class DBPool:
    """Global DB pool for Service Role operations."""
    pool: Optional[asyncpg.Pool] = None

async def init_db_pool() -> None:
    """Initialize the asyncpg pool for DB operations."""
    if not DB_URL:
        raise RuntimeError('SUPABASE_DB_URL not set; cannot initialize DB pool')
    DBPool.pool = await asyncpg.create_pool(
        DB_URL,
        min_size=1,
        max_size=10,
        command_timeout=30,
    )

async def close_db_pool() -> None:
    """Close the DB pool."""
    if DBPool.pool:
        await DBPool.pool.close()
        DBPool.pool = None

@asynccontextmanager
async def get_db_transaction():
    """Context manager for DB transactions."""
    if DBPool.pool is None:
        raise RuntimeError('DB pool not initialized')
    
    async with DBPool.pool.acquire() as conn:
        async with conn.transaction():
            yield conn

async def encrypt_fhir_json(payload: Dict[str, Any]) -> str:
    """
    Create a vault secret for the FHIR JSON payload and return secret_id (UUID string).
    
    IMPORTANT: This function executes vault.create_secret() which may or may not support
    transactional behavior depending on the Supabase installation. Test manually in the
    Supabase SQL editor first: SELECT * FROM vault.create_secret(name := 'test', payload := '{}'::jsonb)
    
    Returns:
        secret_id as string (UUID)
    
    Raises:
        RuntimeError if DB pool is not initialized or if vault.create_secret fails
    """
    if DBPool.pool is None:
        raise RuntimeError('DB pool not initialized')
    
    payload_json = json.dumps(payload)
    
    async with DBPool.pool.acquire() as conn:
        try:
            # Attempt to call vault.create_secret inside a transaction
            # If this fails due to extension restrictions, the compensator pattern
            # (create outside TX, use idempotency checks) should be implemented
            row = await conn.fetchrow(
                "SELECT * FROM vault.create_secret(name := $1, payload := $2::jsonb) as secret_id",
                'main_vault_record_' + str(uuid.uuid4())[:8],
                payload_json,
            )
            
            if row is None:
                raise RuntimeError('vault.create_secret returned no row')
            
            # Extract secret_id; vault returns an object with the secret_id field
            secret_id = row.get('secret_id') if hasattr(row, 'get') else row[0]
            if secret_id is None:
                raise RuntimeError('vault.create_secret returned no secret_id field')
            
            return str(secret_id)
        except Exception as e:
            raise RuntimeError(f'Failed to encrypt FHIR JSON: {e}')

async def decrypt_fhir_json(secret_id: str) -> Dict[str, Any]:
    """
    Decrypt and return the FHIR JSON payload for a given secret_id.
    
    Uses the vault.decrypted_secrets view (or equivalent) available in the Supabase project.
    This operation is auditable and should be called only by authorized backend endpoints.
    
    Args:
        secret_id: The UUID of the secret to decrypt
    
    Returns:
        Decrypted payload as a dict
    
    Raises:
        RuntimeError if DB pool is not initialized or secret not found
    """
    if DBPool.pool is None:
        raise RuntimeError('DB pool not initialized')
    
    async with DBPool.pool.acquire() as conn:
        try:
            # Query the decrypted_secrets view; adapt if your Supabase uses a different view
            row = await conn.fetchrow(
                "SELECT payload FROM vault.decrypted_secrets WHERE id = $1",
                secret_id
            )
            if row is None:
                raise RuntimeError(f'Secret not found or no access: {secret_id}')
            
            payload = row['payload']
            return payload if isinstance(payload, dict) else json.loads(payload)
        except Exception as e:
            raise RuntimeError(f'Failed to decrypt FHIR JSON: {e}')

async def get_staging_vault_for_update(staging_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve and lock a staging_vault row for update within a transaction.
    
    Must be called within a transaction context.
    
    Args:
        staging_id: UUID of the staging row
    
    Returns:
        Row as dict if found and locked, None otherwise
    """
    if DBPool.pool is None:
        raise RuntimeError('DB pool not initialized')
    
    async with DBPool.pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT * FROM staging_vault WHERE id = $1 FOR UPDATE",
                staging_id
            )
            return dict(row) if row else None

async def get_patient_main_vault(patient_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the latest main_vault record for a patient (for diff display).
    
    Args:
        patient_id: Patient identifier
    
    Returns:
        Latest main_vault row or None
    """
    if DBPool.pool is None:
        raise RuntimeError('DB pool not initialized')
    
    async with DBPool.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM main_vault WHERE patient_id = $1 ORDER BY created_at DESC LIMIT 1",
            patient_id
        )
        return dict(row) if row else None
