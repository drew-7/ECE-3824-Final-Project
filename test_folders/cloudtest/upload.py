
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
import time
load_dotenv("../../.env/.env")

uri = os.getenv("MONGO_URI")

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client["EyeDataPoints"]
collection = db["LiveData"]

# Insert a document into the collection


for i in range(1000):
    result = collection.insert_one({"name": "John", "age": 30, "city": "New York"})
    print("Inserted document ID:", result.inserted_id)
    time.sleep(0.1)

# Count number of documents in the collection
print("Number of documents: ", collection.count_documents({}))