from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.database import SessionLocal
from app.routers.auth import get_user_from_token
from app.services.websocket import manager

router = APIRouter()

@router.websocket("/ws/calls/{call_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    call_id: int,
    auth_token: Optional[str] = Query(default=None),
):
    db = SessionLocal()
    try:
        if not auth_token:
            await websocket.close(code=4401)
            return

        try:
            user = get_user_from_token(auth_token, db)
        except Exception:
            await websocket.close(code=4401)
            return

        if (user.status or "").lower() != "active":
            await websocket.close(code=4403)
            return

        await manager.connect(websocket, call_id)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket, call_id)
    finally:
        db.close()
