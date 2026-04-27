from flask import Flask, Response, render_template_string
import requests

app = Flask(__name__)

STREAM_URL = "http://127.0.0.1:5000/video_feed"

# Proxy the stream
def generate_stream():
    with requests.get(STREAM_URL, stream=True) as r:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                yield chunk

@app.route('/video_feed')
def video_feed():
    return Response(generate_stream(),
                    content_type='multipart/x-mixed-replace; boundary=frame')

# Simple frontend
@app.route('/')
def index():
    return render_template_string("""
        <html>
        <head>
            <title>Video Stream</title>
        </head>
        <body style="text-align:center;">
            <h1>Live Video Feed</h1>
            <img src="/video_feed" width="640">
        </body>
        </html>
    """)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=False)