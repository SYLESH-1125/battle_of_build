"""AI worker loop — runs as a background asyncio task inside the FastAPI process."""
import os
import re
import json
import asyncio
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis
from supabase import create_client
from openai import OpenAI

logger = logging.getLogger("memory-vault-worker")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY")
LLM_CLOUD_KEY = os.environ.get("LLM_CLOUD_KEY")
LLM_CLOUD_MODEL = os.environ.get("LLM_CLOUD_MODEL", "llama-3.3-70b-versatile")
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

FHIR_PROMPT_WITH_CONTEXT = (
    "Convert this clinical note to a minimal valid FHIR R4 Bundle JSON. "
    "Return ONLY raw JSON — no markdown, no code fences, no explanation.\n\n"
    "Existing patient context (allergies and conditions already on record):\n{context}\n\n"
    "Clinical note:\n{text}"
)

# Cross-reactivity pairs: if patient has allergy to key, flag prescriptions of any value
CROSS_REACTIVITY_MAP = {
    "penicillin": ["amoxicillin", "ampicillin", "amoxicillin-clavulanate", "piperacillin", "nafcillin"],
    "sulfa": ["sulfamethoxazole", "trimethoprim-sulfamethoxazole", "bactrim"],
    "nsaid": ["ibuprofen", "naproxen", "aspirin", "celecoxib", "diclofenac"],
    "cephalosporin": ["cephalexin", "cefazolin", "ceftriaxone", "cefdinir"],
}


def _extract_json(raw: str) -> str:
    """Strip qwen3 <think> blocks and markdown fences, return bare JSON string."""
    content = raw.strip()
    # qwen3 wraps chain-of-thought in <think>...</think> before the actual answer
    if "<think>" in content and "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    elif content.startswith("<think>"):
        content = ""
    # Strip markdown code fences
    if content.startswith("```"):
        lines = content.splitlines()
        start = 1
        if len(lines) > start and lines[start].strip() in ("json", ""):
            start += 1
        end = len(lines)
        while end > start and lines[end - 1].strip() == "```":
            end -= 1
        content = "\n".join(lines[start:end]).strip()
    # Last resort: find any JSON object anywhere in the full raw response
    if not content:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            content = m.group(0)
    return content


def _get_patient_context(patient_id: str) -> str:
    """Fetch existing allergy/condition records for a patient from main_vault and staging_vault."""
    if not supabase:
        return ""
    try:
        result = (
            supabase.table("main_vault")
            .select("fhir_json")
            .eq("patient_id", patient_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        context_parts = []
        for row in (result.data or []):
            raw_fhir = row.get("fhir_json") or {}
            # Supabase may return fhir_json as a string if double-encoded on insert
            if isinstance(raw_fhir, str):
                try:
                    raw_fhir = json.loads(raw_fhir)
                except Exception:
                    raw_fhir = {}
            fhir = raw_fhir if isinstance(raw_fhir, dict) else {}
            for entry in fhir.get("entry", []):
                resource = entry.get("resource", {})
                rtype = resource.get("resourceType", "")
                if rtype == "AllergyIntolerance":
                    code = resource.get("code", {})
                    display = code.get("text") or (code.get("coding", [{}])[0].get("display", ""))
                    if display:
                        context_parts.append(f"ALLERGY: {display}")
                elif rtype == "Condition":
                    code = resource.get("code", {})
                    display = code.get("text") or (code.get("coding", [{}])[0].get("display", ""))
                    if display:
                        context_parts.append(f"CONDITION: {display}")
        return "\n".join(context_parts) if context_parts else "No prior allergies or conditions on record."
    except Exception as e:
        logger.warning(f"Context fetch failed for {patient_id}: {e}")
        return ""


def _detect_conflicts(raw_text: str, context: str) -> tuple[bool, str]:
    """Check if raw_text prescribes something that cross-reacts with known allergies in context."""
    text_lower = raw_text.lower()
    context_lower = context.lower()
    warnings = []
    for allergen, reactants in CROSS_REACTIVITY_MAP.items():
        if allergen in context_lower:
            for reactant in reactants:
                if reactant in text_lower:
                    warnings.append(
                        f"CONFLICT: Patient has known {allergen} allergy; "
                        f"{reactant} (prescribed in this note) may cause cross-reactivity."
                    )
    if warnings:
        return True, " | ".join(warnings)
    return False, ""


def call_groq(raw_text: str, patient_id: str) -> tuple[dict, bool, str]:
    """Returns (fhir_bundle, conflict_flag, ai_warning_msg)."""
    fallback = {
        "resourceType": "Bundle",
        "entry": [{"resource": {"resourceType": "Patient", "id": patient_id,
                                "note": [{"text": raw_text[:200] if raw_text else "No clinical text provided"}]}}],
    }
    context = _get_patient_context(patient_id)
    conflict_flag, ai_warning_msg = _detect_conflicts(raw_text, context)

    if not groq or not raw_text.strip():
        return fallback, conflict_flag, ai_warning_msg
    try:
        prompt = (
            FHIR_PROMPT_WITH_CONTEXT.format(text=raw_text, context=context)
            if context and context != "No prior allergies or conditions on record."
            else FHIR_PROMPT.format(text=raw_text)
        )
        resp = groq.chat.completions.create(
            model=LLM_CLOUD_MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=30,
        )
        content = _extract_json(resp.choices[0].message.content or "")
        if not content:
            raise ValueError("Empty response after stripping thinking tags")
        return json.loads(content), conflict_flag, ai_warning_msg
    except Exception as e:
        logger.warning(f"Groq/parse error for {patient_id}: {e}")
        return fallback, conflict_flag, ai_warning_msg


def _make_redis_client():
    """Create an async Redis client. Adds ssl_cert_reqs=None for Upstash TLS URLs."""
    kwargs = dict(
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
    )
    if REDIS_URL.startswith("rediss://"):
        import ssl
        kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
    return aioredis.from_url(REDIS_URL, **kwargs)


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
                    fhir, conflict_flag, ai_warning_msg = call_groq(fields.get("raw_text", ""), patient_id)
                    if supabase:
                        row = {
                            "patient_id": patient_id,
                            "raw_payload": fields,
                            "fhir_json": fhir,
                            "status": "processed",
                            "model": LLM_CLOUD_MODEL,
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                        }
                        if conflict_flag:
                            row["conflict_flag"] = True
                            row["ai_warning_msg"] = ai_warning_msg
                            logger.warning(f"⚠️ [WORKER] Conflict detected for {patient_id}: {ai_warning_msg}")
                        supabase.table("staging_vault").insert(row).execute()
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
    """Process pending + stuck-processing records from staging_vault."""
    if not supabase:
        return 0
    try:
        # Pick up pending AND old stuck-processing records (< 3 attempts)
        result = (
            supabase.table("staging_vault")
            .select("id, patient_id, raw_payload, attempts")
            .in_("status", ["pending", "processing"])
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
                fhir, conflict_flag, ai_warning_msg = call_groq(raw_text, patient_id)
                update_data = {
                    "fhir_json": fhir,
                    "status": "processed",
                    "model": LLM_CLOUD_MODEL,
                    "attempts": attempts + 1,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                }
                if conflict_flag:
                    update_data["conflict_flag"] = True
                    update_data["ai_warning_msg"] = ai_warning_msg
                    logger.warning(f"⚠️ [WORKER] Conflict detected for {patient_id}: {ai_warning_msg}")
                supabase.table("staging_vault").update(update_data).eq("id", rid).execute()
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
    """Entry point — called as asyncio.create_task(run_worker()) from FastAPI startup."""
    logger.info("🤖 [WORKER] Background worker starting...")

    redis_client = None
    use_redis = False
    try:
        redis_client = _make_redis_client()
        await redis_client.ping()
        logger.info("✅ [WORKER] Redis connected")
        use_redis = True
    except Exception as e:
        logger.warning(f"⚠️ [WORKER] Redis unavailable, using staging_vault polling: {e}")

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
                await asyncio.sleep(2 if count > 0 else POLL_INTERVAL)
        except asyncio.CancelledError:
            logger.info("🛑 [WORKER] Shutting down")
            break
        except Exception as e:
            logger.error(f"❌ [WORKER] Loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL)
