import cv2
import time
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, Response, request
import numpy as np
from pymongo import MongoClient

app = Flask(__name__)

# ── MongoDB Setup ────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["sensor_db"]
events_col = db["motion_events"]


@app.route('/frame', methods=['POST'])

def receive_frame():
    file = request.files["frame"].read()
    
    # convert to numpy array
    np_arr = np.frombuffer(file, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # show or process
    cv2.imshow("Backend Stream", frame)
    cv2.waitKey(1)

    return "OK", 200


# ── API Routes ───────────────────────────────────────────────────────────────
@app.route("/api/status")
def status():
    last = events_col.find_one(sort=[("timestamp", -1)])
    return jsonify({
        "occupied": True, 
        "label": last.get("label", "none") if last else "none", 
        "last_event": last["timestamp"].strftime("%H:%M:%S") if last else "—"
    })

@app.route("/api/log")
def log():
    docs = list(events_col.find(sort=[("timestamp", -1)], limit=10))
    return jsonify([{"time": d["timestamp"].strftime("%H:%M:%S"), "duration": 5, "label": d.get("label")} for d in docs])

@app.route("/api/hourly")
def hourly():
    # Fetch last 12 entries (60 seconds)
    since = datetime.utcnow() - timedelta(seconds=60)
    docs = list(events_col.find({"timestamp": {"$gte": since}}).sort("timestamp", 1))
    return jsonify({
        "labels": [d["timestamp"].strftime("%H:%M:%S") for d in docs],
        "counts": [1 if d["label"] == "human" else 0 for d in docs]
    })

@app.route("/api/total")
def total():
    count = events_col.count_documents({})
    return jsonify({"total_24h": count})

@app.route("/")
def index(): return render_template("dashboard.html")

if __name__ == "__main__":  app.run(host="0.0.0.0", port=5000, debug=True)
