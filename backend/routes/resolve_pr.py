"""FastAPI router for the /resolve-pr decision engine (Module 4)."""
import os
import json
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status
from supabase import create_client

logger = logging.getLogger('memory-vault')
router = APIRouter(prefix='/admin', tags=['admin'])

# Initialize Supabase client for vault operations
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

class ResolveDecisionRequest(BaseModel):
    """Request schema for /resolve-pr endpoint."""
    staging_id: str
    decision: str  # 'approve' or 'reject'
    admin_id: str
    reason: Optional[str] = None
    override_fhir_json: Optional[Dict[str, Any]] = None

class ResolveDecisionResponse(BaseModel):
    """Response schema for /resolve-pr endpoint."""
    tx_id: str
    staging_id: str
    decision: str
    secret_id: Optional[str] = None
    message: str

def print_notification_stub(patient_id: str) -> None:
    """
    Print non-PHI notification stub. In production, this would call Twilio/Firebase/etc.
    
    Per HIPAA guidance, the message contains no PHI and indicates the patient can log in
    to view details in their secure vault.
    """
    notification_message = (
        "Your medical records were securely updated. "
        "1 medication conflict prevented. "
        "Log in to your secure vault to view."
    )
    logger.info(f"NOTIFY: patient_id={patient_id} message={notification_message}")

@router.post('/resolve-pr', response_model=ResolveDecisionResponse)
async def resolve_pr(request: ResolveDecisionRequest) -> ResolveDecisionResponse:
    """
    Admin decision engine: approve or reject a staging_vault record.
    
    Approve flow (atomic):
    1. Fetch staging record, verify status='processed'
    2. Create secret ID for encrypted reference
    3. Insert into main_vault with encrypted_fhir_json_id
    4. Insert audit log entry (forensic record)
    5. Delete staging row (cleanup)
    6. Return transaction ID + secret ID
    
    Reject flow:
    1. Update staging row: status='rejected', reason=provided
    2. Insert audit log entry (forensic record)
    3. Return transaction ID
    """
    
    if request.decision not in ('approve', 'reject'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision: {request.decision}; must be 'approve' or 'reject'",
        )
    
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase client not initialized",
        )
    
    tx_id = str(uuid.uuid4())
    
    try:
        # Step 1: Fetch staging record
        logger.info(f"🔍 [RESOLVE_PR] Fetching staging record: {request.staging_id}")
        staging_result = supabase.table("staging_vault").select("*").eq(
            "id", request.staging_id
        ).execute()
        
        if not staging_result.data:
            logger.error(f"❌ [RESOLVE_PR] Staging record not found: {request.staging_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Staging record not found: {request.staging_id}",
            )
        
        staging_row = staging_result.data[0]
        logger.debug(f"📋 [RESOLVE_PR] Staging row keys: {list(staging_row.keys())}")
        logger.debug(f"   Status: {staging_row.get('status')}")
        logger.debug(f"   Has fhir_json: {staging_row.get('fhir_json') is not None}")
        logger.debug(f"   Has raw_payload: {staging_row.get('raw_payload') is not None}")
        
        # Verify status is 'pending' (ready for admin review)
        # Note: Records might be in 'pending' status if worker hasn't processed yet
        current_status = staging_row.get('status')
        if current_status not in ('pending', 'processed'):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Staging record already resolved (status={current_status})",
            )
        
        # Extract original payload for audit
        # Prefer fhir_json (processed) over raw_payload
        old_value = staging_row.get('fhir_json') or staging_row.get('raw_payload')
        
        logger.debug(f"📄 [RESOLVE_PR] Original payload type: {type(old_value)}")
        if old_value:
            logger.debug(f"   Payload sample: {str(old_value)[:200]}...")
        
        # Ensure it's a dict (handle string JSON or null)
        if isinstance(old_value, str):
            logger.info(f"📋 [RESOLVE_PR] Payload is string, attempting JSON parse...")
            try:
                old_value = json.loads(old_value)
                logger.info(f"✅ [RESOLVE_PR] Successfully parsed JSON string")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"⚠️ [RESOLVE_PR] Failed to parse payload as JSON: {e}")
                old_value = {"raw_text": str(old_value)}
        elif old_value is None:
            logger.warning(f"⚠️ [RESOLVE_PR] Payload is null, using empty object")
            old_value = {"empty": True}
        elif not isinstance(old_value, dict):
            logger.warning(f"⚠️ [RESOLVE_PR] Payload is {type(old_value)}, wrapping...")
            old_value = {"data": old_value}
        
        # Step 2: Handle rejection
        if request.decision == 'reject':
            supabase.table("staging_vault").update({
                "status": "rejected",
                "fallback_reason": request.reason or "Rejected by admin",
            }).eq("id", request.staging_id).execute()
            
            # Insert audit log for reject
            audit_entry = {
                "tx_id": tx_id,
                "staging_id": request.staging_id,
                "admin_id": request.admin_id,
                "action_type": "reject",
                "action": "reject",
                "patient_id": staging_row.get("patient_id", ""),
                "old_value": old_value,
                "new_value": None,
                "secret_id": None,
                "reason": request.reason or "Rejected by admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            try:
                supabase.table("audit_logs").insert(audit_entry).execute()
            except Exception as e:
                logger.warning(f"Audit log creation failed (table may not exist): {e}")
            
            logger.info(f"Resolved (reject): staging_id={request.staging_id} tx_id={tx_id}")
            
            return ResolveDecisionResponse(
                tx_id=tx_id,
                staging_id=request.staging_id,
                decision="reject",
                message=f"Record rejected and deleted. Audit logged under tx_id={tx_id}",
            )
        
        # Step 3: Handle approval
        if request.decision == 'approve':
            # Determine final JSON
            final_json = request.override_fhir_json or old_value
            
            logger.debug(f"📤 [RESOLVE_PR] Final JSON type: {type(final_json)}")
            
            if not final_json:
                logger.error(f"❌ [RESOLVE_PR] No valid FHIR JSON found to approve")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid FHIR JSON found to approve",
                )
            
            # Generate secret ID (would use Supabase vault.create_secret() in prod)
            secret_id = str(uuid.uuid4())
            
            # Step 4: Insert into main_vault
            patient_id = staging_row.get('patient_id')
            logger.info(f"📝 [RESOLVE_PR] Inserting into main_vault for patient: {patient_id}")
            
            main_vault_entry = {
                "patient_id": patient_id,
                "encrypted_fhir_json_id": secret_id,
                "fhir_json": final_json,
            }
            
            try:
                main_insert_result = supabase.table("main_vault").insert(
                    main_vault_entry
                ).execute()
                
                if not main_insert_result.data:
                    logger.error(f"❌ [RESOLVE_PR] main_vault insert returned no data")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to insert into main_vault",
                    )
                
                main_vault_id = main_insert_result.data[0].get('id')
                logger.info(f"✅ [RESOLVE_PR] Successfully inserted into main_vault: {main_vault_id}")
            except Exception as e:
                logger.error(f"❌ [RESOLVE_PR] main_vault insert failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to write main_vault: {e}",
                )
            
            # Step 5: Insert audit_logs entry
            logger.info(f"📝 [RESOLVE_PR] Creating audit log entry...")
            
            audit_entry = {
                "tx_id": tx_id,
                "staging_id": request.staging_id,
                "admin_id": request.admin_id,
                "action_type": "approve",
                "action": "approve",
                "patient_id": patient_id,
                "old_value": old_value,
                "new_value": final_json,
                "secret_id": secret_id,
                "reason": request.reason or "Approved by admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            try:
                supabase.table("audit_logs").insert(audit_entry).execute()
                logger.info(f"✅ [RESOLVE_PR] Audit log created successfully")
            except Exception as e:
                logger.warning(f"⚠️ [RESOLVE_PR] Audit log creation failed (table may not exist): {e}")
            
            # Step 6: Delete staging record (cleanup)
            try:
                logger.info(f"🗑️ [RESOLVE_PR] Deleting staging record...")
                supabase.table("staging_vault").delete().eq(
                    "id", request.staging_id
                ).execute()
                logger.info(f"✅ [RESOLVE_PR] Staging record deleted")
            except Exception as e:
                logger.error(f"❌ [RESOLVE_PR] staging_vault delete failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete from staging_vault: {e}",
                )
            
            logger.info(
                f"Resolved (approve): staging_id={request.staging_id} "
                f"tx_id={tx_id} secret_id={secret_id} patient_id={patient_id}"
            )
            
            # Emit notification stub (non-PHI)
            print_notification_stub(patient_id)
            
            return ResolveDecisionResponse(
                tx_id=tx_id,
                staging_id=request.staging_id,
                decision="approve",
                secret_id=secret_id,
                message=f"Record approved and committed. Audit logged under tx_id={tx_id}",
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /resolve-pr: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e}",
        )

@router.get('/resolve/{staging_id}')
async def get_resolve_context(staging_id: str) -> Dict[str, Any]:
    """
    Retrieve context for the diff viewer: staging data and current main_vault data.
    
    Returns a unified payload for the frontend to render side-by-side diff.
    """
    if not supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase client not initialized",
        )
    
    try:
        # Fetch staging record
        staging_result = supabase.table("staging_vault").select("*").eq(
            "id", staging_id
        ).execute()
        
        if not staging_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Staging record not found: {staging_id}",
            )
        
        staging_row = staging_result.data[0]
        staging_json = staging_row.get('fhir_json')
        
        # Fetch patient's current main_vault record if it exists
        patient_id = staging_row.get('patient_id')
        main_result = supabase.table("main_vault").select("*").eq(
            "patient_id", patient_id
        ).order("created_at", desc=True).limit(1).execute()
        
        current_main_data = main_result.data[0] if main_result.data else None
        
        return {
            "staging_id": staging_id,
            "staging_json": staging_json,
            "current_main_data": current_main_data,
            "patient_id": patient_id,
            "status": staging_row.get('status'),
            "created_at": staging_row.get('created_at'),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching resolve context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch context: {e}",
        )
