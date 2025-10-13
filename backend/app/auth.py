import os
from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from datetime import datetime, timedelta
import bcrypt
from jose import jwt
from . import db as dbmod
router = APIRouter()
JWT_SECRET = os.getenv("JWT_SECRET", "logpulssecret")
ALGORITHM = "HS256"
class LoginIn(BaseModel):
    username: str
    password: str
@router.post("/auth/login")
async def login(payload: LoginIn):
    if dbmod.db is None:
        raise HTTPException(status_code=503, detail="database not ready")
    user = await dbmod.db.users.find_one({"username": payload.username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    stored = user.get("password")
    if not bcrypt.checkpw(payload.password.encode(), stored):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    exp = datetime.utcnow() + timedelta(hours=12)
    token = jwt.encode({"sub": payload.username, "exp": int(exp.timestamp())}, JWT_SECRET, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
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
