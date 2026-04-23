import cv2
import mediapipe as mp
import time
import os

# ── Configuration ────────────────────────────────────────────────────────────
# Explicitly setting the filename to match your file
MODEL_FILENAME = 'face_landmarker.task'
MODEL_PATH = os.path.join(os.getcwd(), MODEL_FILENAME)

# Diagnostic check
if not os.path.exists(MODEL_PATH):
    print(f"CRITICAL ERROR: Could not find {MODEL_FILENAME} at {MODEL_PATH}")
    print("Files currently in this folder:", os.listdir('.'))
    exit()

# ── Setup MediaPipe ─────────────────────────────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.VIDEO)

# ── Main Loop ───────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
last_focus_time = time.time()
alert_triggered = False

print("Monitoring Focus... Press 'q' to exit.")

with FaceLandmarker.create_from_options(options) as detector:
    while cap.isOpened():
        success, frame = cap.read()
        if not success: continue
        
        frame = cv2.flip(frame, 1)
        # Convert frame to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        timestamp_ms = int(time.time() * 1000)
        results = detector.detect_for_video(mp_image, timestamp_ms)
        
        is_focused = False
        if results.face_landmarks:
            for landmarks in results.face_landmarks:
                # Landmark 1 is the nose tip
                nose_tip = landmarks[1]
                # Logic: If nose is centered (0.4 to 0.6), user is focused
                if 0.4 < nose_tip.x < 0.6:
                    is_focused = True
                
                # Draw Box
                h, w, _ = frame.shape
                x_coords = [lm.x for lm in landmarks]
                y_coords = [lm.y for lm in landmarks]
                x_min, x_max = int(min(x_coords) * w) - 20, int(max(x_coords) * w) + 20
                y_min, y_max = int(min(y_coords) * h) - 20, int(max(y_coords) * h) + 20
                
                color = (0, 255, 0) if is_focused else (0, 0, 255)
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 3)

        # ── Alert Logic ──────────────────────────────────────────────────────
        if is_focused:
            last_focus_time = time.time()
            alert_triggered = False
        else:
            if (time.time() - last_focus_time) > 5.0 and not alert_triggered:
                print("ALERT: FOCUS LOST!")
                os.system('afplay /System/Library/Sounds/Glass.aiff')
                alert_triggered = True

        cv2.imshow('Focus Monitor', frame)
        
        if cv2.waitKey(25) & 0xFF == ord('q'): 
            print("Exiting...")
            break

cap.release()
cv2.destroyAllWindows()
