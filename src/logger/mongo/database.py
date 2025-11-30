import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DATABASE", "log_aggregation")
COLLECTION_NAME = "logs"

async_client = AsyncIOMotorClient(MONGODB_URL)
async_db = async_client[DB_NAME]
logs_collection = async_db[COLLECTION_NAME]


sync_client = MongoClient(MONGODB_URL)
sync_db = sync_client[DB_NAME]
sync_logs_collection = sync_db[COLLECTION_NAME]