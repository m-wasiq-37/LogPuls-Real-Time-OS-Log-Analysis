from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .auth import router as auth_router
from .logs import router as logs_router
from .websocket import router as ws_router
from .db import connect_db
from .seed_user import initial_seed, background_fill
import asyncio
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(logs_router, prefix="/api")
app.include_router(ws_router)
@app.on_event("startup")
async def startup():
    await connect_db()
    await initial_seed()
    asyncio.create_task(background_fill())
