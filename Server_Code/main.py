from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI()

# 1. Host the GUI
@app.get("/")
def get_gui():
    return FileResponse("index.html")

# 2. Mock API endpoints (These provide the data to your HTML)
@app.get("/api/status")
def get_status():
    return {"occupied": True, "last_event": "14:02:10", "label": "human"}

@app.get("/api/total")
def get_total():
    return {"total_24h": 42}

@app.get("/api/hourly")
def get_hourly():
    return {"labels": [f"{i}:00" for i in range(24)], "counts": [0]*24}

@app.get("/api/log")
def get_log():
    return [{"time": "14:02:10", "duration": "5", "label": "human"}]

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    