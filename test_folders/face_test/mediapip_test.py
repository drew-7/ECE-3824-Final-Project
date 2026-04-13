from flask import Flask, Response
from picamera2 import Picamera2
import cv2
import mediapipe as mp

app = Flask(__name__)

# Initialize camera
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,  # adds iris detail
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Drawing style
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)

# Frame skipping
FRAME_SKIP = 2
frame_counter = 0
last_results = None

def generate_frames():
    global frame_counter, last_results

    while True:
        frame = picam2.capture_array()
        frame_counter += 1

        # Convert BGR -> RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Run detection every FRAME_SKIP frames
        if frame_counter % FRAME_SKIP == 0:
            last_results = face_mesh.process(rgb_frame)

        # Draw mesh using last results
        if last_results and last_results.multi_face_landmarks:
            for face_landmarks in last_results.multi_face_landmarks:
                mp_drawing.draw_landmarks(
                    image=frame,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=drawing_spec,
                    connection_drawing_spec=drawing_spec
                )

        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def index():
    return '''
    <html>
        <head><title>MediaPipe Face Mesh</title></head>
        <body>
            <h1>Live Face Mesh (MediaPipe)</h1>
            <img src="/video">
        </body>
    </html>
    '''

@app.route('/video')
def video():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
