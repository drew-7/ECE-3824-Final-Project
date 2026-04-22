from pymongo import MongoClient

client = MongoClient("mongodb+srv://smlgeorgi:Michael12!@eyetrackingdata.owsc6t5.mongodb.net/")

db = client["activity_feed_db"]
collection = db["sample_events"]

collection.insert_one({"event": "eye_tracking_data", "data": {"left_eye": {"x": 0.5, "y": 0.5}, "right_eye": {"x": 0.6, "y": 0.5}}})









