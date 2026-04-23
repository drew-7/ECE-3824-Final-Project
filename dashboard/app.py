import cv2
import mediapipe as mp
import time
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, Response
from pymongo import MongoClient

app = Flask(__name__)

# ── MongoDB Setup ─────────────────────────────────────────────────────────────
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["sensor_db"]
events_col = db["motion_events"]

# ── MediaPipe Setup ───────────────────────────────────────────────────────────
MODEL_PATH = os.path.abspath('face_landmarker.task')
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=mp.tasks.vision.RunningMode.VIDEO
)

# ── Global state (updated by generator, read by API routes) ──────────────────
current_label = "vacant"
last_event_ts = "—"

def generate_stream():
    global current_label, last_event_ts

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    last_db_write = time.time()

    with FaceLandmarker.create_from_options(options) as detector:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results = detector.detect_for_video(mp_image, int(time.time() * 1000))

            is_focused = False

            if results.face_landmarks:
                lm = results.face_landmarks[0]
                h, w, _ = frame.shape

                left_iris  = lm[468]
                right_iris = lm[473]
                is_focused = 0.35 < left_iris.x < 0.65

                # Bounding box
                xs = [p.x * w for p in lm]
                ys = [p.y * h for p in lm]
                x1 = int(min(xs)) - 15
                y1 = int(min(ys)) - 15
                x2 = int(max(xs)) + 15
                y2 = int(max(ys)) + 15
                color = (0, 229, 160) if is_focused else (255, 77, 109)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Iris dots
                cv2.circle(frame, (int(left_iris.x  * w), int(left_iris.y * h)), 5, color, -1)
                cv2.circle(frame, (int(right_iris.x * w), int(right_iris.y * h)), 5, color, -1)

            # Status bar
            label_text = "FOCUSED" if is_focused else ("DISTRACTED" if results.face_landmarks else "NO FACE")
            bar_color  = (0, 229, 160) if is_focused else (255, 77, 109)
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 48), (11, 14, 20), -1)
            cv2.putText(frame, label_text, (16, 33),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, bar_color, 2, cv2.LINE_AA)

            # Timestamp
            ts = datetime.utcnow().strftime("%H:%M:%S UTC")
            cv2.putText(frame, ts, (frame.shape[1] - 170, frame.shape[0] - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 98, 120), 1, cv2.LINE_AA)

            # Update global state
            current_label = "human" if is_focused else "distracted"

            # Write to MongoDB every 5 seconds
            if time.time() - last_db_write >= 5:
                events_col.insert_one({
                    "timestamp": datetime.utcnow(),
                    "duration_sec": 5,
                    "label": current_label
                })
                last_event_ts = datetime.utcnow().strftime("%H:%M:%S")
                last_db_write = time.time()

            # Encode and yield frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/video_feed')
def video_feed():
    return Response(
        generate_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route("/api/status")
def status():
    last = events_col.find_one(sort=[("timestamp", -1)])
    return jsonify({
        "occupied": current_label in ("human", "distracted"),
        "label": current_label,
        "last_event": last["timestamp"].strftime("%H:%M:%S") if last else "—"
    })

@app.route("/api/log")
def log():
    docs = list(events_col.find(sort=[("timestamp", -1)], limit=10))
    return jsonify([{
        "time":     d["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
        "duration": d.get("duration_sec", 5),
        "label":    d.get("label", "unknown")
    } for d in docs])

@app.route("/api/hourly")
def hourly():
    since = datetime.utcnow() - timedelta(seconds=60)
    docs = list(events_col.find({"timestamp": {"$gte": since}}).sort("timestamp", 1))
    return jsonify({
        "labels": [d["timestamp"].strftime("%H:%M:%S") for d in docs],
        "counts": [1 if d.get("label") == "human" else 0 for d in docs]
    })

@app.route("/api/total")
def total():
    count = events_col.count_documents({})
    return jsonify({"total_24h": count})

@app.route("/")
def index():
    return render_template("dashboard.html")


if __name__ == "__main__":
    print("✅ Starting Desk Security Monitor")
    print("✅ Dashboard → http://127.0.0.1:5050")
    print("✅ Camera feed → http://127.0.0.1:5050/video_feed")
    app.run(debug=False, port=5050, use_reloader=False, threaded=True)
    