from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
from backend.app.db import db
from backend.app.logs import analyzer

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            logs = db.get_logs(size=100)
            stats = db.get_log_statistics()
            analysis = analyzer.analyze_logs(logs)
            
            data = {
                "type": "update",
                "stats": stats,
                "analysis": analysis,
                "log_count": len(logs)
            }
            
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)