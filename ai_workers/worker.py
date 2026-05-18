"""
Edge AI Worker for Memory Vault Module 3.
Consumes vault:ingest Redis stream, hydrates patient context, runs LLM inference,
validates JSON output, and writes structured FHIR data to staging_vault.
"""
import asyncio
import json
import logging
import os
import socket
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from pathlib import Path
import redis.asyncio as redis
from redis.exceptions import ResponseError
from supabase import create_client

try:
    from .router import infer_with_router
except ImportError:
    from router import infer_with_router

# Load environment variables from the project .env (ensure correct path regardless of cwd)
base_dir = Path(__file__).resolve().parents[1]
load_dotenv(base_dir / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("vault-worker")

# ============================================================================
# CONFIGURATION
# ============================================================================

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")

# Redis stream & consumer group
STREAM_KEY = "vault:ingest"
GROUP_NAME = "vault-consumer-group"
CONSUMER_NAME = f"worker-{socket.gethostname()}-{os.getpid()}"
DLQ_KEY = "vault:dead-letter"

# Worker config
MAX_ATTEMPTS = 3
CLAIM_AGE_MS = 60000  # 60 seconds
BLOCK_MS = 5000  # 5 second block for XREADGROUP
STAGING_POLL_INTERVAL = 5  # seconds between polling staging_vault when Redis unavailable

# ============================================================================
# INITIALIZATION
# ============================================================================

redis_client: Optional[redis.Redis] = None
supabase_client: Optional[Any] = None


async def init_clients() -> Tuple[redis.Redis, Any]:
    """Initialize Redis and Supabase clients."""
    global redis_client, supabase_client

    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    if SUPABASE_URL and SUPABASE_SECRET_KEY:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
    else:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY required")

    return redis_client, supabase_client


async def ensure_consumer_group() -> None:
    """Ensure Redis consumer group exists; recover pending messages."""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")

    try:
        await redis_client.xgroup_create(STREAM_KEY, GROUP_NAME, mkstream=True)
        logger.info(f"Consumer group '{GROUP_NAME}' created for stream '{STREAM_KEY}'")
    except ResponseError:
        logger.info(f"Consumer group '{GROUP_NAME}' already exists")

    # Recover any pending messages older than CLAIM_AGE_MS
    try:
        pending = await redis_client.xpending(STREAM_KEY, GROUP_NAME)
        if pending and pending[0] > 0:
            pending_ids = await redis_client.xpending_range(
                STREAM_KEY, GROUP_NAME, min="-", max="+", count=pending[0]
            )
            for msg_id_dict in pending_ids:
                msg_id = msg_id_dict["message_id"]
                idle_ms = msg_id_dict["idle_milliseconds"]
                if idle_ms > CLAIM_AGE_MS:
                    logger.warning(
                        f"Reclaiming stalled message {msg_id} (idle {idle_ms}ms)"
                    )
                    await redis_client.xclaim(
                        STREAM_KEY, GROUP_NAME, CONSUMER_NAME, CLAIM_AGE_MS, [msg_id]
                    )
    except Exception as exc:
        logger.warning(f"Error recovering pending messages: {exc}")


# ============================================================================
# IDEMPOTENCY & STATE MANAGEMENT
# ============================================================================


async def check_idempotency(ingest_id: str) -> bool:
    """
    Check if this ingest_id has already been processed.
    Returns True if already processed, False if new.
    """
    if not supabase_client or not ingest_id:
        return False

    try:
        result = supabase_client.table("staging_vault").select("id").eq(
            "ingest_id", ingest_id
        ).eq("status", "processed").execute()
        return len(result.data) > 0
    except Exception as exc:
        logger.warning(f"Idempotency check failed for {ingest_id}: {exc}")
        return False


async def mark_processing(
    ingest_id: str, patient_id: str, raw_payload: Dict[str, Any]
) -> str:
    """Insert a staging_vault row with status='processing'."""
    if not supabase_client:
        raise RuntimeError("Supabase client not initialized")

    try:
        data = {
            "ingest_id": ingest_id,
            "patient_id": patient_id,
            "raw_payload": raw_payload,
            "status": "processing",
            "attempts": 0,
        }
        result = supabase_client.table("staging_vault").insert(data).execute()
        staging_id = result.data[0]["id"] if result.data else None
        logger.info(f"Marked {ingest_id} as processing (staging_id={staging_id})")
        return staging_id
    except Exception as exc:
        logger.error(f"Failed to mark processing: {exc}")
        raise


# ============================================================================
# DLQ HANDLING
# ============================================================================


async def send_to_dlq(
    ingest_id: str,
    patient_id: str,
    raw_payload: Dict[str, Any],
    error: str,
    attempts: int,
) -> None:
    """Send a failed job to the dead-letter queue."""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")

    try:
        dlq_payload = {
            "ingest_id": ingest_id,
            "patient_id": patient_id,
            "raw_payload": json.dumps(raw_payload),
            "error": error,
            "attempts": str(attempts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await redis_client.xadd(DLQ_KEY, dlq_payload)
        logger.error(f"Sent {ingest_id} to DLQ after {attempts} attempts: {error}")
    except Exception as exc:
        logger.error(f"Failed to send to DLQ: {exc}")


async def hydrate_patient_context(patient_id: str) -> list:
    """
    Query main_vault for patient's historical records, then enrich with staging_vault data.
    Returns list of enriched records (last 20) with FHIR, raw_payload, and conflict info.
    """
    if not supabase_client:
        return []

    try:
        # Step 1: Get main_vault records
        main_result = supabase_client.table("main_vault").select("*").eq(
            "patient_id", patient_id
        ).order("created_at", desc=True).limit(20).execute()

        history = main_result.data if main_result.data else []
        
        if not history:
            logger.info(f"Hydrated 0 historical records for {patient_id}")
            return []
        
        # Step 2: Enrich each main_vault record with corresponding staging_vault data
        enriched_history = []
        for main_record in history:
            staging_id = main_record.get("encrypted_fhir_json_id")
            if staging_id:
                try:
                    staging_result = supabase_client.table("staging_vault").select("*").eq(
                        "id", staging_id
                    ).execute()
                    
                    if staging_result.data and len(staging_result.data) > 0:
                        staging_record = staging_result.data[0]
                        # Merge main_vault + staging_vault data
                        enriched = {
                            **main_record,
                            "fhir_json": staging_record.get("fhir_json"),
                            "raw_payload": staging_record.get("raw_payload"),
                            "ai_warning_msg": staging_record.get("ai_warning_msg"),
                            "conflict_flag": staging_record.get("conflict_flag"),
                            "model": staging_record.get("model"),
                        }
                        enriched_history.append(enriched)
                    else:
                        enriched_history.append(main_record)
                except Exception as e:
                    logger.warning(f"Failed to enrich record {staging_id}: {e}")
                    enriched_history.append(main_record)
            else:
                enriched_history.append(main_record)
        
        logger.info(f"Hydrated {len(enriched_history)} enriched historical records for {patient_id}")
        return enriched_history
    except Exception as exc:
        logger.warning(f"Failed to hydrate context for {patient_id}: {exc}")
        return []


# ============================================================================
# MESSAGE PROCESSING
# ============================================================================


async def process_message(message_id: str, message_data: Dict[str, str]) -> bool:
    """
    Process a single Redis message.
    Returns True if successful (ready to XACK), False if transient failure.
    """
    ingest_id = message_id
    patient_id = message_data.get("patient_id", "")
    raw_text = message_data.get("raw_text", "")

    # If this message was pulled from staging_vault, the caller should set
    # a `_staging_row_id` on message_data. In that case, reuse the staging
    # row instead of inserting another processing row.
    staging_row_id = message_data.get("_staging_row_id")
    from_staging = staging_row_id is not None

    if from_staging:
        staging_id = staging_row_id
        # Validate the staging row hasn't already been processed
        try:
            result = supabase_client.table("staging_vault").select("status").eq(
                "id", staging_id
            ).execute()
            status_val = result.data[0].get("status") if result.data else None
            if status_val == "processed":
                logger.info(f"Staging row {staging_id} already processed; skipping")
                return True
        except Exception as exc:
            logger.warning(f"Failed to verify staging status for {staging_id}: {exc}")

        # Ensure we still have required fields for processing
        if not patient_id:
            logger.error(f"Invalid staging row {staging_id}: missing patient_id")
            return False
        
        if not raw_text:
            logger.warning(f"Staging row {staging_id}: raw_text is empty, using placeholder")
            raw_text = "No clinical text available for processing"

    else:
        # Idempotency check for redis-origin messages
        if not patient_id:
            logger.error(f"Invalid message {ingest_id}: missing patient_id")
            return False
        
        if not raw_text:
            logger.error(f"Invalid message {ingest_id}: missing raw_text")
            return False

        if await check_idempotency(ingest_id):
            logger.info(f"Skipping already-processed {ingest_id}")
            return True

        # Mark as processing (create a staging_vault row)
        try:
            staging_id = await mark_processing(ingest_id, patient_id, message_data)
        except Exception as exc:
            logger.error(f"Failed to mark processing: {exc}")
            return False

    # ========================================================================
    # STEP 3: AI LOGIC — CONTEXT HYDRATION + LLM INFERENCE
    # ========================================================================

    try:
        # 1. Hydrate patient context from main_vault
        history_records = await hydrate_patient_context(patient_id)

        # 2. Call LLM router (local-first, cloud-fallback)
        logger.info(f"Invoking LLM router for {ingest_id}")
        result_json = await infer_with_router(raw_text, history_records)

        if not result_json:
            logger.error(f"LLM router returned None for {ingest_id}")
            # Return False to indicate processing failed; caller will handle
            # attempts/failure bookkeeping so we don't override staging status.
            return False

        # 3. Extract fields and update staging_vault with FHIR data
        fhir_data = result_json.get("fhir_data")
        conflict_flag = result_json.get("conflict_flag", False)
        ai_warning_msg = result_json.get("ai_warning_msg")
        model_used = result_json.get("processing_metadata", {}).get("model_used", "unknown")

        logger.info(
            f"LLM result: model={model_used}, conflict={conflict_flag}, warning={ai_warning_msg}"
        )

        # 4. Write final result to staging_vault
        supabase_client.table("staging_vault").update(
            {
                "fhir_json": fhir_data,
                "conflict_flag": conflict_flag,
                "ai_warning_msg": ai_warning_msg,
                "model": model_used,
                "status": "processed",  # processed = AI done, waiting for admin review (Module 4)
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", staging_id).execute()

        logger.info(f"Successfully processed {ingest_id}; status set to pending for review")
        return True

    except Exception as exc:
        logger.error(f"Exception during AI processing: {exc}")
        # Don't update staging here; allow caller to increment attempts.
        return False


# ============================================================================
# CONSUMER LOOP
# ============================================================================


async def consumer_loop() -> None:
    """Main consumer loop: read from Redis, process, acknowledge."""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")

    await ensure_consumer_group()

    logger.info(
        f"Starting consumer loop: stream={STREAM_KEY}, group={GROUP_NAME}, consumer={CONSUMER_NAME}"
    )

    while True:
        try:
            # Read new messages
            entries = await redis_client.xreadgroup(
                GROUP_NAME,
                CONSUMER_NAME,
                {STREAM_KEY: ">"},
                count=1,
                block=BLOCK_MS,
            )

            if not entries:
                # No new messages; try polling staging_vault for pending rows
                logger.debug("No new Redis messages; checking staging_vault for pending")
                await process_staging_vault_pending()
                continue

            # Process each message
            for stream_key, messages in entries:
                for message_id, message_data in messages:
                    logger.info(f"Processing message {message_id}")

                    try:
                        # Attempt to process
                        success = await process_message(message_id, message_data)

                        if success:
                            # Acknowledge the message
                            await redis_client.xack(STREAM_KEY, GROUP_NAME, message_id)
                            logger.info(f"Acknowledged {message_id}")
                        else:
                            # Transient failure; let PEL retry
                            logger.warning(f"Transient failure for {message_id}; will retry")

                    except Exception as exc:
                        logger.error(f"Exception processing {message_id}: {exc}")
                        # For now, acknowledge to avoid infinite loop
                        await redis_client.xack(STREAM_KEY, GROUP_NAME, message_id)

        except Exception as exc:
            logger.error(f"Consumer loop error: {exc}")
            await asyncio.sleep(5)


async def process_staging_vault_pending() -> None:
    """Poll staging_vault for rows with status='pending' from fallback inserts."""
    if not supabase_client:
        return

    try:
        result = supabase_client.table("staging_vault").select("*").eq(
            "status", "pending"
        ).limit(10).execute()

        for row in result.data:
            ingest_id = row.get("ingest_id") or row.get("id")
            patient_id = row.get("patient_id", "")
            raw_payload = row.get("raw_payload", {})

            logger.info(f"Processing pending staging_vault row {ingest_id}")

            try:
                # Mark as processing on the existing staging row
                supabase_client.table("staging_vault").update(
                    {"status": "processing"}
                ).eq("id", row["id"]).execute()

                # Flatten raw_payload to extract raw_text
                # Handle both string and dict formats
                raw_text = ""
                if isinstance(raw_payload, str):
                    raw_text = raw_payload
                elif isinstance(raw_payload, dict):
                    # Try to extract raw_text from nested payload
                    raw_text = raw_payload.get("raw_text", "")
                    if not raw_text:
                        # Fall back to clinical_note or any string value
                        for key in ["clinical_note", "note", "text", "message"]:
                            if isinstance(raw_payload.get(key), str):
                                raw_text = raw_payload[key]
                                break
                    if not raw_text:
                        # Last resort: dump the whole dict as string
                        raw_text = json.dumps(raw_payload)

                # Process using message data with raw_text extracted
                message_data = {
                    "patient_id": patient_id,
                    "raw_text": raw_text,
                    "_staging_row_id": row["id"],
                }

                success = await process_message(ingest_id, message_data)

                if success:
                    # Mark as processed
                    supabase_client.table("staging_vault").update(
                        {"status": "processed", "processed_at": datetime.now(timezone.utc).isoformat()}
                    ).eq("id", row["id"]).execute()
                    logger.info(f"Processed staging_vault row {ingest_id}")
                else:
                    # Processing failed; increment attempts and possibly move to failed
                    attempts = row.get("attempts", 0) + 1
                    if attempts >= MAX_ATTEMPTS:
                        supabase_client.table("staging_vault").update(
                            {
                                "status": "failed",
                                "attempts": attempts,
                                "ai_warning_msg": "LLM inference failed or returned invalid JSON",
                            }
                        ).eq("id", row["id"]).execute()
                        logger.error(f"Moved row {ingest_id} to failed after {attempts} attempts")
                    else:
                        supabase_client.table("staging_vault").update(
                            {"status": "pending", "attempts": attempts}
                        ).eq("id", row["id"]).execute()
                        logger.info(f"Requeued staging_vault row {ingest_id} as pending (attempts={attempts})")

            except Exception as exc:
                logger.error(f"Failed to process staging_vault row: {exc}")
                attempts = row.get("attempts", 0) + 1
                if attempts >= MAX_ATTEMPTS:
                    supabase_client.table("staging_vault").update(
                        {"status": "failed", "attempts": attempts}
                    ).eq("id", row["id"]).execute()
                    logger.error(f"Moved row {ingest_id} to failed after {attempts} attempts")
                else:
                    supabase_client.table("staging_vault").update(
                        {"attempts": attempts}
                    ).eq("id", row["id"]).execute()

    except Exception as exc:
        logger.debug(f"Error processing staging_vault pending: {exc}")


# ============================================================================
# ENTRYPOINT
# ============================================================================


async def main() -> None:
    """Main entrypoint."""
    try:
        logger.info("Initializing worker...")
        try:
            await init_clients()
            logger.info("Clients initialized successfully")
        except Exception as exc:
            logger.error(f"Redis unavailable: {exc}")
            if supabase_client:
                logger.info("Entering continuous polling loop for staging_vault (no Redis)...")
                # Continuously poll staging_vault so fallback inserts are processed
                while True:
                    try:
                        await process_staging_vault_pending()
                    except Exception as poll_exc:
                        logger.error(f"Error while polling staging_vault: {poll_exc}")
                    await asyncio.sleep(STAGING_POLL_INTERVAL)
            else:
                logger.error("Supabase client not initialized; cannot process pending records.")
            return

        # If Redis initialized, try normal consumer loop
        try:
            await consumer_loop()
        except Exception as exc:
            logger.error(f"Consumer loop failed: {exc}")
            logger.info("Falling back to continuous staging_vault polling...")
            while True:
                try:
                    await process_staging_vault_pending()
                except Exception as poll_exc:
                    logger.error(f"Error while polling staging_vault: {poll_exc}")
                await asyncio.sleep(STAGING_POLL_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
    except Exception as exc:
        logger.error(f"Fatal error: {exc}")
        raise
    finally:
        if redis_client:
            await redis_client.aclose()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
