"""
LLM Router: Local-first (llama.cpp), Cloud-fallback (Groq/Gemini).
Handles context hydration, inference, JSON validation, and repair logic.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
import httpx
from openai import AsyncOpenAI, APIError, APIConnectionError, APITimeoutError

# Load environment variables from project .env
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base_dir, ".env"))

logger = logging.getLogger("vault-router")

# ============================================================================
# CONFIGURATION
# ============================================================================

LLM_LOCAL_ENDPOINT = os.environ.get("LLM_LOCAL_ENDPOINT", "http://localhost:8080/v1")
LLM_LOCAL_TIMEOUT = float(os.environ.get("LLM_LOCAL_TIMEOUT_MS", 3000)) / 1000  # 3s

LLM_CLOUD_PROVIDER = os.environ.get("LLM_CLOUD_PROVIDER", "groq")  # groq or gemini
LLM_CLOUD_KEY = os.environ.get("LLM_CLOUD_KEY", "")
LLM_CLOUD_TIMEOUT = float(os.environ.get("LLM_CLOUD_TIMEOUT_MS", 10000)) / 1000  # 10s

PHI_TO_CLOUD_ALLOWED = os.environ.get("PHI_TO_CLOUD_ALLOWED", "true").lower() == "true"

# Semaphore to limit concurrent local inferences (resource-heavy)
LOCAL_INFERENCE_SEMAPHORE = asyncio.Semaphore(2)

# ============================================================================
# SINGLETON CLIENTS — built once to avoid httpx 0.28 proxies compat issue
# openai>=1.0 passes `proxies` to httpx which dropped that kwarg in 0.28.
# Workaround: supply our own httpx.AsyncClient so openai never touches proxies.
# ============================================================================

def _make_openai_client(base_url: str, api_key: str, timeout: float) -> AsyncOpenAI:
    """Create an AsyncOpenAI client with an explicit httpx client to bypass proxies kwarg."""
    http_client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
    return AsyncOpenAI(api_key=api_key, base_url=base_url, http_client=http_client)

_local_client: Optional[AsyncOpenAI] = None
_cloud_client: Optional[AsyncOpenAI] = None


def get_local_client() -> AsyncOpenAI:
    global _local_client
    if _local_client is None:
        _local_client = _make_openai_client(LLM_LOCAL_ENDPOINT, "not-used", LLM_LOCAL_TIMEOUT)
    return _local_client


def get_cloud_client() -> AsyncOpenAI:
    global _cloud_client
    if _cloud_client is None:
        if LLM_CLOUD_PROVIDER.lower() == "groq":
            base_url = "https://api.groq.com/openai/v1"
        else:
            base_url = os.environ.get("LLM_CLOUD_BASE_URL", "https://api.openai.com/v1")
        _cloud_client = _make_openai_client(base_url, LLM_CLOUD_KEY, LLM_CLOUD_TIMEOUT)
    return _cloud_client

# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

SYSTEM_PROMPT = """You are a Clinical Data Structurer specializing in FHIR data normalization.

INPUT: You will receive:
- context_history: Array of prior medical records (may be empty if patient_zero_state=true)
- new_text: Raw extracted text from clinical intake
- patient_zero_state: Boolean indicating if this is a new patient

OUTPUT: Return ONLY a single valid JSON object matching this exact schema. Do not include any markdown, code fences, or explanatory text. Return only the JSON:

{
  "fhir_data": {
    "resourceType": "Bundle",
    "entry": [
      {
        "resource": {
          "resourceType": "Patient" | "Condition" | "MedicationStatement" | "AllergyIntolerance" | ...,
          ... (valid FHIR fields for the resource type)
        }
      }
    ]
  } | null,
  "conflict_flag": true | false,
  "ai_warning_msg": "string explaining any issues or null if confident",
  "processing_metadata": {
    "model_used": "string",
    "model_latency_ms": number,
    "confidence_score": number between 0 and 1 or null
  }
}

Rules:
1. If you can successfully parse and structure the clinical data, populate fhir_data and set conflict_flag based on detected drug/allergy conflicts.
2. If you cannot parse (malformed input, missing critical fields), return fhir_data=null, conflict_flag=true, ai_warning_msg with reason.
3. For patient_zero_state=true: check new medications/allergies against standard medical knowledge (no historical context available).
4. For patient_zero_state=false: check new data against context_history for conflicts.
5. Always include confidence_score if you are uncertain; set ai_warning_msg to explain.
"""

USER_PROMPT_TEMPLATE = """context_history: {context_json}
patient_zero_state: {patient_zero_state}
new_text: {new_text}

Return ONLY the JSON object as specified. No commentary, no markdown."""

# ============================================================================
# CONTEXT HYDRATION
# ============================================================================


def build_patient_context(history_records: list) -> Tuple[str, bool]:
    """
    Build a JSON context string from patient's main_vault history.
    Returns (context_json, patient_zero_state).
    """
    patient_zero_state = len(history_records) == 0

    if patient_zero_state:
        context_json = json.dumps([])
    else:
        # Trim to last 10 records and serialize
        trimmed = history_records[-10:] if len(history_records) > 10 else history_records
        context_json = json.dumps(trimmed, default=str)

    return context_json, patient_zero_state


# ============================================================================
# LOCAL LLM INFERENCE (llama.cpp)
# ============================================================================


async def infer_local(
    system_prompt: str, user_prompt: str
) -> Optional[str]:
    """
    Attempt inference against local LLM endpoint (llama.cpp OpenAI-compatible).
    Returns parsed JSON string or None if failed.
    """
    async with LOCAL_INFERENCE_SEMAPHORE:
        try:
            client = get_local_client()

            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="local",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=1024,
                ),
                timeout=LLM_LOCAL_TIMEOUT,
            )

            return response.choices[0].message.content.strip()

        except asyncio.TimeoutError:
            logger.warning("Local LLM inference timed out after {:.1f}s".format(LLM_LOCAL_TIMEOUT))
            return None
        except APIConnectionError as e:
            logger.warning(f"Local LLM connection failed: {e}")
            return None
        except APITimeoutError as e:
            logger.warning(f"Local LLM timeout: {e}")
            return None
        except Exception as e:
            logger.warning(f"Local LLM inference failed: {type(e).__name__}: {e}")
            return None


# ============================================================================
# CLOUD LLM INFERENCE (Groq / Gemini)
# ============================================================================


async def infer_cloud(
    system_prompt: str, user_prompt: str
) -> Optional[str]:
    """
    Attempt inference against cloud LLM endpoint (Groq or Gemini).
    Returns parsed JSON string or None if failed.
    """
    if not PHI_TO_CLOUD_ALLOWED:
        logger.warning("PHI to cloud not allowed; skipping cloud fallback")
        return None

    try:
        client = get_cloud_client()

        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=os.environ.get("LLM_CLOUD_MODEL", "gpt-3.5-turbo"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=1024,
            ),
            timeout=LLM_CLOUD_TIMEOUT,
        )

        return response.choices[0].message.content.strip()

    except asyncio.TimeoutError:
        logger.warning(f"Cloud LLM timeout after {LLM_CLOUD_TIMEOUT}s")
        return None
    except APIError as e:
        logger.warning(f"Cloud LLM API error: {e}")
        return None
    except Exception as e:
        logger.warning(f"Cloud LLM inference failed: {type(e).__name__}: {e}")
        return None


# ============================================================================
# JSON VALIDATION & REPAIR
# ============================================================================


def validate_json_schema(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate that data matches the required schema.
    Returns (is_valid, error_message).
    """
    required_keys = {"fhir_data", "conflict_flag", "ai_warning_msg", "processing_metadata"}

    if not isinstance(data, dict):
        return False, "Response is not a JSON object"

    if not required_keys.issubset(data.keys()):
        missing = required_keys - set(data.keys())
        return False, f"Missing required keys: {missing}"

    if not isinstance(data["conflict_flag"], bool):
        return False, "conflict_flag must be boolean"

    if data["fhir_data"] is not None:
        if not isinstance(data["fhir_data"], dict):
            return False, "fhir_data must be dict or null"
        if "resourceType" not in data["fhir_data"] and "entry" not in data["fhir_data"]:
            return False, "fhir_data must contain resourceType or entry"

    if not isinstance(data.get("processing_metadata"), dict):
        return False, "processing_metadata must be dict"

    return True, None


async def attempt_json_repair(
    invalid_text: str, system_prompt: str, attempt: int = 1
) -> Optional[Dict[str, Any]]:
    """
    Attempt to repair invalid JSON by re-prompting the LLM.
    Max 2 repair attempts.
    """
    if attempt > 2:
        logger.error("JSON repair max attempts exceeded")
        return None

    repair_prompt = f"""The following response was not valid JSON. Return ONLY valid JSON matching the schema:

{invalid_text}

You MUST return only a single JSON object, no markdown, no code fences."""

    # Try local first, then cloud
    response_text = await infer_local(system_prompt, repair_prompt)
    if not response_text:
        response_text = await infer_cloud(system_prompt, repair_prompt)

    if not response_text:
        logger.error(f"Repair attempt {attempt} failed: no response from LLM")
        return None

    try:
        data = json.loads(response_text)
        is_valid, error = validate_json_schema(data)
        if is_valid:
            logger.info(f"JSON repair successful (attempt {attempt})")
            return data
        else:
            logger.warning(f"Repair attempt {attempt} produced invalid schema: {error}")
            if attempt < 2:
                return await attempt_json_repair(response_text, system_prompt, attempt + 1)
            return None
    except json.JSONDecodeError as e:
        logger.warning(f"Repair attempt {attempt} produced invalid JSON: {e}")
        if attempt < 2:
            return await attempt_json_repair(response_text, system_prompt, attempt + 1)
        return None


def simple_rule_infer(new_text: str, patient_zero_state: bool, history_records: list = None) -> Optional[Dict[str, Any]]:
    """Lightweight deterministic fallback to extract minimal FHIR-like results when LLMs fail.
    This is intentionally conservative and low-confidence; it helps testing and offline runs.
    Detects simple medication-allergy conflicts by comparing current text with historical records.
    """
    if history_records is None:
        history_records = []
        
    text = (new_text or "").lower()
    if not text.strip():
        return None

    conflict_flag = False
    ai_warning_msg = None
    fhir_data = None
    
    # Check for allergy mentions in current text
    has_allergy = "allergy" in text or "allergic" in text or "angioedema" in text
    has_ace_inhibitor_allergy = ("ace inhibitor" in text or "lisinopril" in text or "acei" in text.lower()) and has_allergy
    has_penicillin_allergy = ("penicillin" in text or "penici" in text) and has_allergy
    
    # Check for medication mentions in current text
    has_lisinopril = "lisinopril" in text
    has_amoxi = "amoxicillin" in text or "amoxi" in text
    
    # Check for conflicts with history
    if history_records and not patient_zero_state:
        # Build comprehensive history text from all available fields
        history_parts = []
        for record in history_records:
            # Convert record to string (handles dict, UUID, etc)
            if isinstance(record, dict):
                # Add patient_id and all text content
                history_parts.append(str(record.get("patient_id", "")).lower())
                # Add FHIR JSON content
                if "fhir_json" in record and record["fhir_json"]:
                    history_parts.append(json.dumps(record["fhir_json"]).lower())
                # Add other text fields
                for key in ["ai_warning_msg", "raw_payload"]:
                    if key in record and record[key]:
                        history_parts.append(str(record[key]).lower())
            else:
                history_parts.append(str(record).lower())
        
        history_text = " ".join(history_parts)
        
        # ACE Inhibitor allergy vs prior Lisinopril prescription
        if has_ace_inhibitor_allergy and ("lisinopril" in history_text or "acei" in history_text):
            conflict_flag = True
            ai_warning_msg = "CONFLICT DETECTED: Patient is allergic to ACE Inhibitors (Lisinopril). Prior prescription found in medical history. Medication review required."
        
        # Penicillin allergy vs prior Amoxicillin prescription
        elif has_penicillin_allergy and ("amoxicillin" in history_text or "amoxi" in history_text):
            conflict_flag = True
            ai_warning_msg = "CONFLICT DETECTED: Patient is allergic to Penicillin. Prior Amoxicillin prescription found."

    # Simple allergy vs medication conflict detection
    # ACE Inhibitor allergy (must check before generic Lisinopril check)
    if has_ace_inhibitor_allergy:
        fhir_data = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "AllergyIntolerance", "code": "ACE Inhibitor", "note": [{"text": new_text}]}}
            ],
        }
        if not ai_warning_msg:
            ai_warning_msg = "rule-based extraction used; low confidence"
    
    # Penicillin allergy
    elif "allergy" in text and ("penicillin" in text or "penici" in text):
        if "amoxicillin" in text or "amoxi" in text:
            conflict_flag = True
        fhir_data = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "AllergyIntolerance", "note": [{"text": new_text}]}}
            ],
        }
        if not ai_warning_msg:
            ai_warning_msg = "rule-based extraction used; low confidence"

    # Lisinopril medication
    elif has_lisinopril:
        fhir_data = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {
                    "resourceType": "MedicationRequest",
                    "medicationCodeableConcept": {"coding": [{"code": "314076", "system": "http://www.nlm.nih.gov/research/umls/rxnorm"}]},
                    "note": [{"text": new_text}]
                }}
            ],
        }
        ai_warning_msg = "rule-based extraction used; low confidence"

    # Medication extraction
    elif any(med in text for med in ("paracetamol", "acetaminophen", "ibuprofen", "amoxicillin")):
        fhir_data = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "MedicationStatement", "note": [{"text": new_text}]}}
            ],
        }
        ai_warning_msg = "rule-based medication extraction"

    else:
        # Generic Patient note
        fhir_data = {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "Patient", "note": [{"text": new_text}]}}
            ],
        }
        ai_warning_msg = "rule-based fallback used; low confidence"

    return {
        "fhir_data": fhir_data,
        "conflict_flag": conflict_flag,
        "ai_warning_msg": ai_warning_msg or "rule-based processing",
        "processing_metadata": {
            "model_used": "rule-based",
            "model_latency_ms": 0,
            "confidence_score": 0.3,
        },
    }


# ============================================================================
# MAIN ROUTER
# ============================================================================


async def infer_with_router(
    new_text: str, history_records: list, system_prompt: str = SYSTEM_PROMPT
) -> Optional[Dict[str, Any]]:
    """
    Main LLM router: local-first, cloud-fallback, with JSON validation and repair.
    Returns parsed JSON dict or None if all attempts failed.
    """
    context_json, patient_zero_state = build_patient_context(history_records)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        context_json=context_json,
        patient_zero_state=patient_zero_state,
        new_text=new_text,
    )

    logger.info(
        f"Starting inference (patient_zero_state={patient_zero_state}, context_records={len(history_records)})"
    )

    # Try local
    start_time = asyncio.get_event_loop().time()
    response_text = await infer_local(system_prompt, user_prompt)
    local_latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    if response_text:
        try:
            data = json.loads(response_text)
            is_valid, error = validate_json_schema(data)

            if is_valid:
                data["processing_metadata"]["model_used"] = "local"
                data["processing_metadata"]["model_latency_ms"] = int(local_latency_ms)
                logger.info(f"Local inference successful ({local_latency_ms:.0f}ms)")
                return data
            else:
                logger.warning(f"Local response invalid schema: {error}")
                repaired = await attempt_json_repair(response_text, system_prompt)
                if repaired:
                    repaired["processing_metadata"]["model_used"] = "local_repaired"
                    repaired["processing_metadata"]["model_latency_ms"] = int(local_latency_ms)
                    return repaired

        except json.JSONDecodeError as e:
            logger.warning(f"Local response not JSON: {e}")

    logger.info("Local inference failed or unavailable; attempting cloud fallback")

    # Try cloud
    start_time = asyncio.get_event_loop().time()
    response_text = await infer_cloud(system_prompt, user_prompt)
    cloud_latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    if response_text:
        try:
            data = json.loads(response_text)
            is_valid, error = validate_json_schema(data)

            if is_valid:
                data["processing_metadata"]["model_used"] = LLM_CLOUD_PROVIDER
                data["processing_metadata"]["model_latency_ms"] = int(cloud_latency_ms)
                logger.info(f"Cloud inference successful ({cloud_latency_ms:.0f}ms)")
                return data
            else:
                logger.warning(f"Cloud response invalid schema: {error}")
                repaired = await attempt_json_repair(response_text, system_prompt)
                if repaired:
                    repaired["processing_metadata"]["model_used"] = f"{LLM_CLOUD_PROVIDER}_repaired"
                    repaired["processing_metadata"]["model_latency_ms"] = int(cloud_latency_ms)
                    return repaired

        except json.JSONDecodeError as e:
            logger.warning(f"Cloud response not JSON: {e}")

    logger.warning("All inference attempts failed; trying rule-based fallback")
    # As a last resort, attempt a lightweight rule-based extraction so the
    # pipeline can make progress in offline or degraded environments.
    rule_result = simple_rule_infer(new_text, patient_zero_state, history_records)
    if rule_result:
        logger.info("Rule-based fallback produced a result")
        return rule_result

    logger.error("All inference attempts failed")
    return None
