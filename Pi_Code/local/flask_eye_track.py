from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from datetime import datetime, timezone
from flask import Flask, Response
import os
import cv2

### ── MongoDB Setup ─────────────────────────────────────
load_dotenv("../../.env/.env")
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

### ── Flask App ─────────────────────────────────────────
app = Flask(__name__)


### ── Camera Setup ──────────────────────────────────────
cap = cv2.VideoCapture(0)
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

print(" Camera running...")

### ── Haar Cascades ─────────────────────────────────────
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

### ── Settings ──────────────────────────────────────────
FRAME_SKIP = 3
PRINT_EVERY = 1

frame_counter = 0
last_faces = []

### ── STREAM GENERATOR 
def generate_frames():
    global frame_counter, last_faces

    while True:
        success, frame = cap.read()
        if not success:
             success, frame = cap.read()
        if not success:
            database.insert_one({
                "_id": database.count_documents({}) + 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "left_eye": None,
                "right_eye": None,
                "camera_error": True,
                "focused": False
            })
            continue

        frame_counter += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Face detection
        if frame_counter % FRAME_SKIP == 0:
            last_faces = face_cascade.detectMultiScale(gray, 1.1, 5)

        normalized_eyes = []

        for (x, y, w, h) in last_faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

            roi_gray = gray[y:y+h, x:x+w]
            roi_color = frame[y:y+h, x:x+w]

            eyes = eye_cascade.detectMultiScale(roi_gray, 1.1, 3)

            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), -1)

                # Eye center
                eye_center_x = ex + ew // 2
                eye_center_y = ey + eh // 2

                global_x = x + eye_center_x
                global_y = y + eye_center_y

                norm_x = global_x / FRAME_WIDTH
                norm_y = global_y / FRAME_HEIGHT

                normalized_eyes.append((norm_x, norm_y))

                cv2.circle(frame, (global_x, global_y), 3, (0, 0, 255), -1)

        # MongoDB logging
        if frame_counter % PRINT_EVERY == 0 and len(normalized_eyes) >= 2:
            normalized_eyes.sort(key=lambda e: e[0])

            left_eye = normalized_eyes[0]
            right_eye = normalized_eyes[1]

            data = {
                "_id": database.count_documents({}) + 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "left_eye": {"x": left_eye[0], "y": left_eye[1]},
                "right_eye": {"x": right_eye[0], "y": right_eye[1]},
                "camera_error": False,
                "focused": True   

            }

            database.insert_one(data)

        # Encode frame WITH rectangles drawn
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        frame_bytes = buffer.tobytes()

        # MJPEG stream format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

### ── ROUTE ─────────────────────────────────────────────
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

### ── MAIN ──────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)