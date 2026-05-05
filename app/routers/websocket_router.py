from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket import manager

router = APIRouter()

@router.websocket("/ws/calls/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: int):
    await manager.connect(websocket, call_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, call_id)
