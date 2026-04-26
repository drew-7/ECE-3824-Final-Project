
from flask import Flask, render_template, Response, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
import requests
import json


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
STREAM_URL = "http://127.0.0.1:5000/video_feed"

# ── Routes ──

# Proxy the stream
def generate_stream():
    with requests.get(STREAM_URL, stream=True) as r:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                yield chunk

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
        "right_eye": d.get("right_eye")
    } for d in docs])


## Connect server to backend!
@app.route('/')
def index():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=False, port=5050, use_reloader=False)