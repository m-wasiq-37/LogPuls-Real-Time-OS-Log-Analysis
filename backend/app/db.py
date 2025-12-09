from pymongo import MongoClient
from typing import List, Dict, Any, Optional
import os
import sys
from datetime import datetime, timedelta
from bson import ObjectId
from dateutil import parser as dateutil_parser

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
            self.collection.create_index([("timestamp", 1), ("event_id", 1), ("provider", 1)], unique=True, name="unique_log_entry")
        except Exception as e:
            print(f"Error creating indexes: {e}", file=sys.stderr)

    def insert_logs(self, logs: List[Dict[str, Any]]) -> bool:
        try:
            if not logs:
                return False

            to_insert = []
            seen = set()
            for log in logs:
                doc = dict(log)
                try:
                    ts = doc.get("timestamp")
                    if isinstance(ts, str):
                        try:
                            doc["timestamp"] = dateutil_parser.isoparse(ts)
                        except Exception:
                            pass
                    ca = doc.get("collected_at")
                    if isinstance(ca, str):
                        try:
                            doc["collected_at"] = dateutil_parser.isoparse(ca)
                        except Exception:
                            pass
                    
                    unique_key = (
                        str(doc.get("timestamp", "")),
                        str(doc.get("event_id", "")),
                        str(doc.get("provider", ""))
                    )
                    
                    if unique_key in seen:
                        continue
                    seen.add(unique_key)
                    
                    existing = self.collection.find_one({
                        "timestamp": doc.get("timestamp"),
                        "event_id": doc.get("event_id"),
                        "provider": doc.get("provider")
                    })
                    
                    if not existing:
                        to_insert.append(doc)
                except Exception:
                    pass

            if to_insert:
                try:
                    result = self.collection.insert_many(to_insert, ordered=False)
                    print(f"Inserted {len(result.inserted_ids)} new logs into MongoDB")
                    return len(result.inserted_ids) > 0
                except Exception as e:
                    if "duplicate key" in str(e).lower() or "E11000" in str(e):
                        print(f"Skipped {len(to_insert)} duplicate logs")
                        return True
                    raise
            else:
                print("No new logs to insert (all duplicates)")
                return True
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
                        try:
                            date_query["$gte"] = dateutil_parser.isoparse(filters.get("start_date"))
                        except Exception:
                            date_query["$gte"] = filters.get("start_date")
                    if filters.get("end_date"):
                        try:
                            date_query["$lte"] = dateutil_parser.isoparse(filters.get("end_date"))
                        except Exception:
                            date_query["$lte"] = filters.get("end_date")
                    if date_query:
                        query["timestamp"] = date_query

            cursor = self.collection.find(query).sort("timestamp", -1).limit(size)
            logs = list(cursor)

            for log in logs:
                if "_id" in log:
                    log["_id"] = str(log["_id"])
                try:
                    if isinstance(log.get("timestamp"), datetime):
                        log["timestamp"] = log["timestamp"].isoformat()
                except Exception:
                    pass
                try:
                    if isinstance(log.get("collected_at"), datetime):
                        log["collected_at"] = log["collected_at"].isoformat()
                except Exception:
                    pass

            return logs

        except Exception as e:
            print(f"Error retrieving logs: {e}", file=sys.stderr)
            return []

    def get_log_statistics(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                        try:
                            date_query["$gte"] = dateutil_parser.isoparse(filters.get("start_date"))
                        except Exception:
                            date_query["$gte"] = filters.get("start_date")
                    if filters.get("end_date"):
                        try:
                            date_query["$lte"] = dateutil_parser.isoparse(filters.get("end_date"))
                        except Exception:
                            date_query["$lte"] = filters.get("end_date")
                    if date_query:
                        query["timestamp"] = date_query

            total_count = self.collection.count_documents(query)

            level_pipeline = [
                {"$match": query} if query else {"$match": {}},
                {"$group": {"_id": "$level", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            level_results = list(self.collection.aggregate(level_pipeline))
            by_level = {item["_id"]: item["count"] for item in level_results}

            logname_pipeline = [
                {"$match": query} if query else {"$match": {}},
                {"$group": {"_id": "$log_name", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            logname_results = list(self.collection.aggregate(logname_pipeline))
            by_log_name = {item["_id"]: item["count"] for item in logname_results}

            provider_pipeline = [
                {"$match": query} if query else {"$match": {}},
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
            result = self.collection.delete_many({"timestamp": {"$lt": cutoff_date}})
            print(f"Deleted {result.deleted_count} old logs")
            return True
        except Exception as e:
            print(f"Error deleting old logs: {e}", file=sys.stderr)
            return False

db = MongoDB()
