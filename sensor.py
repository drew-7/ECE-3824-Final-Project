import cv2
import time
import requests

API_URL = "http://your-computer-ip:8000/log"
TOKEN = "your_secret_token_123"

def run_sensor():
    cap = cv2.VideoCapture(0)
    motion_start_time = None
    
    while True:
        ret, frame = cap.read()
        # [Simplified Motion Detection Logic]
        # ... (Using the OpenCV logic we discussed before) ...
        
        motion_detected = True # Placeholder for actual CV logic
        
        if motion_detected:
            if motion_start_time is None:
                motion_start_time = time.time()
            
            # Filter: Must be motion for > 3 seconds (The "Cat" Filter)
            if time.time() - motion_start_time > 3:
                payload = {
                    "device_id": "Pi_Desk_01",
                    "event_type": "human_presence",
                    "duration": time.time() - motion_start_time
                }
                headers = {"Authorization": f"Bearer {TOKEN}"}
                requests.post(API_URL, json=payload, headers=headers)
                time.sleep(10) # Prevent double-logging
        else:
            motion_start_time = None

run_sensor()
