
from flask import Flask, render_template, Response, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
import requests

## MongoDB overhead
load_dotenv("../.env/.env")
uri = os.getenv("MONGO_URI")

print("Connecting to MongoDB...")
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(e)

db = client["EyeDataPoints"]
database = db["LiveData"]


app = Flask(__name__)
STREAM_URL = "http://172.20.10.5:5000/video_feed"


# ── Routes ──

# Proxy the stream
def generate_stream():
    try:
        with requests.get(STREAM_URL, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
    except requests.exceptions.RequestException:
        return

@app.route('/video_feed')
def video_feed():
    return Response(generate_stream(),
                    content_type='multipart/x-mixed-replace; boundary=frame')


@app.route("/api/log")
def log():
    docs = list(database.find().sort("timestamp", -1))

    return jsonify([{
        "timestamp": d["timestamp"],
        "left_eye": d.get("left_eye"),
        "right_eye": d.get("right_eye"),
        "camera_error": d.get("camera_error", False),
        "focused": d.get("focused", False)
    } for d in docs])


@app.route("/api/status")
def status():
    latest = database.find_one(sort=[("timestamp", -1)])
    if not latest:
        return jsonify({"label": "unknown"})

    if latest.get("camera_error"):
        return jsonify({"label": "camera_error", "seconds_since": 0})

    now = datetime.now(timezone.utc).timestamp()
    last_ts = latest["timestamp"]
    if hasattr(last_ts, "timestamp"):
        last_ts = last_ts.timestamp()
    else:
        last_ts = datetime.fromisoformat(last_ts).timestamp()

    seconds_since = now - last_ts
    label = "focused" if seconds_since < 5 else "distracted"
    return jsonify({"label": label, "seconds_since": round(seconds_since, 2)})

## Connect server to backend!
@app.route('/')
def index():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=False, port=5000, use_reloader=False)
