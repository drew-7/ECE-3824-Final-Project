import cv2
import mediapipe as mp
import time
import os
from datetime import datetime, timedelta, timezone
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
    running_mode=mp.tasks.vision.RunningMode.VIDEO,
    num_faces=1,
    output_face_blendshapes=True,
    min_face_detection_confidence=0.6,
    min_face_presence_confidence=0.6,
    min_tracking_confidence=0.6,
)

# ── Global state ──────────────────────────────────────────────────────────────
current_label = "vacant"
last_event_ts = "—"
SMOOTH_N      = 6        # frames to average for smoothing
gaze_history  = []


def now_utc():
    """Deprecation-safe UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_gaze_score(lm, w, h):
    """
    Returns 0.0 (looking away) to 1.0 (looking at screen).
    Uses 3 signals:
      1. Iris horizontal offset from face center  (weight 50%)
      2. Iris vertical offset from face center    (weight 25%)
      3. Head yaw — nose offset from face center  (weight 25%)
    """
    left_iris  = lm[468]
    right_iris = lm[473]
    iris_x = (left_iris.x + right_iris.x) / 2.0
    iris_y = (left_iris.y + right_iris.y) / 2.0

    nose_tip    = lm[1]
    left_cheek  = lm[234]
    right_cheek = lm[454]
    chin        = lm[152]
    forehead    = lm[10]

    face_center_x = (left_cheek.x + right_cheek.x) / 2.0
    face_center_y = (forehead.y   + chin.y)         / 2.0
    face_width    = abs(right_cheek.x - left_cheek.x)
    face_height   = abs(chin.y - forehead.y)

    if face_width < 0.001 or face_height < 0.001:
        return 0.0

    # Signal 1 — horizontal iris offset
    h_offset = abs(iris_x - face_center_x) / face_width
    h_score  = max(0.0, 1.0 - (h_offset / 0.25))

    # Signal 2 — vertical iris offset (more lenient — screens are slightly below eye level)
    v_offset = abs(iris_y - face_center_y) / face_height
    v_score  = max(0.0, 1.0 - (v_offset / 0.35))

    # Signal 3 — head yaw (nose off-center means head is turned)
    nose_offset = abs(nose_tip.x - face_center_x) / face_width
    yaw_score   = max(0.0, 1.0 - (nose_offset / 0.20))

    return (h_score * 0.50) + (v_score * 0.25) + (yaw_score * 0.25)


def draw_gaze_bar(frame, score):
    """Draw a small gaze accuracy bar in top-right corner."""
    h, w, _ = frame.shape
    bx, by, bw, bh = w - 140, 60, 120, 12
    cv2.rectangle(frame, (bx - 2, by - 2), (bx + bw + 2, by + bh + 2), (30, 30, 30), -1)
    fill  = int(bw * score)
    color = (0, 229, 160) if score > 0.6 else (255, 180, 0) if score > 0.35 else (255, 77, 109)
    cv2.rectangle(frame, (bx, by), (bx + fill, by + bh), color, -1)
    cv2.putText(frame, f"Gaze: {int(score * 100)}%", (bx, by - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 180, 180), 1, cv2.LINE_AA)


def generate_stream():
    global current_label, last_event_ts, gaze_history

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    last_db_write  = time.time()
    SUSTAIN_SECS   = 2.0   # must look away for 2s before switching to distracted
    distract_since = None
    no_face_since  = None

    with FaceLandmarker.create_from_options(options) as detector:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame     = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results   = detector.detect_for_video(mp_image, int(time.time() * 1000))

            h, w, _    = frame.shape
            is_focused = False
            smoothed   = 0.0

            if results.face_landmarks:
                lm            = results.face_landmarks[0]
                no_face_since = None

                # Multi-signal gaze score
                gaze_score = compute_gaze_score(lm, w, h)

                # Smooth over last N frames
                gaze_history.append(gaze_score)
                if len(gaze_history) > SMOOTH_N:
                    gaze_history.pop(0)
                smoothed = sum(gaze_history) / len(gaze_history)

                raw_focused = smoothed > 0.55

                # Sustain filter — don't switch instantly on a glance away
                if raw_focused:
                    distract_since = None
                    is_focused     = True
                else:
                    if distract_since is None:
                        distract_since = time.time()
                    is_focused = (time.time() - distract_since) < SUSTAIN_SECS

                # Draw bounding box
                xs    = [p.x * w for p in lm]
                ys    = [p.y * h for p in lm]
                color = (0, 229, 160) if is_focused else (255, 77, 109)
                cv2.rectangle(frame,
                    (max(0, int(min(xs)) - 15), max(0, int(min(ys)) - 15)),
                    (min(w, int(max(xs)) + 15), min(h, int(max(ys)) + 15)),
                    color, 2)

                # Draw iris dots
                li = lm[468]; ri = lm[473]
                cv2.circle(frame, (int(li.x * w), int(li.y * h)), 6, color, -1)
                cv2.circle(frame, (int(ri.x * w), int(ri.y * h)), 6, color, -1)

                # Gaze accuracy bar
                draw_gaze_bar(frame, smoothed)

            else:
                gaze_history.clear()
                distract_since = None
                if no_face_since is None:
                    no_face_since = time.time()
                is_focused = (time.time() - no_face_since) < 1.5

            # Status bar
            if results.face_landmarks:
                label_text = "FOCUSED" if is_focused else "DISTRACTED"
            else:
                label_text = "NO FACE DETECTED"
            bar_color = (0, 229, 160) if is_focused else (255, 77, 109)
            cv2.rectangle(frame, (0, 0), (w, 48), (11, 14, 20), -1)
            cv2.putText(frame, label_text, (16, 33),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, bar_color, 2, cv2.LINE_AA)

            # Timestamp
            ts = now_utc().strftime("%H:%M:%S UTC")
            cv2.putText(frame, ts, (w - 170, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 98, 120), 1, cv2.LINE_AA)

            current_label = "human" if is_focused else "distracted"

            # Write to MongoDB every 5 seconds
            if time.time() - last_db_write >= 5:
                events_col.insert_one({
                    "timestamp":    now_utc(),
                    "duration_sec": 5,
                    "label":        current_label
                })
                last_event_ts = now_utc().strftime("%H:%M:%S")
                last_db_write = time.time()

            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/video_feed')
def video_feed():
    return Response(generate_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/status")
def status():
    last = events_col.find_one(sort=[("timestamp", -1)])
    return jsonify({
        "occupied":   current_label in ("human", "distracted"),
        "label":      current_label,
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
    since = now_utc() - timedelta(seconds=60)
    docs  = list(events_col.find({"timestamp": {"$gte": since}}).sort("timestamp", 1))
    return jsonify({
        "labels": [d["timestamp"].strftime("%H:%M:%S") for d in docs],
        "counts": [1 if d.get("label") == "human" else 0 for d in docs]
    })

@app.route("/api/total")
def total():
    since = now_utc() - timedelta(hours=24)
    count = events_col.count_documents({"timestamp": {"$gte": since}})
    return jsonify({"total_24h": count})

@app.route("/")
def index():
    return render_template("dashboard.html")


if __name__ == "__main__":
    print("✅ Starting Desk Security Monitor")
    print("✅ Dashboard      → http://127.0.0.1:5050")
    print("✅ Network access → http://0.0.0.0:5050")
    print("✅ Camera feed    → http://127.0.0.1:5050/video_feed")
    app.run(host="0.0.0.0", debug=False, port=5050, use_reloader=False, threaded=True)
    