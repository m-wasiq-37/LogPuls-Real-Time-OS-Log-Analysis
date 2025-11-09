from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .auth import router as auth_router
from .logs import router as logs_router
from .websocket import router as ws_router
from .db import connect_db, close_db
from .seed_user import initial_seed, background_fill
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
import asyncio
import sys

logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add("logs/logpuls.log", rotation="500 MB", retention="10 days")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="LogPuls API", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."}
    )

@app.get("/api/health")
async def health_check():
    try:
        await dbmod.db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

app.include_router(auth_router)
app.include_router(logs_router, prefix="/api")
app.include_router(ws_router)

@app.on_event("startup")
async def startup():
    logger.info("Starting LogPuls server...")
    try:
        await connect_db()
        logger.info("Database connection established")
        await initial_seed()
        logger.info("Initial data seeded")
        asyncio.create_task(background_fill())
        logger.info("Background tasks initialized")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down LogPuls server...")
    await close_db()
    logger.info("Database connection closed")
