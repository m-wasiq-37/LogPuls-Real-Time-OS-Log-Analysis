from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import List
from jose import jwt
from .auth import JWT_SECRET, ALGORITHM
router = APIRouter()
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
    async def connect(self, websocket: WebSocket, token: str = None):
        await websocket.accept()
        if token:
            try:
                jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
            except:
                await websocket.close()
                return
        else:
            await websocket.close()
            return
        self.active.append(websocket)
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)
    async def broadcast(self, message: dict):
        to_remove = []
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except:
                to_remove.append(ws)
        for ws in to_remove:
            self.disconnect(ws)
manager = ConnectionManager()
@router.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    await manager.connect(websocket, token)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
