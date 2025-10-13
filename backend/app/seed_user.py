import os, asyncio, random, datetime
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
from dotenv import load_dotenv
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/logpuls")
ADMIN_USER = os.getenv("ADMIN_USER", "MWasiq")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1122")
async def wait_db():
    for _ in range(60):
        try:
            client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            await client.server_info()
            client.close()
            return
        except Exception:
            await asyncio.sleep(1)
    raise RuntimeError("mongo not available")
async def initial_seed():
    await wait_db()
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
    existing = await db.users.find_one({"username": ADMIN_USER})
    if not existing:
        hashed = bcrypt.hashpw(ADMIN_PASS.encode(), bcrypt.gensalt())
        await db.users.insert_one({"username": ADMIN_USER, "password": hashed})
    count = await db.logs.count_documents({})
    if count < 2000:
        levels = ["INFO","WARNING","ERROR"]
        sources = ["System","Auth","Kernel","App","Net","Service","DB","UI"]
        messages = ["Service started","Connection lost","Disk nearing capacity","User login failed","Task completed","Unexpected error occurred","Configuration updated","Permission denied","Timeout reached","Resource created","Cache cleared","Background job ran"]
        batch = []
        now = datetime.datetime.utcnow()
        for i in range(2000 - count):
            seconds_back = random.randint(0, 30*24*3600)
            dt = now - datetime.timedelta(seconds=seconds_back)
            batch.append({"timestamp": dt.isoformat(), "level": random.choice(levels), "source": random.choice(sources), "message": random.choice(messages)})
        if batch:
            await db.logs.insert_many(batch)
    client.close()
async def background_fill():
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
    target = 100000
    count = await db.logs.count_documents({})
    if count >= target:
        client.close()
        return
    levels = ["INFO","WARNING","ERROR"]
    sources = ["System","Auth","Kernel","App","Net","Service","DB","UI"]
    messages = ["Service started","Connection lost","Disk nearing capacity","User login failed","Task completed","Unexpected error occurred","Configuration updated","Permission denied","Timeout reached","Resource created","Cache cleared","Background job ran"]
    batch = []
    now = datetime.datetime.utcnow()
    remaining = target - count
    for i in range(remaining):
        seconds_back = random.randint(0, 365*24*3600)
        dt = now - datetime.timedelta(seconds=seconds_back)
        batch.append({"timestamp": dt.isoformat(), "level": random.choice(levels), "source": random.choice(sources), "message": random.choice(messages)})
        if len(batch) >= 5000:
            await db.logs.insert_many(batch)
            batch = []
    if batch:
        await db.logs.insert_many(batch)
    client.close()
