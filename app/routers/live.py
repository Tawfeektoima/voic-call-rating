import uuid
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LiveSession, Employee, SystemLog
from app.schemas import SessionStartRequest, SessionStartResponse
from app.routers.auth import get_current_user, get_user_from_token
from app.services.security_policy import (
    validate_websocket_security_context,
    revalidate_websocket_security,
    WebSocketSecurityError,
    record_websocket_security_close,
)
from app.workers.asr_worker import SessionASRBuffer
from app.workers.session_flusher import flush_live_session
from app.services.gpu_router import get_best_gpu
from app.config import get_settings
from typing import Dict, Any
import asyncio

# Global storage for active ASR buffers to manage rolling audio context
active_asr_sessions: Dict[str, SessionASRBuffer] = {}

# Global storage for pending session flushes (reconnect window)
pending_flushes: Dict[str, asyncio.Task] = {}

async def background_flush(session_id: str):
    """Wait for reconnect window then flush."""
    try:
        await asyncio.sleep(60) # 60-second reconnect window
        db = SessionLocal()
        try:
            await flush_live_session(session_id, db)
        finally:
            db.close()
        if session_id in pending_flushes:
            del pending_flushes[session_id]
    except asyncio.CancelledError:
        print(f"[Live] Reconnect detected for {session_id}. Flush cancelled.")

router = APIRouter(prefix="/api/live", tags=["Live Pipeline"])

@router.post("/session/start", response_model=SessionStartResponse)
async def start_live_session(
    request: SessionStartRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Initializes a new live session for an agent.
    Verifies if the live pipeline is enabled (Phase 8).
    """
    settings = get_settings()
    if not settings.LIVE_PIPELINE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Live pipeline is currently disabled in this environment."
        )

    session_id = str(uuid.uuid4())
    reconnect_token = secrets.token_urlsafe(48)
    # 2. Dynamic GPU Session Routing (Critical Fix C-5)
    # Assign session to the healthiest/least loaded GPU
    assigned_gpu = await get_best_gpu()

    # 3. Create Session Record
    new_session = LiveSession(
        id=session_id,
        agent_id=current_user.id,
        campaign_id=request.campaign_id,
        gpu_id=assigned_gpu, # Target GPU for failover/load balancing
        reconnect_token=secrets.token_urlsafe(32)
    )
    
    db.add(new_session)
    try:
        db.commit()
        db.refresh(new_session)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize live session: {str(e)}"
        )
    
    return SessionStartResponse(
        session_id=new_session.id,
        wss_url=f"/ws/live/{new_session.id}",
        reconnect_token=new_session.reconnect_token
    )


# ---------------------------------------------------------------------------
# WebSocket Audio Ingestion (Task 2)
# ---------------------------------------------------------------------------

from fastapi import WebSocket, WebSocketDisconnect, Query
from app.database import SessionLocal

@router.websocket("/ws/live/{session_id}")
async def live_audio_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(...),
    auth_token: str | None = Query(default=None),
):
    """
    WebSocket endpoint for receiving live audio data.
    Validates the session and token before accepting.
    """
    settings = get_settings()
    if not settings.LIVE_PIPELINE_ENABLED:
        # Use Policy Violation code for disabled features
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Cancel any pending flush if the agent is reconnecting
    if session_id in pending_flushes:
        pending_flushes[session_id].cancel()

    db = SessionLocal()
    try:
        # 1. Connection Security & Validation
        session = db.query(LiveSession).filter(LiveSession.id == session_id).first()
        
        if not session or session.reconnect_token != token:
            # Unauthorized or invalid session
            record_websocket_security_close(
                db,
                close_code=4003,
                message="Live session token is invalid",
                reason_code="LIVE_SESSION_TOKEN_INVALID",
            )
            await websocket.close(code=4003)
            return

        try:
            current_user, ws_security_context = validate_websocket_security_context(db, auth_token)
        except WebSocketSecurityError as wse:
            record_websocket_security_close(
                db,
                close_code=wse.code,
                message=wse.message,
                employee_id=wse.employee_id,
                reason_code=wse.reason_code,
                audit_only=wse.audit_only,
                session_id=wse.session_id,
            )
            await websocket.close(code=wse.code)
            return
        except Exception:
            record_websocket_security_close(
                db,
                close_code=4401,
                message="Invalid token",
                reason_code="INVALID_TOKEN",
            )
            await websocket.close(code=4401)
            return

        if current_user.id != session.agent_id:
            record_websocket_security_close(
                db,
                close_code=4403,
                message="Authenticated user does not own this live session",
                employee_id=current_user.id,
                reason_code="LIVE_SESSION_ACCESS_DENIED",
            )
            await websocket.close(code=4403)
            return

        await websocket.accept()

        # Initialize ASR Buffer for this session with IDs for RAG filtering
        asr_buffer = SessionASRBuffer(
            session_id=session_id,
            campaign_id=session.campaign_id,
            company_id=1 # Mock company_id (MVP)
        )
        active_asr_sessions[session_id] = asr_buffer

        # 2. Audio Format Negotiation (Fixing C-2)
        await websocket.send_json({
            "event": "connected",
            "expected_format": "pcm_16000_16bit_mono_muxed",
            "chunk_duration_ms": 100
        })

        import time
        from app.services.agent_archive import archive_agent_chunk

        # 3. Audio Ingestion Loop
        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_bytes(),
                        timeout=settings.SECURITY_WS_REVALIDATION_INTERVAL_SECONDS
                    )
                    revalidate_websocket_security(db, ws_security_context)
                except asyncio.TimeoutError:
                    revalidate_websocket_security(db, ws_security_context, force=True)
                    continue

                # --- FIXED-OFFSET SLICER ---
                if len(data) == 6400:
                    customer_data = data[0:3200]
                    agent_data    = data[3200:6400]
                elif len(data) == 3200:
                    # Backward-compatibility: legacy single-channel packet during rollout
                    customer_data = data
                    agent_data    = bytes(3200)   # silence padding
                else:
                    continue   # reject malformed packets silently

                chunk_ts = time.time()   # Unix timestamp for post-call alignment

                # PATH A: Customer audio → ASR Worker (GPU)
                await asr_buffer.push(customer_data) # Using the existing push method which is now updated to enforce 3200 bytes

                # PATH B: Agent audio → Redis Archive (NO GPU, NO transcription)
                try:
                    await archive_agent_chunk(session_id, agent_data, chunk_ts)
                except Exception as redis_err:
                    print(f"[WS] Redis archive failed (non-fatal): {redis_err}")
                
        except WebSocketDisconnect:
            print(f"[WS] Session {session_id} disconnected normally.")
        except WebSocketSecurityError as wse:
            record_websocket_security_close(
                db,
                close_code=wse.code,
                message=wse.message,
                employee_id=wse.employee_id,
                reason_code=wse.reason_code,
                audit_only=wse.audit_only,
                session_id=wse.session_id,
            )
            try:
                await websocket.close(code=wse.code)
            except Exception:
                pass
    except Exception as e:
        import traceback
        error_msg = f"Live WS session {session_id} crashed: {str(e)}"
        print(f"[WS CRASH] Session {session_id}: {e}")
        print(traceback.format_exc())
        try:
            db_log = SessionLocal()
            log_entry = SystemLog(
                error_type="processing_failure",
                error_message=error_msg,
                severity="critical"
            )
            db_log.add(log_entry)
            db_log.commit()
            db_log.close()
        except Exception as log_err:
            print(f"[WS Logging Error] Failed to write SystemLog: {log_err}")
            
    finally:
        # Ensure buffer is flushed
        if session_id in active_asr_sessions:
            await active_asr_sessions[session_id].flush()
            del active_asr_sessions[session_id]
        
        # Start the reconnect window timer (Phase 6)
        # This will trigger the final flush and QA evaluation if the client doesn't return
        flush_task = asyncio.create_task(background_flush(session_id))
        pending_flushes[session_id] = flush_task
        
        db.close()
