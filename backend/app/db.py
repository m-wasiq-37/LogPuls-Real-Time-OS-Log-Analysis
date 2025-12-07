
from pymongo import MongoClient
from typing import List, Dict, Any, Optional
import os
import sys
from datetime import datetime, timedelta
from bson import ObjectId

class MongoDB:
    def __init__(self):
        self.host = os.getenv("MONGODB_HOST", "mongodb")
        self.port = int(os.getenv("MONGODB_PORT", "27017"))
        self.database_name = os.getenv("MONGODB_DATABASE", "logpuls")
        self.collection_name = "windows_logs"

        try:
            self.client = MongoClient(f"mongodb://{self.host}:{self.port}", serverSelectionTimeoutMS=5000)

            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            self._create_indexes()
            print(f"Connected to MongoDB at {self.host}:{self.port}")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}", file=sys.stderr)
            raise

    def _create_indexes(self):
        
        try:

            self.collection.create_index("timestamp")
            self.collection.create_index("event_id")
            self.collection.create_index("level")
            self.collection.create_index("log_name")
            self.collection.create_index("provider")
            self.collection.create_index("collected_at")

            self.collection.create_index([("message", "text")])
        except Exception as e:
            print(f"Error creating indexes: {e}", file=sys.stderr)

    def insert_logs(self, logs: List[Dict[str, Any]]) -> bool:
        
        try:
            if not logs:
                return False

            result = self.collection.insert_many(logs)
            print(f"Inserted {len(result.inserted_ids)} logs into MongoDB")
            return len(result.inserted_ids) > 0
        except Exception as e:
            print(f"Error inserting logs: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False

    def get_logs(self, filters: Optional[Dict[str, Any]] = None, size: int = 1000) -> List[Dict[str, Any]]:
        
        try:
            query = {}

            if filters:
                if filters.get("log_name"):
                    query["log_name"] = filters["log_name"]

                if filters.get("level"):
                    query["level"] = filters["level"]

                if filters.get("event_id"):
                    query["event_id"] = filters["event_id"]

                if filters.get("provider"):
                    query["provider"] = {"$regex": filters["provider"], "$options": "i"}

                if filters.get("message"):
                    query["$text"] = {"$search": filters["message"]}

                if filters.get("start_date") or filters.get("end_date"):
                    date_query = {}
                    if filters.get("start_date"):
                        date_query["$gte"] = filters["start_date"]
                    if filters.get("end_date"):
                        date_query["$lte"] = filters["end_date"]
                    if date_query:
                        query["timestamp"] = date_query

            cursor = self.collection.find(query).sort("timestamp", -1).limit(size)
            logs = list(cursor)

            for log in logs:
                if "_id" in log:
                    log["_id"] = str(log["_id"])

            return logs

        except Exception as e:
            print(f"Error retrieving logs: {e}", file=sys.stderr)
            return []

    def get_log_statistics(self) -> Dict[str, Any]:
        
        try:

            total_count = self.collection.count_documents({})

            level_pipeline = [
                {"$group": {"_id": "$level", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            level_results = list(self.collection.aggregate(level_pipeline))
            by_level = {item["_id"]: item["count"] for item in level_results}

            logname_pipeline = [
                {"$group": {"_id": "$log_name", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            logname_results = list(self.collection.aggregate(logname_pipeline))
            by_log_name = {item["_id"]: item["count"] for item in logname_results}

            provider_pipeline = [
                {"$group": {"_id": "$provider", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            provider_results = list(self.collection.aggregate(provider_pipeline))
            by_provider = {item["_id"]: item["count"] for item in provider_results}

            return {
                "total_logs": total_count,
                "by_level": by_level,
                "by_log_name": by_log_name,
                "by_provider": by_provider
            }
        except Exception as e:
            print(f"Error getting statistics: {e}", file=sys.stderr)
            return {
                "total_logs": 0,
                "by_level": {},
                "by_log_name": {},
                "by_provider": {}
            }

    def delete_old_logs(self, days: int = 30) -> bool:
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = self.collection.delete_many({"timestamp": {"$lt": cutoff_date.isoformat()}})
            print(f"Deleted {result.deleted_count} old logs")
            return True
        except Exception as e:
            print(f"Error deleting old logs: {e}", file=sys.stderr)
            return False

db = MongoDB()