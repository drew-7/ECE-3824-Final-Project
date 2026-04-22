"""
seed_demo.py  –  run once to populate MongoDB with fake data so the dashboard
has something to show right away.

Usage:
    python seed_demo.py
"""
from pymongo import MongoClient
from datetime import datetime, timedelta
import random

MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
col = client["sensor_db"]["motion_events"]

labels = ["human", "human", "human", "motion", "noise"]
now = datetime.utcnow()

docs = []
for i in range(60):
    ts = now - timedelta(minutes=random.randint(0, 1440))
    docs.append({
        "timestamp": ts,
        "duration_sec": round(random.uniform(1, 45), 1),
        "label": random.choice(labels),
    })

col.insert_many(docs)
print(f"Inserted {len(docs)} demo events into sensor_db.motion_events")
