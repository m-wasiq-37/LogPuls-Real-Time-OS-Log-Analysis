import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/logpuls")
client = None
db = None
async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.get_default_database()
async def close_db():
    global client
    if client:
        client.close()
