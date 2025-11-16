import os
from fastapi import APIRouter, HTTPException, Form, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
import bcrypt
from jose import jwt
from . import db as dbmod
from .main import limiter
from loguru import logger
router = APIRouter()
JWT_SECRET = os.getenv("JWT_SECRET", "logpulssecret")
ALGORITHM = "HS256"
class LoginIn(BaseModel):
    username: str
    password: str
@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginIn):
    try:
        if dbmod.db is None:
            raise HTTPException(status_code=503, detail="Database not ready")
            
        user = await dbmod.db.users.find_one({"username": payload.username})
        if not user:
            logger.warning(f"Failed login attempt for non-existent user: {payload.username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        stored = user.get("password")
        if not bcrypt.checkpw(payload.password.encode(), stored):
            logger.warning(f"Failed login attempt for user: {payload.username}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        exp = datetime.utcnow() + timedelta(hours=12)
        token_data = {
            "sub": payload.username,
            "exp": int(exp.timestamp()),
            "iat": int(datetime.utcnow().timestamp()),
            "type": "access"
        }
        
        token = jwt.encode(token_data, JWT_SECRET, algorithm=ALGORITHM)
        logger.info(f"Successful login for user: {payload.username}")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": int(timedelta(hours=12).total_seconds())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
@router.post("/auth/login_form")
async def login_form(username: str = Form(...), password: str = Form(...)):
    if dbmod.db is None:
        raise HTTPException(status_code=503, detail="database not ready")
    user = await dbmod.db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    stored = user.get("password")
    if not bcrypt.checkpw(password.encode(), stored):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    exp = datetime.utcnow() + timedelta(hours=12)
    token = jwt.encode({"sub": username, "exp": int(exp.timestamp())}, JWT_SECRET, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
