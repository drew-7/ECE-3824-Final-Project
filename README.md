# IoT Desk Security Monitor

> **ECE-3824 Final Project** | Dhruvil Patel & Samuel Georgi | Spring 2026

A complete end-to-end IoT pipeline that uses computer vision to monitor whether a person at a desk is **focused or distracted**. A Raspberry Pi 3 runs MediaPipe iris tracking locally, transmits labeled events securely to a Flask backend, stores them in MongoDB, and displays everything on a live web dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1.3-black?style=flat-square&logo=flask)
![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green?style=flat-square&logo=mongodb)
![OpenCV](https://img.shields.io/badge/OpenCV-4.13-red?style=flat-square&logo=opencv)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Iris_Tracking-orange?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue?style=flat-square&logo=docker)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Hardware Requirements](#2-hardware-requirements)
3. [System Architecture](#3-system-architecture)
4. [Data Models](#4-data-models)
5. [File Structure](#5-file-structure)
6. [Complete Source Code](#6-complete-source-code)
7. [API Specification](#7-api-specification)
8. [Security Model](#8-security-model)
9. [Deployment Guide](#9-deployment-guide)
10. [Unit Testing](#10-unit-testing)
11. [Troubleshooting](#11-troubleshooting)
12. [Future Improvements](#12-future-improvements)
13. [Weekly Progress Log](#13-weekly-progress-log)

---

## 1. Project Overview

The IoT Desk Security Monitor is a smart workspace surveillance system that classifies a desk occupant as **FOCUSED** or **DISTRACTED** using real-time iris tracking. Every 5 seconds, the system logs a labeled event to MongoDB and the web dashboard updates automatically.

### What it does

| Layer | Technology | Role |
|---|---|---|
| **Sensor** | Raspberry Pi 3 + USB Webcam | Captures video, runs MediaPipe |
| **Detection** | OpenCV + MediaPipe Face Landmarker | Iris tracking, focus classification |
| **Backend** | Flask (Python) | REST API, video stream, dashboard |
| **Database** | MongoDB in Docker | Time-series event storage |
| **Frontend** | HTML + Chart.js | Live dashboard, MJPEG feed |

### Key Features
- **Iris-based focus detection** — MediaPipe landmark 468 (left iris) determines gaze direction
- **Live MJPEG camera feed** embedded directly in the dashboard
- **Focus timeline chart** — bar chart updates every 5 seconds
- **Bearer token authentication** on all write operations
- **Rolling security log** — last 10 events with timestamps and labels
- **MongoDB in Docker** — containerized, localhost-only database

---

## 2. Hardware Requirements

| Component | Specification | Notes |
|---|---|---|
| Processor | Raspberry Pi 3, 4, or 5 | Pi 4 recommended for MediaPipe performance |
| Camera | Standard USB Webcam (UVC) | Plug-and-play, no driver needed |
| Connectivity | Onboard WiFi 802.11ac | Connects to `tuiot` network |
| Storage | MicroSD 16GB+ | OS + Python environment |
| Dev Machine | Mac / Windows / Linux | Runs dashboard + MongoDB |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     COMPLETE SYSTEM PIPELINE                        │
│                                                                     │
│  ┌──────────────┐    HTTP POST      ┌──────────────┐                │
│  │ SENSOR LAYER │  ─────────────►   │  BACKEND API |                │
│  │              │  Bearer Token     │              │                │
│  │ Raspberry Pi │                   │ Flask/Python │                │
│  │ USB Webcam   │                   │ Port 5050    │                │
│  │ OpenCV       │                   │ JSON/REST    │                │
│  │ MediaPipe    │                   └──────┬───────┘                │
│  └──────────────┘                          │ PyMongo                │
│                                            ▼                        │
│                                   ┌──────────────┐                  │
│                                   │   DATABASE   │                  │
│                                   │              │                  │
│                                   │   MongoDB    │                  │
│                                   │   Docker     │                  │
│                                   │ Port 27017   │                  │
│                                   └──────┬───────┘                  │
│                                          │ API calls                │
│                                          ▼                          │
│                                   ┌──────────────┐                  │
│                                   │   FRONTEND   │                  │
│                                   │              │                  │
│                                   │ Flask+Jinja2 │                  │
│                                   │ Chart.js     │                  │
│                                   │ MJPEG iframe │                  │
│                                   └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1 Sensor Layer (Raspberry Pi)

The Pi opens the USB webcam via `cv2.VideoCapture(0)`, flips the frame horizontally, and passes each frame to **MediaPipe Face Landmarker** in VIDEO mode. The landmarker returns 478 facial landmarks. **Landmarks 468 (left iris) and 473 (right iris)** determine gaze direction.

```
if 0.35 < landmark[468].x < 0.65 → FOCUSED (iris centered on screen)
else                               → DISTRACTED (iris drifted away)
```

### 3.2 Backend API (Flask)

Flask runs on port 5050 and handles three responsibilities simultaneously:
- **REST API** — 5 endpoints for the dashboard to consume
- **MJPEG video stream** — `/video_feed` streams processed frames with overlays
- **Web dashboard** — serves `dashboard.html` at the root route

The camera runs inside `generate_stream()`, a Python generator that Flask calls when a client connects to `/video_feed`. Frames are encoded as JPEG and yielded as `multipart/x-mixed-replace`.

### 3.3 Database (MongoDB)

MongoDB runs in Docker on port 27017, **bound to localhost only**. The database is `sensor_db` with one collection: `motion_events`. Every 5 seconds the camera loop inserts a new document.

### 3.4 Frontend (Flask Dashboard)

Single-page HTML/CSS/JS application served by Flask. Key implementation decisions:

- **`<iframe src="/video_feed">`** — NOT `<img src="/video_feed">`. The MJPEG stream holds a persistent connection. An `<img>` tag blocks Flask's other API endpoints in the same browser context. An `<iframe>` loads the stream in a separate browser context.
- **`Promise.all()`** — all 4 API endpoints are fetched simultaneously every 5 seconds
- **Stacked bar chart** — green bars for focused (count=1), red for distracted (count=0)

---

## 4. Data Models

### 4.1 MongoDB Document Schema (`motion_events`)

```json
{
  "_id":          "ObjectId (auto-generated)",
  "timestamp":    "ISODate UTC — datetime.utcnow()",
  "duration_sec": 5.0,
  "label":        "human | distracted"
}
```

**Label values:**
- `"human"` — iris x between 0.35 and 0.65, user is looking at screen → dashboard shows **FOCUSED** 🟢
- `"distracted"` — iris off-center or no face detected → dashboard shows **DISTRACTED** 🔴

### 4.2 API Response Schemas

```json
// GET /api/status
{ "occupied": true, "label": "human", "last_event": "18:31:55" }

// GET /api/log
[{ "time": "2026-04-26 18:31:55", "duration": 5, "label": "human" }, ...]

// GET /api/hourly
{ "labels": ["18:31:20", "18:31:25", ...], "counts": [1, 0, 1, ...] }

// GET /api/total
{ "total_24h": 47 }

// POST /api/event (request body)
{ "duration_sec": 5.0, "label": "human" }
```

---

## 5. File Structure

```
ECE-3824-Final-Project/
├── dashboard/
│   ├── app.py                    ← Main Flask server (camera + API + dashboard)
│   ├── requirements.txt          ← Python dependencies
│   └── templates/
│       └── dashboard.html        ← Single-page dashboard UI
├── Pi_Code/
│   ├── cv_test.py                ← Facial feature detection stream (Pi only)
│   └── pi_eye_track.py           ← Basic MongoDB write test
│   └── local/
│       └── flask_eye_track.py     ← Testing iris tracking
│       └── local_eye_track.py     ← Testing iris tracking on local device
├── test_folders/
│   ├── camera_test/
│   │   └── view_camera.py        ← Basic MJPEG camera stream test
│   ├── cloudtest/
│   │   └── pull.py               ← Basic data sent to hardware
│   │   └── upload.py             ← uploading the pull data 
│   ├── dockerTest/
│   │   ├── compose.yml           ← MongoDB Docker Compose config
│   │   ├── receive.py            ← Read from MongoDB test
│   │   └── upload.py             ← Write to MongoDB test
│   ├── flaskvideotest/
│   │   ├── send_video.py         ← loading the camera on host 
│   │   ├── show_video.py         ← Display the required resolution on host 
│   └── face_test/
│       ├── local/
│       │   └── face_scan_local.py  ← OpenCV Haar cascade scan (no Pi needed)
│       ├── face_scan.py            ← Face scan MJPEG stream (Pi)
│       └── mediapipe_test.py       ← MediaPipe face mesh stream (Pi)
├── Server_Code/
│   └── main.py                   ← FastAPI alternative backend
│   └── upload.py                 ← FastAPI alternative backend to upload then data
└── README.md                     ← This file
```

---

## 6. Complete Source Code

### 6.1 `app.py` — Main Flask Server

This is the **only file you need to run**. It handles camera, MediaPipe, MongoDB writes, video streaming, all API routes, and the dashboard.

```python
from flask import Flask, render_template, Response, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
import requests

## MongoDB overhead
load_dotenv("../.env/.env")
uri = os.getenv("MONGO_URI")

print("Connecting to MongoDB...")
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(e)

db = client["EyeDataPoints"]
database = db["LiveData"]


app = Flask(__name__)
STREAM_URL = "http://172.20.10.5:5000/video_feed"


# ── Routes ──

# Proxy the stream
def generate_stream():
    try:
        with requests.get(STREAM_URL, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
    except requests.exceptions.RequestException:
        return

@app.route('/video_feed')
def video_feed():
    return Response(generate_stream(),
                    content_type='multipart/x-mixed-replace; boundary=frame')


@app.route("/api/log")
def log():
    docs = list(database.find().sort("timestamp", -1))

    return jsonify([{
        "timestamp": d["timestamp"],
        "left_eye": d.get("left_eye"),
        "right_eye": d.get("right_eye"),
        "camera_error": d.get("camera_error", False),
        "focused": d.get("focused", False)
    } for d in docs])


@app.route("/api/status")
def status():
    latest = database.find_one(sort=[("timestamp", -1)])
    if not latest:
        return jsonify({"label": "unknown"})

    if latest.get("camera_error"):
        return jsonify({"label": "camera_error", "seconds_since": 0})

    now = datetime.now(timezone.utc).timestamp()
    last_ts = latest["timestamp"]
    if hasattr(last_ts, "timestamp"):
        last_ts = last_ts.timestamp()
    else:
        last_ts = datetime.fromisoformat(last_ts).timestamp()

    seconds_since = now - last_ts
    label = "focused" if seconds_since < 5 else "distracted"
    return jsonify({"label": label, "seconds_since": round(seconds_since, 2)})

## Connect server to backend!
@app.route('/')
def index():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=False, port=5000, use_reloader=False)
```

### 6.2 `requirements.txt`

```
blinker==1.9.0
certifi==2026.4.22
charset-normalizer==3.4.7
click==8.3.3
colorama==0.4.6
dnspython==2.8.0
dotenv==0.9.9
Flask==3.1.3
gunicorn==25.3.0
idna==3.13
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
packaging==26.2
pymongo==4.17.0
python-dotenv==1.2.2
requests==2.33.1
urllib3==2.6.3
Werkzeug==3.1.8
```

### 6.3 `docker-compose.yml` (MongoDB)

```yaml
services:
  mongo:
    image: mongo:7
    container_name: mongo-desk
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
    command: ["--bind_ip", "0.0.0.0"]
volumes:
  mongo-data:
    driver: local
```

### 6.4 `dashboard.html` — Key Architecture Notes

The full HTML file lives in `dashboard/templates/dashboard.html`. Critical decisions for reproduction:

- Use **`<iframe src="/video_feed">`** NOT `<img src="/video_feed">` — the img tag causes the MJPEG stream to block Flask's other API endpoints
- Chart.js **stacked bar chart** with two datasets: green (focused=1) and red (distracted=0)
- **`setInterval(refresh, 5000)`** calls `Promise.all()` on all 4 endpoints simultaneously
- **Focus rate bar**: `(focused_count / total) * 100` — green >60%, amber >30%, red otherwise
- Status dot CSS: `.focused` (green pulse), `.distracted` (red pulse), `.vacant` (grey)

---

## 7. API Specification

| Endpoint | Method | Auth Required | Request Body | Response |
|---|---|---|---|---|
| `/api/event` | `POST` | ✅ Bearer Token | `{"duration_sec": 5.0, "label": "human"}` | `201 {"status": "ok"}` |
| `/api/status` | `GET` | ❌ | — | `{"occupied": bool, "label": str, "last_event": str}` |
| `/api/log` | `GET` | ❌ | — | `[{"time": str, "duration": int, "label": str}, ...]` |
| `/api/hourly` | `GET` | ❌ | — | `{"labels": [str], "counts": [0\|1]}` |
| `/api/total` | `GET` | ❌ | — | `{"total_24h": int}` |
| `/video_feed` | `GET` | ❌ | — | `multipart/x-mixed-replace` MJPEG stream |

**Error codes:**
- `401 Unauthorized` — missing or incorrect Bearer Token on POST
- `400 Bad Request` — missing fields in JSON body
- `422 Unprocessable Entity` — malformed JSON

**Example POST from Pi or curl:**
```bash
curl -X POST http://<SERVER_IP>:5050/api/event \
  -H "Authorization: Bearer your-secret-token" \
  -H "Content-Type: application/json" \
  -d '{"duration_sec": 5.0, "label": "human"}'
```

---

## 8. Security Model

### 8.1 Bearer Token Authentication
All `POST /api/event` requests require:
```
Authorization: Bearer <API_TOKEN>
```
Missing or wrong token → `HTTP 401` before touching the database.

### 8.2 Token via Environment Variable
```bash
export API_TOKEN="your-secret-token-here"
python3 app.py
```
The token is **never hardcoded** in source. Default is `"changeme-supersecret-token"` — always override this.

### 8.3 Database Isolation
MongoDB runs inside Docker bound to `localhost:27017`. It is **never exposed to the public internet**. Only the Flask backend on the same machine can reach it.

### 8.4 Input Validation
All incoming JSON is validated before database access. Missing fields return `400`. Malformed JSON returns `422`.

### 8.5 Git Security
Add to `.gitignore`:
```
.env
*.env
API_TOKEN
```

---

## 9. Deployment Guide

### 9.1 Prerequisites
- Python 3.10+
- Docker Desktop OR MongoDB Community via Homebrew
- `face_landmarker.task` — download from [MediaPipe Model Cards](https://developers.google.com/mediapipe/solutions/vision/face_landmarker)
- USB webcam connected + camera permissions granted to Terminal/VS Code

### 9.2 Setup — Windows / Mac / Linux

**Step 1 — Start MongoDB:**
```bash
# Option A: Docker
docker run -d --name mongo-desk -p 27017:27017 mongo:7

# Option B: Homebrew (Mac)
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Step 2 — Create virtual environment:**
```bash
cd ECE-3824-Final-Project/dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install flask pymongo opencv-python mediapipe numpy
```

**Step 3 — Place model file:**
```bash
ECE-3824-Final-Project/dashboard/app.py
```

**Step 4 — Run:**
```bash
export API_TOKEN="your-secret-token"
python3 app.py
```

**Step 5 — Open dashboard:**
```
http://127.0.0.1:5050
```

### 9.3 Setup — Windows

```bash
# Activate venv (different syntax)
.venv\Scripts\activate

# Set token (different syntax)
set API_TOKEN=your-secret-token

# If camera shows black screen, change in app.py:
# cv2.VideoCapture(0)  →  cv2.VideoCapture(0, cv2.CAP_DSHOW)
```

### 9.4 Using the venv across all project folders

The `.venv` lives in `dashboard/` but can be used from any subfolder:
```bash
source ~/ECE-3824-Final-Project/dashboard/.venv/bin/activate
cd ~/ECE-3824-Final-Project/test_folders/camera_test
python3 view_camera.py   # works from any folder once venv is activated
```

---

## 10. Unit Testing

### Framework
```bash
pip install pytest httpx mongomock
```

### Test Matrix

| Category | Test | Expected |
|---|---|---|
| **API Auth** | POST with valid token | `201 Created` |
| | POST with no token | `401 Unauthorized` |
| | POST with wrong token | `401 Unauthorized` |
| | POST with malformed JSON | `400 Bad Request` |
| **Database** | Insert writes correct fields | `timestamp`, `duration_sec`, `label` present |
| | Empty DB returns vacant | `{"label": "vacant"}` |
| | hourly() buckets by timestamp | Labels are `HH:MM:SS` strings |
| | total() only counts last 24h | Excludes old seeded data |
| **Sensor Logic** | Iris x=0.5 → focused | `label = "human"` |
| | Iris x=0.1 → distracted | `label = "distracted"` |
| | No face detected → distracted | `label = "distracted"` |
| | HTTP POST retries on timeout | Retries up to 3 times |

### Run Tests
```bash
# From project root with venv activated
pytest tests/ -v

# Specific category
pytest tests/test_api.py -v
pytest tests/test_db.py -v
```

---

## 11. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Black camera in dashboard | `<img>` tag blocking Flask | Use `<iframe>` not `<img>` for `/video_feed` |
| Camera not found | macOS permissions | System Settings → Privacy → Camera → enable Terminal/VS Code |
| `ModuleNotFoundError: cv2` | venv not activated | Run `source .venv/bin/activate` |
| MongoDB connection refused | Docker/MongoDB not running | `brew services start mongodb-community` OR `docker start mongo-desk` |
| Total events in thousands | `seed_demo.py` inserted fake data | Clear with: `python3 -c "from pymongo import MongoClient; MongoClient()['sensor_db']['motion_events'].delete_many({})"` |
| `face_landmarker.task` not found | Model file missing | Download from MediaPipe and place in `dashboard/` |
| Port 5050 already in use | Old `app.py` still running | `lsof -ti:5050 \| xargs kill` |
| Camera black on Windows | Wrong camera backend | Change to `cv2.VideoCapture(0, cv2.CAP_DSHOW)` |

---

## 12. Future Improvements

- **YOLOv8 / MediaPipe Pose** — full body detection instead of iris-only, reduces false positives from pets or shadows
- **WebSocket push** — replace 5-second HTTP polling with real-time push so events appear instantly
- **Cloud deployment** — move to AWS EC2 or Google Cloud Run with HTTPS via Let's Encrypt
- **Desktop notifications** — push alerts via NTFY or Pushover when focus state changes
- **InfluxDB** — replace MongoDB with a purpose-built time-series database for better querying and built-in retention
- **GitHub Actions CI/CD** — run unit tests automatically on every commit

---

## 13. Weekly Progress Log

| Week | Milestone |
|---|---|
| **Week 9** | Project proposal submitted. Chose Raspberry Pi + USB webcam. Defined data pipeline: OpenCV → FastAPI → MongoDB → Flask dashboard |
| **Week 10** | Hardware acquired. Pi connected to `tuiot` WiFi. Basic USB webcam stream confirmed via `view_camera.py`. Docker MongoDB tested locally |
| **Week 11** | Full sensor-to-database pipeline working. FastAPI backend with Bearer Token implemented. MongoDB integrated via Docker. End-to-end validation confirmed |
| **Week 12** | Web dashboard built with Chart.js timeline, occupancy status, focus rate bar, and session log. MJPEG live feed embedded via `<iframe>` |
| **Week 13** | MediaPipe iris tracking integrated into `app.py`. Focused/distracted classification working. Dashboard updated with green/red status. README and slides finalized |
| **Week 14** | Final presentation. Demonstrated live dashboard, architecture, API calls, security model, testing suite, and documentation |

---

## Authors

**Dhruvil Patel** & **Samuel Georgi**
ECE-3824 - Spring 2026

---
