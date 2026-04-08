from flask import Flask, Response
from picamera2 import Picamera2
import cv2

app = Flask(__name__)

# Initialize camera
picam2 = Picamera2()
# Set lower resolution for performance
picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
picam2.start()

# Load OpenCV face detector
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# Frame skipping settings
FRAME_SKIP = 2  # process every 2nd frame
frame_counter = 0
last_faces = []  # store last detected faces to draw on skipped frames

def generate_frames():
    global frame_counter, last_faces
    while True:
        frame = picam2.capture_array()
        frame_counter += 1

        # Only detect faces every FRAME_SKIP frames
        if frame_counter % FRAME_SKIP == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            last_faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

        # Draw rectangles on all frames using last detected faces
        for (x, y, w, h) in last_faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def index():
    return '''
    <html>
        <head><title>Pi Camera Stream</title></head>
        <body>
            <h1>Live Camera Feed (Face Detection, Frame Skipping)</h1>
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
