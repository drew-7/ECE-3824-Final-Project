from pymongo import MongoClient


client = MongoClient("mongodb://10.109.104.9:27017")

db = client["store"]  
customers = db["customers"]

print("Number of customers: ", customers.count_documents({}))







