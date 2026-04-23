import cv2
import mediapipe as mp
import requests
import time

# Configuration
API_URL = "http://127.0.0.1:5050/api/event"
API_TOKEN = "changeme-supersecret-token"

# Initialize MediaPipe Face Detection
mp_face = mp.solutions.face_detection
face_detector = mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5)

cap = cv2.VideoCapture(0) # Open Mac Webcam

while cap.isOpened():
    ret, frame = cap.read()
    results = face_detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    # Simple logic: If face detected, send "human" event
    if results.detections:
        data = {"duration_sec": 1.0, "label": "human"}
        requests.post(API_URL, json=data, headers={"Authorization": f"Bearer {API_TOKEN}"})
    
    # Add your eye-tracking logic here using MediaPipe Face Mesh
    
    cv2.imshow('Face Detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
