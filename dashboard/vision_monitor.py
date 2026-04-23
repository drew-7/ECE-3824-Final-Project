import cv2
import mediapipe as mp
import requests
import time
import os

# ── Configuration ────────────────────────────────────────────────────────────
API_URL = "http://127.0.0.1:5050/api/event"
API_TOKEN = "changeme-supersecret-token"
MODEL_PATH = 'detector.tflite'  # Ensure this file is in your dashboard/ folder

# ── Setup MediaPipe Detector (Modern API) ───────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
FaceDetector = mp.tasks.vision.FaceDetector
FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Check if model exists
if not os.path.exists(MODEL_PATH):
    print(f"CRITICAL ERROR: Could not find {MODEL_PATH} in this folder.")
    exit()

options = FaceDetectorOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.VIDEO)

# ── Camera Loop ─────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not access camera. Please check macOS System Settings > Privacy & Security > Camera.")
    exit()

print("Starting Camera... Press 'q' to exit.")

with FaceDetector.create_from_options(options) as detector:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            continue
        
        # Convert frame to MediaPipe format
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # Detect
        timestamp_ms = int(time.time() * 1000)
        results = detector.detect_for_video(mp_image, timestamp_ms)
        
        # ── Trigger API on detection ─────────────────────────────────────────
        if results.detections:
            # Uncomment the next line to actually send data to your server
            try:
                payload = {"duration_sec": 1.0, "label": "human"}
                headers = {"Authorization": f"Bearer {API_TOKEN}"}
                requests.post(API_URL, json=payload, headers=headers)
                print("Face detected and event sent to Dashboard.")
            except Exception as e:
                print(f"Could not connect to dashboard: {e}")
        
        # Display window
        cv2.imshow('Desk Security — Face Monitor', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
