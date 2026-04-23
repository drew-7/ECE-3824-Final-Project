import cv2
import mediapipe as mp
import time
import os

# ── Configuration ────────────────────────────────────────────────────────────
MODEL_PATH = 'detector.tflite'
# 5 seconds threshold
ALERT_THRESHOLD = 5.0 

# ── Setup MediaPipe ─────────────────────────────────────────────────────────
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

cap = cv2.VideoCapture(0)
last_focus_time = time.time()
alert_triggered = False

print("Monitoring Eye Focus... Press 'q' to exit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: continue
    
    frame = cv2.flip(frame, 1) # Mirror
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    
    is_focused = False
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            # Simplified Gaze Logic: 
            # In a real app, calculate iris position relative to eye corners
            # Here we check if the face is centered/facing forward
            nose_tip = face_landmarks.landmark[1]
            if 0.4 < nose_tip.x < 0.6: # Face is centered
                is_focused = True
            
            # Draw Square around face
            h, w, _ = frame.shape
            x_min = int(min([lm.x for lm in face_landmarks.landmark]) * w) - 20
            y_min = int(min([lm.y for lm in face_landmarks.landmark]) * h) - 20
            x_max = int(max([lm.x for lm in face_landmarks.landmark]) * w) + 20
            y_max = int(max([lm.y for lm in face_landmarks.landmark]) * h) + 20
            
            color = (0, 255, 0) if is_focused else (0, 0, 255)
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, 3)

    # ── Alert Logic ──────────────────────────────────────────────────────────
    if is_focused:
        last_focus_time = time.time()
        alert_triggered = False
    else:
        if (time.time() - last_focus_time) > ALERT_THRESHOLD and not alert_triggered:
            print("ALERT: FOCUS LOST!")
            # Add a system beep here: os.system('say "Focus lost"')
            alert_triggered = True

    cv2.imshow('Focus Monitor', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
