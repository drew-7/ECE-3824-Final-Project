import cv2
import mediapipe as mp
import time
import os

# ── Configuration ────────────────────────────────────────────────────────────
MODEL_PATH = os.path.abspath('face_landmarker.task')
ALERT_THRESHOLD = 5.0 

# ── Setup ──────────────────────────────────────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.VIDEO)

cap = cv2.VideoCapture(0)
last_focus_time = time.time()
alert_triggered = False

print("Monitoring Eye Focus... Press 'q' to exit.")

with FaceLandmarker.create_from_options(options) as detector:
    while cap.isOpened():
        success, frame = cap.read()
        if not success: continue
        
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = detector.detect_for_video(mp_image, int(time.time() * 1000))
        
        is_focused = True
        
        if results.face_landmarks:
            for landmarks in results.face_landmarks:
                h, w, _ = frame.shape
                
                # 1. Draw Face Square
                x_min = int(min([lm.x for lm in landmarks]) * w) - 20
                y_min = int(min([lm.y for lm in landmarks]) * h) - 20
                x_max = int(max([lm.x for lm in landmarks]) * w) + 20
                y_max = int(max([lm.y for lm in landmarks]) * h) + 20
                
                # 2. Track Iris Points (468 for left, 473 for right)
                left_iris = landmarks[468]
                right_iris = landmarks[473]
                
                # Logic: Check if irises are centered
                if not (0.35 < left_iris.x < 0.65): is_focused = False
                
                # Draw Visuals
                color = (0, 255, 0) if is_focused else (0, 0, 255)
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 2)
                cv2.circle(frame, (int(left_iris.x * w), int(left_iris.y * h)), 5, color, -1)
                cv2.circle(frame, (int(right_iris.x * w), int(right_iris.y * h)), 5, color, -1)

        # ── Alert Logic ──────────────────────────────────────────────────────
        if is_focused:
            last_focus_time = time.time()
            alert_triggered = False
        else:
            if (time.time() - last_focus_time) > ALERT_THRESHOLD and not alert_triggered:
                print("ALERT: FOCUS LOST!")
                os.system('afplay /System/Library/Sounds/Glass.aiff')
                alert_triggered = True

        cv2.imshow('Precision Gaze Tracker', frame)
        if cv2.waitKey(25) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
