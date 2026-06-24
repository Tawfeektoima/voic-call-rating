import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.database import SessionLocal
from app.services.websocket import manager
from app.services.security_policy import (
    validate_websocket_security_context,
    revalidate_websocket_security,
    WebSocketSecurityError,
    record_websocket_security_close,
)
from app.config import get_settings

router = APIRouter()

@router.websocket("/ws/calls/{call_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    call_id: int,
    auth_token: Optional[str] = Query(default=None),
):
    db = SessionLocal()
    ws_security_context = None
    try:
        try:
            user, ws_security_context = validate_websocket_security_context(db, auth_token)
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

        await manager.connect(websocket, call_id)
        settings = get_settings()
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=settings.SECURITY_WS_REVALIDATION_INTERVAL_SECONDS,
                    )
                    revalidate_websocket_security(db, ws_security_context)
                except asyncio.TimeoutError:
                    revalidate_websocket_security(db, ws_security_context, force=True)
                    continue
        except WebSocketDisconnect:
            pass
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
        finally:
            manager.disconnect(websocket, call_id)
    finally:
        db.close()

