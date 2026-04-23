import cv2
import mediapipe as mp
import requests
import time

# ── Configuration ────────────────────────────────────────────────────────────
API_URL = "http://127.0.0.1:5050/api/event"
API_TOKEN = "changeme-supersecret-token"

# ── Setup MediaPipe Detector (Modern API) ───────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
FaceDetector = mp.tasks.vision.FaceDetector
FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Using default model (auto-downloads)
options = FaceDetectorOptions(
    base_options=BaseOptions(model_asset_path=None),
    running_mode=VisionRunningMode.VIDEO)

# ── Camera Loop ─────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)

print("Starting Camera... Press 'q' to exit.")

with FaceDetector.create_from_options(options) as detector:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue
        
        # Convert frame to MediaPipe format
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # Detect face
        timestamp_ms = int(time.time() * 1000)
        results = detector.detect_for_video(mp_image, timestamp_ms)
        
        # ── Trigger API on detection ─────────────────────────────────────────
        if results.detections:
            print("Face Detected — Sending Event")
            try:
                # Payload matching your Flask API expectations
                payload = {"duration_sec": 1.0, "label": "human"}
                headers = {"Authorization": f"Bearer {API_TOKEN}"}
                requests.post(API_URL, json=payload, headers=headers)
            except Exception as e:
                print(f"Could not connect to dashboard: {e}")
        
        # Display window
        cv2.imshow('Desk Security — Face Monitor', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
