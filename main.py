from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os

app = FastAPI()

# Database Setup (Replace with your free MongoDB Atlas link later)
MONGO_DETAILS = "mongodb://localhost:27017" 
client = AsyncIOMotorClient(MONGO_DETAILS)
database = client.security_monitor
collection = database.get_collection("motion_events")

SECRET_TOKEN = "your_secret_token_123"

class MotionEvent(BaseModel):
    device_id: str
    event_type: str  # e.g., "sustained_motion"
    duration: float  # seconds

def verify_token(authorization: str = Header(None)):
    if authorization != f"Bearer {SECRET_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return authorization

@app.post("/log")
async def log_motion(data: MotionEvent, token: str = Depends(verify_token)):
    event_dict = data.dict()
    event_dict["timestamp"] = datetime.utcnow()
    
    # Store in MongoDB
    new_event = await collection.insert_one(event_dict)
    return {"status": "success", "id": str(new_event.inserted_id)}
