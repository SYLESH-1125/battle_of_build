"""FastAPI entrypoint for the Memory Vault gateway."""
import os
import logging
from typing import Optional

from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

# Load env from .env in backend dir (local dev); Render injects env vars directly
base_dir = Path(__file__).resolve().parent
load_dotenv(base_dir / ".env")

from config import apply_privacy_filter, REDIS_URL
import re
from dependencies import verify_api_key
from routes.resolve_pr import router as resolve_pr_router

# Enhanced logging with colors for visibility
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m', # Red background
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
        record.msg = f"{log_color}[{record.levelname}]{self.RESET} {record.msg}"
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s - %(message)s'))
logging.basicConfig(level=logging.DEBUG, handlers=[handler])
logger = logging.getLogger("memory-vault")

# Silence noisy third-party loggers
for _noisy in ("httpcore", "httpx", "hpack", "hpack.hpack", "hpack.table", "httpcore.http2", "httpcore.connection"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

app = FastAPI(title="Digital Human Memory Vault - Ingest")

# Allow localhost in dev and the deployed Vercel URL set via FRONTEND_URL env var
_allowed_origins = ["http://localhost:3000"]
_frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(resolve_pr_router)


# Prefer service_role key for fallback inserts if available
SUPABASE_URL = os.environ.get("SUPABASE_URL", "mock")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY", "mock-key")

try:
    if SUPABASE_URL == "mock":
        supabase = None
    else:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None


@app.on_event("startup")
async def startup_event() -> None:
    # Initialize Redis
    logger.info("🚀 Initializing Memory Vault gateway...")
    logger.info(f"📡 Redis URL: {REDIS_URL}")
    app.state.redis = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
    )
    logger.info("✅ Startup complete: Ready to ingest clinical records")
    # Note: DB pool initialization skipped - Module 4 now uses Supabase client directly


@app.on_event("shutdown")
async def shutdown_event() -> None:
    # Close Redis
    redis_client = getattr(app.state, "redis", None)
    if redis_client is not None:
        await redis_client.aclose()

class IngestPayload(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    raw_text: str
    file_url: Optional[str] = None

@app.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_record(
    payload: IngestPayload,
    _api_key: str = Depends(verify_api_key),
):
    logger.info(f"📥 [INGEST] New record for patient_id={payload.patient_id}")
    logger.debug(f"   Raw text length: {len(payload.raw_text)} chars")
    
    # 1. Basic quick-checks to catch obvious PHI even if pattern loading failed
    if not payload.raw_text or payload.raw_text.strip() == "":
        logger.warning(f"🔒 [INGEST] Blocked: empty payload for patient_id={payload.patient_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Blocked by privacy filter: empty payload.",
        )

    # Explicit SSN detection
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", payload.raw_text):
        logger.warning(f"🔒 [INGEST] Blocked: SSN detected for patient_id={payload.patient_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Blocked by privacy filter: SSN detected.",
        )

    # 2. Run the configurable privacy filter patterns
    is_clean = apply_privacy_filter(payload.raw_text)
    if not is_clean:
        logger.warning(f"🔒 [INGEST] Blocked: privacy filter matched for patient_id={payload.patient_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Blocked by privacy filter.",
        )
    
    logger.info(f"✅ [INGEST] Privacy filter passed for patient_id={payload.patient_id}")
    
    payload_data = {
        "patient_id": payload.patient_id,
        "doctor_id": payload.doctor_id or "",
        "raw_text": payload.raw_text,
        "file_url": payload.file_url or "",
    }

    # 2. Try Redis stream first
    try:
        redis_client = getattr(app.state, "redis", None)
        if redis_client is None:
            raise RedisConnectionError("Redis client not available")

        await redis_client.xadd("vault:ingest", payload_data)
        logger.info(f"✅ [REDIS] Record queued to vault:ingest stream for patient_id={payload.patient_id}")
        return {"message": "Payload queued successfully."}
    except (RedisConnectionError, RedisTimeoutError) as error:
        logger.warning(f"⚠️  [REDIS] Unavailable: {error}")
        logger.info(f"📦 [FALLBACK] Attempting staging_vault insert for patient_id={payload.patient_id}")

        # 3. Fallback to staging_vault for worker processing
        if supabase:
            try:
                data = {
                    "patient_id": payload.patient_id,
                    "raw_payload": payload_data,
                    "status": "pending",
                    "fallback_reason": "redis_unavailable",
                    "attempts": 0,
                }
                result = supabase.table("staging_vault").insert(data).execute()
                record_id = result.data[0].get('id') if result.data else "unknown"
                logger.info(f"✅ [STAGING_VAULT] Record inserted, id={record_id}, patient_id={payload.patient_id}")
                logger.info(f"⏳ [STAGING_VAULT] Status=PENDING, waiting for worker processing...")
            except Exception as exc:
                logger.error(f"❌ [STAGING_VAULT] Insert failed: {exc}")
        else:
            logger.error(f"❌ [SUPABASE] Client is None!")

        return {"message": "Queue bypassed: Saved to staging vault for processing."}

