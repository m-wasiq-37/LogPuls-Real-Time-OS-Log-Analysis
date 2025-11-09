from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Body
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, validator, constr
from . import db as dbmod
from .auth import JWT_SECRET, ALGORITHM
from jose import jwt, JWTError
from .websocket import manager
from .main import limiter
from loguru import logger

class LogEntry(BaseModel):
    timestamp: Optional[str] = None
    level: constr(regex='^(INFO|WARNING|ERROR)$')
    source: constr(min_length=1, max_length=50)
    message: constr(min_length=1, max_length=1000)

    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        if v is None:
            return datetime.utcnow().isoformat()
        try:
            datetime.fromisoformat(v)
            return v
        except (TypeError, ValueError):
            raise ValueError('Invalid timestamp format. Use ISO format.')

router = APIRouter()
async def get_current_user(request: Request):
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
@router.post("/logs/ingest")
@limiter.limit("100/minute")
async def ingest_log(request: Request, log_entry: LogEntry, user: str = Depends(get_current_user)):
    try:
        if dbmod.db is None:
            raise HTTPException(status_code=503, detail="Database not ready")
        
        data = log_entry.dict()
        result = await dbmod.db.logs.insert_one(data)
        
        doc = await dbmod.db.logs.find_one({"_id": result.inserted_id})
        if not doc:
            raise HTTPException(status_code=500, detail="Failed to verify log insertion")
            
        doc["_id"] = str(doc["_id"])
        
        try:
            await manager.broadcast(doc)
        except Exception as e:
            logger.warning(f"Failed to broadcast log: {e}")
            
        logger.info(f"Log ingested: {data['level']} from {data['source']}")
        return {"status": "ok", "id": str(result.inserted_id)}
        
    except Exception as e:
        logger.error(f"Error ingesting log: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest log entry")
@router.get("/logs")
async def list_logs(level: str = None, q: str = None, source: str = None, start: str = None, end: str = None, limit: int = 200, skip: int = 0, user: str = Depends(get_current_user)):
    if dbmod.db is None:
        raise HTTPException(status_code=503, detail="database not ready")
    query = {}
    if level:
        query["level"] = level
    if q:
        query["message"] = {"$regex": q, "$options": "i"}
    if source:
        query["source"] = source
    if start and end:
        query["timestamp"] = {"$gte": start, "$lte": end}
    cursor = dbmod.db.logs.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        items.append(doc)
    return items
@router.get("/logs/stats")
async def stats(level: str = None, q: str = None, source: str = None, start: str = None, end: str = None, granularity: str = None, user: str = Depends(get_current_user)):
    if dbmod.db is None:
        raise HTTPException(status_code=503, detail="database not ready")
    match = {}
    if level:
        match["level"] = level
    if q:
        match["message"] = {"$regex": q, "$options": "i"}
    if source:
        match["source"] = source
    pipeline = []
    if match:
        pipeline.append({"$match": match})
    pipeline_lvl = pipeline + [{"$group": {"_id": "$level", "count": {"$sum": 1}}}]
    pipeline_src = pipeline + [{"$group": {"_id": "$source", "count": {"$sum": 1}}}]
    unit = "day"
    if granularity in ("minute","hour","day","month"):
        unit = granularity
    pipeline_time = []
    if start and end:
        pipeline_time.append({"$match": {"timestamp": {"$gte": start, "$lte": end}}})
    pipeline_time += [
        {"$addFields": {"ts": {"$dateFromString": {"dateString": "$timestamp"}}}},
        {"$group": {"_id": {"$dateTrunc": {"date": "$ts", "unit": unit}}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    lvl_cursor = dbmod.db.logs.aggregate(pipeline_lvl)
    src_cursor = dbmod.db.logs.aggregate(pipeline_src)
    time_cursor = dbmod.db.logs.aggregate(pipeline_time)
    levels = {}
    async for d in lvl_cursor:
        levels[d["_id"] or "UNKNOWN"] = d["count"]
    sources = {}
    async for d in src_cursor:
        sources[d["_id"] or "UNKNOWN"] = d["count"]
    times = []
    async for d in time_cursor:
        ts = d["_id"]
        times.append({"t": ts.isoformat() if hasattr(ts, "isoformat") else str(ts), "count": d["count"]})
    return {"levels": levels, "sources": sources, "times": times}
