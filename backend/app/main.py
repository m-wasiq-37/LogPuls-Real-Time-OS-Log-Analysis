from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.db import db
from backend.app.auth import get_current_user, verify_password
from backend.app.logs import analyzer
from backend.app.websocket import manager, websocket_endpoint
from fastapi import WebSocket
from agent.agent import get_logs_filtered
from datetime import datetime, timedelta

app = FastAPI(title="LogPuls - Real-Time OS Log Analysis")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class LoginRequest(BaseModel):
    password: str


class LogFilters(BaseModel):
    log_name: Optional[str] = None
    level: Optional[str] = None
    event_id: Optional[int] = None
    provider: Optional[str] = None
    message: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None



@app.get("/")
async def root():
    return {
        "message": "LogPuls API",
        "status": "running",
        "frontend_url": "http://localhost:1234",
        "docs": "http://localhost:8000/docs"
    }


@app.post("/api/login")
async def login(request: LoginRequest):
    
    password = os.getenv("LOGIN_PASSWORD", "admin123")
    if request.password == password:
        return {"success": True, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")


@app.post("/api/logs/collect")
async def collect_logs(
    log_type: str = Query("All", description="Log type: System, Application, Security, All"),
    hours: int = Query(24, description="Hours to look back"),
    max_events: int = Query(1000, description="Maximum events to collect")
):
    
    try:
        filters = {
            "log_type": log_type,
            "hours": hours,
            "max_events": max_events
        }
        
        logs = get_logs_filtered(filters)
        
        if logs:
            
            success = db.insert_logs(logs)
            if success:
                
                stats = db.get_log_statistics()
                analysis = analyzer.analyze_logs(logs)
                data = {
                    "type": "logs_collected",
                    "count": len(logs),
                    "stats": stats,
                    "analysis": analysis
                }
                await manager.broadcast(str(data))
                
                return {
                    "success": True,
                    "message": f"Collected {len(logs)} logs",
                    "count": len(logs)
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to save logs to database")
        else:
            
            error_msg = "No logs collected. "
            try:
                
                test_logs = get_logs_filtered(filters)
                if not test_logs:
                    error_msg += "Log collector service may not be running. "
                    error_msg += "Check docker-compose logs for log-collector service."
            except Exception as e:
                error_msg += f"Error: {str(e)}. "
                error_msg += "Make sure log collector service is running on port 5000."
            
            return {
                "success": False,
                "message": error_msg,
                "count": 0,
                "detail": error_msg
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs/filter")
async def filter_logs(filters: LogFilters, size: int = Query(1000, description="Maximum results")):
    
    try:
        filter_dict = filters.dict(exclude_none=True)
        logs = db.get_logs(filters=filter_dict, size=size)
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
async def get_logs(
    log_name: Optional[str] = None,
    level: Optional[str] = None,
    event_id: Optional[int] = None,
    provider: Optional[str] = None,
    message: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    size: int = 1000
):
    
    try:
        filters = {}
        if log_name:
            filters["log_name"] = log_name
        if level:
            filters["level"] = level
        if event_id:
            filters["event_id"] = event_id
        if provider:
            filters["provider"] = provider
        if message:
            filters["message"] = message
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        
        logs = db.get_logs(filters=filters if filters else None, size=size)
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_statistics():
    
    try:
        stats = db.get_log_statistics()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis")
async def get_analysis(
    log_name: Optional[str] = None,
    level: Optional[str] = None,
    hours: int = 24
):
    
    try:
        
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        filters = {}
        if log_name:
            filters["log_name"] = log_name
        if level:
            filters["level"] = level
        filters["start_date"] = start_date
        filters["end_date"] = end_date
        
        logs = db.get_logs(filters=filters, size=1000)
        analysis = analyzer.analyze_logs(logs)
        
        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


@app.get("/api/health")
async def health_check():
    
    try:
        
        db.client.admin.command('ping')
        return {
            "status": "healthy",
            "mongodb": "connected"
        }
    except:
        return {
            "status": "unhealthy",
            "mongodb": "disconnected"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)