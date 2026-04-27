from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

### ── MongoDB Setup ─────────────────────────────────────
load_dotenv("../../.env/.env")
uri = os.getenv("MONGO_URI")
print("Connecting to MongoDB...")
client = MongoClient(uri, server_api=ServerApi('1'))



try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(e)




