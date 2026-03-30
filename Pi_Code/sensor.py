from pymongo import MongoClient
from datetime import datetime
import random
import time

# Replace with your laptop's IP address
client = MongoClient("mongodb://192.168.1.100:27017/")

db = client["sensor_db"]
collection = db["readings"]

while True:
    data = {"timestamp": datetime.now(), "value": random.randint(0,100)}
    collection.insert_one(data)
    print("Inserted:", data)
    time.sleep(5)
