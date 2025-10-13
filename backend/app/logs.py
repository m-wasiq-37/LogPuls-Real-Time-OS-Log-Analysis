from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Body
from datetime import datetime
from . import db as dbmod
from .auth import JWT_SECRET, ALGORITHM
from jose import jwt, JWTError
from .websocket import manager
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
async def ingest_log(payload: dict = Body(...), user: str = Depends(get_current_user)):
    if dbmod.db is None:
        raise HTTPException(status_code=503, detail="database not ready")
    data = {
        "timestamp": payload.get("timestamp") or datetime.utcnow().isoformat(),
        "level": payload.get("level", "INFO"),
        "source": payload.get("source", "agent"),
        "message": payload.get("message", "")
    }
    result = await dbmod.db.logs.insert_one(data)
    doc = await dbmod.db.logs.find_one({"_id": result.inserted_id})
    doc["_id"] = str(doc["_id"])
    try:
        await manager.broadcast(doc)
    except:
        pass
    return {"status": "ok", "id": str(result.inserted_id)}
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
