"""AI worker: reads pending records, calls Groq to generate FHIR JSON, updates staging_vault."""
import os
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import redis.asyncio as aioredis
from supabase import create_client
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s",
)
logger = logging.getLogger("memory-vault-worker")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY")
LLM_CLOUD_KEY = os.environ.get("LLM_CLOUD_KEY")
LLM_CLOUD_MODEL = os.environ.get("LLM_CLOUD_MODEL", "qwen/qwen3-32b")
POLL_INTERVAL = 10  # seconds between staging_vault polls

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
groq = OpenAI(
    api_key=LLM_CLOUD_KEY,
    base_url="https://api.groq.com/openai/v1",
) if LLM_CLOUD_KEY else None

FHIR_PROMPT = (
    "You are a clinical FHIR converter. Convert the following clinical note into a minimal "
    "valid FHIR R4 Bundle JSON. Return ONLY raw JSON — no markdown, no explanation, no code fences.\n\n"
    "Clinical note:\n{text}"
)


def call_groq(raw_text: str, patient_id: str) -> dict:
    if not groq or not raw_text.strip():
        return {
            "resourceType": "Bundle",
            "entry": [{"resource": {"resourceType": "Patient", "id": patient_id,
                                    "note": [{"text": "No clinical text available for processing"}]}}],
        }
    try:
        resp = groq.chat.completions.create(
            model=LLM_CLOUD_MODEL,
            messages=[{"role": "user", "content": FHIR_PROMPT.format(text=raw_text)}],
            timeout=30,
        )
        content = resp.choices[0].message.content.strip()
        # Strip markdown code fences if model adds them
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning(f"LLM returned non-JSON for patient {patient_id}, using fallback")
        return {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": patient_id}}]}
    except Exception as e:
        logger.error(f"Groq error for patient {patient_id}: {e}")
        return {"resourceType": "Bundle", "entry": [{"resource": {"resourceType": "Patient", "id": patient_id}}]}


async def drain_redis_stream(redis_client) -> int:
    """Read entries from vault:ingest stream, process each, delete on success."""
    try:
        entries = await redis_client.xread({"vault:ingest": "0-0"}, count=10, block=5000)
        if not entries:
            return 0

        processed = 0
        for _stream, records in entries:
            for msg_id, fields in records:
                patient_id = fields.get("patient_id", "unknown")
                raw_text = fields.get("raw_text", "")
                try:
                    logger.info(f"📥 [REDIS] Processing patient={patient_id}")
                    fhir = call_groq(raw_text, patient_id)
                    if supabase:
                        supabase.table("staging_vault").insert({
                            "patient_id": patient_id,
                            "raw_payload": fields,
                            "fhir_json": fhir,
                            "status": "processed",
                            "model": LLM_CLOUD_MODEL,
                        }).execute()
                    await redis_client.xdel("vault:ingest", msg_id)
                    logger.info(f"✅ [REDIS] Done patient={patient_id}")
                    processed += 1
                except Exception as e:
                    logger.error(f"❌ [REDIS] Failed msg {msg_id}: {e}")
        return processed
    except Exception as e:
        logger.warning(f"⚠️ [REDIS] Stream read error: {e}")
        return -1  # signal caller that Redis is unavailable


async def poll_staging_vault() -> int:
    """Fallback: pick up pending rows directly from staging_vault."""
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
            rid = row["id"]
            patient_id = row.get("patient_id", "unknown")
            raw_payload = row.get("raw_payload") or {}
            raw_text = raw_payload.get("raw_text", "") if isinstance(raw_payload, dict) else ""
            attempts = row.get("attempts", 0) or 0
            try:
                logger.info(f"📥 [VAULT] Processing patient={patient_id} id={rid}")
                fhir = call_groq(raw_text, patient_id)
                supabase.table("staging_vault").update({
                    "fhir_json": fhir,
                    "status": "processed",
                    "model": LLM_CLOUD_MODEL,
                    "attempts": attempts + 1,
                }).eq("id", rid).execute()
                logger.info(f"✅ [VAULT] Updated to processed: id={rid}")
                processed += 1
            except Exception as e:
                logger.error(f"❌ [VAULT] Failed id={rid}: {e}")
                supabase.table("staging_vault").update({
                    "attempts": attempts + 1,
                    "ai_warning_msg": str(e)[:500],
                }).eq("id", rid).execute()
        return processed
    except Exception as e:
        logger.error(f"❌ [VAULT] Poll error: {e}")
        return 0


async def main():
    logger.info("🚀 Memory Vault AI Worker starting...")

    redis_client = None
    use_redis = False
    try:
        redis_client = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
        await redis_client.ping()
        logger.info(f"✅ Connected to Redis")
        use_redis = True
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable, using staging_vault polling: {e}")

    while True:
        try:
            if use_redis and redis_client:
                count = await drain_redis_stream(redis_client)
                if count == -1:
                    logger.warning("⚠️ Redis failed mid-run, switching to staging_vault polling")
                    use_redis = False
                elif count == 0:
                    await asyncio.sleep(POLL_INTERVAL)
            else:
                count = await poll_staging_vault()
                if count == 0:
                    await asyncio.sleep(POLL_INTERVAL)
                else:
                    logger.info(f"✅ Batch done: {count} records processed")
        except Exception as e:
            logger.error(f"❌ Worker loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
