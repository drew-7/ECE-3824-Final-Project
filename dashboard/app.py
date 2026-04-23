import cv2
import time
import mediapipe as mp
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, Response
from pymongo import MongoClient

app = Flask(__name__)

# ── MongoDB Setup ────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["sensor_db"]
events_col = db["motion_events"]

# ── AI Model Setup ───────────────────────────────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='face_landmarker.task'),
    running_mode=mp.tasks.vision.RunningMode.VIDEO)

# ── Video Streaming & AI Logic ───────────────────────────────────────────────
def generate_frames():
    camera = cv2.VideoCapture(0)
    last_db_update = time.time()
    
    with FaceLandmarker.create_from_options(options) as detector:
        while True:
            success, frame = camera.read()
            if not success: break
            
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results = detector.detect_for_video(mp_image, int(time.time() * 1000))
            
            is_focused = False
            if results.face_landmarks:
                lm = results.face_landmarks[0]
                # Iris tracking (468: Left, 473: Right)
                if 0.35 < lm[468].x < 0.65: is_focused = True
            
            # Log to DB every 5 seconds
            if (time.time() - last_db_update) >= 5:
                events_col.insert_one({
                    "timestamp": datetime.utcnow(),
                    "duration_sec": 5,
                    "label": "human" if is_focused else "distracted"
                })
                last_db_update = time.time()
            
            # Draw overlay for the live feed stream
            status_text = "HUMAN" if is_focused else "DISTRACTED"
            color = (0, 255, 0) if is_focused else (0, 0, 255)
            cv2.putText(frame, status_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed(): return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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

if __name__ == "__main__": app.run(debug=False, port=5050)
