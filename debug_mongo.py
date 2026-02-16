
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
print(f"Connecting to: {mongo_uri}")

try:
    client = MongoClient(mongo_uri)
    db = client["log_analyzer_db"]
    users = db["users"]
    
    count = users.count_documents({})
    print(f"Total users found: {count}")
    
    admin = users.find_one({"username": "admin"})
    if admin:
        print(f"✅ Admin user found: {admin['username']} (Role: {admin.get('role')})")
        print(f"Password stored: {admin.get('password')}")
    else:
        print("❌ Admin user NOT found. Creating it now...")
        users.insert_one({
            "username": "admin",
            "password": "admin",
            "name": "System Administrator",
            "role": "Administrator"
        })
        print("✅ Admin user created: admin / admin")

except Exception as e:
    print(f"❌ Error: {e}")
