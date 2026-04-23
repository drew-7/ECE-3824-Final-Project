import cv2
import time
import mediapipe as mp
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request, Response
from pymongo import MongoClient

app = Flask(__name__)

# ── MongoDB Connection ───────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["sensor_db"]
events_col = db["motion_events"]

# ── MediaPipe Setup ──────────────────────────────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='face_landmarker.task'),
    running_mode=VisionRunningMode.VIDEO)

# ── Video Streaming Logic ────────────────────────────────────────────────────
def generate_frames():
    camera = cv2.VideoCapture(0)
    # Create the detector once outside the loop for efficiency
    with FaceLandmarker.create_from_options(options) as detector:
        while True:
            success, frame = camera.read()
            if not success: break
            
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            results = detector.detect_for_video(mp_image, int(time.time() * 1000))
            
            is_focused = True
            if results.face_landmarks:
                for landmarks in results.face_landmarks:
                    # Iris tracking (468: Left, 473: Right)
                    if not (0.35 < landmarks[468].x < 0.65):
                        is_focused = False
            
            # ── Database Event Trigger ──
            if not is_focused:
                # Log a distraction event if not already logged recently
                last_event = events_col.find_one(sort=[("timestamp", -1)])
                if not last_event or (datetime.utcnow() - last_event["timestamp"]).total_seconds() > 10:
                    events_col.insert_one({
                        "timestamp": datetime.utcnow(),
                        "duration_sec": 0,
                        "label": "distracted"
                    })
            
            # ── Stream to Browser ──
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ── API & Dashboard Routes ───────────────────────────────────────────────────

@app.route("/api/status")
def status():
    last = events_col.find_one(sort=[("timestamp", -1)])
    if last and (datetime.utcnow() - last["timestamp"]).total_seconds() < 30:
        occupied = True
        label = last.get("label", "motion")
        ts = last["timestamp"].strftime("%H:%M:%S")
    else:
        occupied = False
        label = "none"
        ts = "—"
    return jsonify({"occupied": occupied, "label": label, "last_event": ts})

@app.route("/api/log")
def log():
    docs = list(events_col.find(sort=[("timestamp", -1)], limit=10))
    rows = [{"time": d["timestamp"].strftime("%H:%M:%S"), "duration": 0, "label": d.get("label")} for d in docs]
    return jsonify(rows)

@app.route("/api/hourly")
def hourly():
    counts = [0] * 24
    return jsonify({"labels": [f"{i}h" for i in range(24)], "counts": counts})

@app.route("/api/total")
def total():
    count = events_col.count_documents({})
    return jsonify({"total_24h": count})

@app.route("/")
def index():
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=False, port=5050)
    