"""AI worker loop — runs as a background asyncio task inside the FastAPI process."""
import os
import json
import asyncio
import logging

import redis.asyncio as aioredis
from supabase import create_client
from openai import OpenAI

logger = logging.getLogger("memory-vault-worker")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY")
LLM_CLOUD_KEY = os.environ.get("LLM_CLOUD_KEY")
LLM_CLOUD_MODEL = os.environ.get("LLM_CLOUD_MODEL", "qwen/qwen3-32b")
POLL_INTERVAL = 15

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
groq = OpenAI(
    api_key=LLM_CLOUD_KEY,
    base_url="https://api.groq.com/openai/v1",
) if LLM_CLOUD_KEY else None

FHIR_PROMPT = (
    "Convert this clinical note to a minimal valid FHIR R4 Bundle JSON. "
    "Return ONLY raw JSON — no markdown, no code fences, no explanation.\n\n"
    "Clinical note:\n{text}"
)


def call_groq(raw_text: str, patient_id: str) -> dict:
    if not groq or not raw_text.strip():
        return {
            "resourceType": "Bundle",
            "entry": [{"resource": {"resourceType": "Patient", "id": patient_id,
                                    "note": [{"text": "No clinical text provided"}]}}],
        }
    try:
        resp = groq.chat.completions.create(
            model=LLM_CLOUD_MODEL,
            messages=[{"role": "user", "content": FHIR_PROMPT.format(text=raw_text)}],
            timeout=30,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Groq/parse error for {patient_id}: {e}")
        return {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": patient_id}}]}


async def _drain_redis(redis_client) -> int:
    try:
        entries = await redis_client.xread({"vault:ingest": "0-0"}, count=10, block=3000)
        if not entries:
            return 0
        processed = 0
        for _stream, records in entries:
            for msg_id, fields in records:
                patient_id = fields.get("patient_id", "unknown")
                try:
                    fhir = call_groq(fields.get("raw_text", ""), patient_id)
                    if supabase:
                        supabase.table("staging_vault").insert({
                            "patient_id": patient_id,
                            "raw_payload": fields,
                            "fhir_json": fhir,
                            "status": "processed",
                            "model": LLM_CLOUD_MODEL,
                        }).execute()
                    await redis_client.xdel("vault:ingest", msg_id)
                    logger.info(f"✅ [WORKER] Redis processed: patient={patient_id}")
                    processed += 1
                except Exception as e:
                    logger.error(f"❌ [WORKER] Redis msg {msg_id} failed: {e}")
        return processed
    except Exception as e:
        logger.warning(f"⚠️ [WORKER] Redis read failed: {e}")
        return -1


async def _poll_staging_vault() -> int:
    if not supabase:
        return 0
    try:
        result = (
            supabase.table("staging_vault")
            .select("id, patient_id, raw_payload, attempts")
            .eq("status", "pending")
            .lt("attempts", 3)
            .limit(10)
            .execute()
        )
        if not result.data:
            return 0
        processed = 0
        for row in result.data:
            rid, patient_id = row["id"], row.get("patient_id", "unknown")
            raw_payload = row.get("raw_payload") or {}
            raw_text = raw_payload.get("raw_text", "") if isinstance(raw_payload, dict) else ""
            attempts = row.get("attempts") or 0
            try:
                fhir = call_groq(raw_text, patient_id)
                supabase.table("staging_vault").update({
                    "fhir_json": fhir,
                    "status": "processed",
                    "model": LLM_CLOUD_MODEL,
                    "attempts": attempts + 1,
                }).eq("id", rid).execute()
                logger.info(f"✅ [WORKER] Vault processed: patient={patient_id}")
                processed += 1
            except Exception as e:
                logger.error(f"❌ [WORKER] Vault row {rid} failed: {e}")
                supabase.table("staging_vault").update({
                    "attempts": attempts + 1,
                    "ai_warning_msg": str(e)[:500],
                }).eq("id", rid).execute()
        return processed
    except Exception as e:
        logger.error(f"❌ [WORKER] Vault poll error: {e}")
        return 0


async def run_worker():
    """Entry point — call this as asyncio.create_task(run_worker()) from FastAPI startup."""
    logger.info("🤖 [WORKER] Background worker starting...")

    redis_client = None
    use_redis = False
    try:
        redis_client = aioredis.from_url(
            REDIS_URL, decode_responses=True,
            socket_connect_timeout=10, socket_timeout=10,
        )
        await redis_client.ping()
        logger.info("✅ [WORKER] Redis connected")
        use_redis = True
    except Exception as e:
        logger.warning(f"⚠️ [WORKER] Redis unavailable, polling staging_vault: {e}")

    while True:
        try:
            if use_redis and redis_client:
                count = await _drain_redis(redis_client)
                if count == -1:
                    use_redis = False
                elif count == 0:
                    await asyncio.sleep(POLL_INTERVAL)
            else:
                count = await _poll_staging_vault()
                await asyncio.sleep(POLL_INTERVAL if count == 0 else 2)
        except asyncio.CancelledError:
            logger.info("🛑 [WORKER] Shutting down")
            break
        except Exception as e:
            logger.error(f"❌ [WORKER] Loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL)
