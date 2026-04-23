import cv2
import mediapipe as mp
import time
import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, Response
from pymongo import MongoClient
import threading

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

# ── Shared Camera State ───────────────────────────────────────────────────────
# One camera instance, one detector — shared across all requests via a lock
camera_lock = threading.Lock()
latest_frame = None          # latest JPEG bytes to stream
current_label = "vacant"     # "human" | "distracted"
last_event_time = "—"

def camera_loop():
    """Background thread: reads camera, runs MediaPipe, writes to MongoDB every 5s."""
    global latest_frame, current_label, last_event_time

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("❌ Camera not found. Check USB connection.")
        return

    last_db_write = time.time()

    with FaceLandmarker.create_from_options(options) as detector:
        while True:
            success, frame = cap.read()
            if not success:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Run detection
            results = detector.detect_for_video(mp_image, int(time.time() * 1000))

            is_focused = False

            if results.face_landmarks:
                lm = results.face_landmarks[0]
                h, w, _ = frame.shape

                # Iris landmarks 468 (left) and 473 (right)
                left_iris  = lm[468]
                right_iris = lm[473]
                is_focused = 0.35 < left_iris.x < 0.65

                # Draw face bounding box
                xs = [p.x * w for p in lm]
                ys = [p.y * h for p in lm]
                x1, y1 = int(min(xs)) - 15, int(min(ys)) - 15
                x2, y2 = int(max(xs)) + 15, int(max(ys)) + 15
                color = (0, 229, 160) if is_focused else (255, 77, 109)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Draw iris dots
                cv2.circle(frame, (int(left_iris.x  * w), int(left_iris.y  * h)), 5, color, -1)
                cv2.circle(frame, (int(right_iris.x * w), int(right_iris.y * h)), 5, color, -1)

            # Status bar overlay
            label_text = "FOCUSED" if is_focused else ("DISTRACTED" if results.face_landmarks else "NO FACE")
            bar_color  = (0, 229, 160) if is_focused else (77, 109, 255) if not results.face_landmarks else (255, 77, 109)
            cv2.rectangle(frame, (0, 0), (frame.shape[1], 48), (11, 14, 20), -1)
            cv2.putText(frame, label_text, (16, 33),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, bar_color, 2, cv2.LINE_AA)

            # Timestamp bottom-right
            ts = datetime.utcnow().strftime("%H:%M:%S UTC")
            cv2.putText(frame, ts, (frame.shape[1] - 170, frame.shape[0] - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 98, 120), 1, cv2.LINE_AA)

            # Encode to JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                with camera_lock:
                    latest_frame = buffer.tobytes()
                    current_label = "human" if is_focused else "distracted"

            # Write to MongoDB every 5 seconds
            now = time.time()
            if now - last_db_write >= 5:
                label = "human" if is_focused else "distracted"
                events_col.insert_one({
                    "timestamp": datetime.utcnow(),
                    "duration_sec": 5,
                    "label": label
                })
                last_event_time = datetime.utcnow().strftime("%H:%M:%S")
                last_db_write = now

            time.sleep(0.03)  # ~30 fps

    cap.release()


def generate_stream():
    """MJPEG generator — pulls latest_frame from shared memory."""
    while True:
        with camera_lock:
            frame = latest_frame

        if frame is None:
            # Send a black placeholder until camera is ready
            time.sleep(0.1)
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)


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
    with camera_lock:
        label = current_label
    return jsonify({
        "occupied": label in ("human", "distracted"),
        "label": label,
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


# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start camera in background thread BEFORE Flask starts
    t = threading.Thread(target=camera_loop, daemon=True)
    t.start()
    print("✅ Camera thread started")
    print("✅ Dashboard at http://127.0.0.1:5050")
    # use_reloader=False is critical — reloader would start camera twice
    app.run(debug=False, port=5050, use_reloader=False, threaded=True)
    