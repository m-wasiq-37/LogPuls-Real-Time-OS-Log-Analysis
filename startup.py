import time
import sys
import pymongo
import os

def wait_for_mongodb():
    host = os.getenv("MONGODB_HOST", "mongodb")
    port = int(os.getenv("MONGODB_PORT", "27017"))
    max_retries = 30
    retry_count = 0
    
    print("Waiting for MongoDB...")
    while retry_count < max_retries:
        try:
            client = pymongo.MongoClient(f"mongodb://{host}:{port}", serverSelectionTimeoutMS=2000)
            client.admin.command('ping')
            print("MongoDB is ready!")
            client.close()
            return True
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                print(f"  MongoDB not ready, waiting... (attempt {retry_count}/{max_retries})")
                time.sleep(2)
            else:
                print(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                return False
    
    return False

if __name__ == "__main__":
    if wait_for_mongodb():
        sys.exit(0)
    else:
        sys.exit(1)

