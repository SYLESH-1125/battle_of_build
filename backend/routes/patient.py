"""
Passive Flow — Patient Identity endpoints
POST /patient/enroll-biometric  → store SHA-256(face_descriptor) + optional NFC tag
GET  /patient/qr/{patient_id}   → return QR payload from patient_qr_codes (or build one from main_vault)
POST /patient/nfc-register      → associate NFC tag UID to existing patient_identities row
"""
import os
import hashlib
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from supabase import create_client

logger = logging.getLogger("memory-vault.patient")
router = APIRouter(prefix="/patient", tags=["patient"])

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None


class BiometricEnrollRequest(BaseModel):
    patient_id: str
    face_descriptor: List[float]   # 128-float L2FE embedding — never stored raw
    nfc_tag_id: Optional[str] = None
    enrolled_by: Optional[str] = None


class NfcRegisterRequest(BaseModel):
    patient_id: str
    nfc_tag_id: str
    enrolled_by: Optional[str] = None


def _face_hash(descriptor: List[float]) -> str:
    """SHA-256 of quantized descriptor. Deterministic for same face, never reversible."""
    quantized = bytes([max(0, min(255, int((max(-1.0, min(1.0, float(v))) + 1.0) / 2.0 * 255)))
                       for v in descriptor])
    return hashlib.sha256(quantized).hexdigest()


@router.post("/enroll-biometric")
async def enroll_biometric(req: BiometricEnrollRequest):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not available")

    face_hash = _face_hash(req.face_descriptor)

    row = {
        "patient_id": req.patient_id,
        "face_hash": face_hash,
        "enrolled_by": req.enrolled_by or "",
    }
    if req.nfc_tag_id:
        row["nfc_tag_id"] = req.nfc_tag_id

    try:
        supabase.table("patient_identities").upsert(row, on_conflict="patient_id").execute()
    except Exception as exc:
        logger.error("patient_identities upsert failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"DB error: {exc}")

    # Auto-generate QR payload if main_vault record exists
    vault_rows = (
        supabase.table("main_vault")
        .select("id, patient_id")
        .eq("patient_id", req.patient_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if vault_rows.data:
        vault_id = vault_rows.data[0]["id"]
        qr_payload = {
            "patient_id": req.patient_id,
            "vault_id": vault_id,
            "system": "memory-vault-v2",
        }
        try:
            supabase.table("patient_qr_codes").upsert(
                {"patient_id": req.patient_id, "qr_payload": qr_payload},
                on_conflict="patient_id"
            ).execute()
        except Exception as exc:
            logger.warning("patient_qr_codes upsert failed: %s", exc)

    logger.info("Biometric enrolled: patient=%s face_hash_prefix=%s", req.patient_id, face_hash[:8])
    return {
        "status": "enrolled",
        "patient_id": req.patient_id,
        "face_hash_prefix": face_hash[:8] + "…",
        "nfc_registered": bool(req.nfc_tag_id),
    }


@router.get("/qr/{patient_id}")
async def get_qr(patient_id: str):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not available")

    # Try patient_qr_codes first
    qr_rows = (
        supabase.table("patient_qr_codes")
        .select("*")
        .eq("patient_id", patient_id)
        .limit(1)
        .execute()
    )
    if qr_rows.data:
        return {"patient_id": patient_id, "qr_payload": qr_rows.data[0]["qr_payload"],
                "issued_at": qr_rows.data[0].get("issued_at")}

    # Fallback: build payload from latest main_vault record
    vault_rows = (
        supabase.table("main_vault")
        .select("id, patient_id, created_at")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not vault_rows.data:
        raise HTTPException(status_code=404, detail="No vault record or QR found for patient")

    vault_row = vault_rows.data[0]
    qr_payload = {
        "patient_id": patient_id,
        "vault_id": vault_row["id"],
        "system": "memory-vault-v2",
    }

    # Persist it for next time
    try:
        supabase.table("patient_qr_codes").upsert(
            {"patient_id": patient_id, "qr_payload": qr_payload},
            on_conflict="patient_id"
        ).execute()
    except Exception as exc:
        logger.warning("patient_qr_codes persist failed: %s", exc)

    return {"patient_id": patient_id, "qr_payload": qr_payload, "issued_at": vault_row["created_at"]}


@router.post("/nfc-register")
async def nfc_register(req: NfcRegisterRequest):
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not available")

    # Upsert — creates row if not enrolled yet (NFC-first flow)
    try:
        supabase.table("patient_identities").upsert({
            "patient_id": req.patient_id,
            "face_hash": "",          # empty until biometric enrolled
            "nfc_tag_id": req.nfc_tag_id,
            "enrolled_by": req.enrolled_by or "",
        }, on_conflict="patient_id").execute()
    except Exception as exc:
        logger.error("nfc_register upsert failed: %s", exc)
        raise HTTPException(status_code=503, detail=f"DB error: {exc}")

    logger.info("NFC registered: patient=%s tag=%s", req.patient_id, req.nfc_tag_id)
    return {"status": "registered", "patient_id": req.patient_id, "nfc_tag_id": req.nfc_tag_id}


@router.get("/identity/{patient_id}")
async def get_identity(patient_id: str):
    """Returns enrollment status for a patient — used by Active Flow to check what methods are available."""
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase not available")

    rows = (
        supabase.table("patient_identities")
        .select("patient_id, face_hash, nfc_tag_id, enrolled_at")
        .eq("patient_id", patient_id)
        .limit(1)
        .execute()
    )
    if not rows.data:
        return {"patient_id": patient_id, "enrolled": False}

    row = rows.data[0]
    return {
        "patient_id": patient_id,
        "enrolled": True,
        "has_face": bool(row.get("face_hash")),
        "has_nfc": bool(row.get("nfc_tag_id")),
        "enrolled_at": row.get("enrolled_at"),
    }
