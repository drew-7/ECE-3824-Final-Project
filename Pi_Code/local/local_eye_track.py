from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from datetime import datetime,timezone
import os
import cv2
import json

### Load Mongo Data Base
load_dotenv("../../.env/.env")
uri = os.getenv("MONGO_URI")
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client["EyeDataPoints"]
database = db["LiveData"]



# Initialize webcam
cap = cv2.VideoCapture(0)
print("Camera is up and running...")
# Set resolution
FRAME_WIDTH = 320
FRAME_HEIGHT = 240
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# Load cascades
#face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Settings
FRAME_SKIP = 3
PRINT_EVERY = 1

frame_counter = 0
last_faces = []

while True:
    success, frame = cap.read()
    if not success:
        break

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
            # Draw filled eye box
            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), -1)

            # Eye center (ROI coords)
            eye_center_x = ex + ew // 2
            eye_center_y = ey + eh // 2

            # Convert to global coords
            global_x = x + eye_center_x
            global_y = y + eye_center_y

            # Normalize (0–1)
            norm_x = global_x / FRAME_WIDTH
            norm_y = global_y / FRAME_HEIGHT

            normalized_eyes.append((norm_x, norm_y))

            # Draw center point
            cv2.circle(frame, (global_x, global_y), 3, (0, 0, 255), -1)

    # JSON OUTPUT SECTION
    if frame_counter % PRINT_EVERY == 0 and len(normalized_eyes) >= 2:
        # Sort by x position (left eye first)
        normalized_eyes.sort(key=lambda e: e[0])

        left_eye = normalized_eyes[0]
        right_eye = normalized_eyes[1]

        data = {
            #"timestamp": datetime.now().isoformat(),
            "_id" : database.count_documents({}) + 1,
            "timestamp" : datetime.now(timezone.utc).isoformat(),
            "left_eye": {
                "x": left_eye[0],
                "y": left_eye[1]
            },
            "right_eye": {
                "x": right_eye[0],
                "y": right_eye[1]
            }
        }

        json_data = json.dumps(data)
        #print(json_data, flush=True)

        print(data["left_eye"]["x"])

        ## upload data to MongoDB
        database.insert_one(json.loads(json_data))

    # Show frame
    cv2.imshow("Eye Tracking (Normalized 0–1)", frame)

    # Exit on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

     

# Cleanup
cap.release()
cv2.destroyAllWindows()