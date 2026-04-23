from pymongo import MongoClient

client = MongoClient("mongodb+srv://smlgeorgi:Michael12!@eyetrackingdata.owsc6t5.mongodb.net/")

db = client["activity_feed_db"]
collection = db["sample_events"]


print("Number of documents: ", collection.count_documents({}))








