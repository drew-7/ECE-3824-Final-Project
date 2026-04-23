import cv2
import mediapipe as mp
import time
import os

# ── Configuration ────────────────────────────────────────────────────────────
MODEL_PATH = os.path.abspath('face_landmarker.task')
ALERT_THRESHOLD = 5.0 

# ── Setup ───────────────────────────────────────────────────────────────────
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
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        results = detector.detect_for_video(mp_image, int(time.time() * 1000))
        
        is_focused = True # Assume focused until proven otherwise
        
        if results.face_landmarks:
            for landmarks in results.face_landmarks:
                # Landmark indices for Iris (approximate center)
                left_eye_iris = landmarks[468] 
                right_eye_iris = landmarks[473]
                
                # Logic: If iris is too far left or right, you are not looking at the screen
                # Center is usually around 0.5. Let's use a 0.15 tolerance.
                if not (0.35 < left_eye_iris.x < 0.65):
                    is_focused = False
                
                # Draw visual feedback on the frame
                cv2.putText(frame, "STATUS: FOCUSING" if is_focused else "STATUS: DISTRACTED", 
                            (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 
                            (0, 255, 0) if is_focused else (0, 0, 255), 2)

        # ── Alert Logic ──────────────────────────────────────────────────────
        if is_focused:
            last_focus_time = time.time()
            alert_triggered = False
        else:
            if (time.time() - last_focus_time) > ALERT_THRESHOLD and not alert_triggered:
                print("ALERT: YOU ARE LOSING FOCUS!")
                os.system('afplay /System/Library/Sounds/Glass.aiff')
                alert_triggered = True

        cv2.imshow('Gaze Tracker', frame)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
