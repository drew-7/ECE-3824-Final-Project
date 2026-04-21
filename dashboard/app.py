from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# ── MongoDB connection ─────────────────────────────────────────────────────────
# Change this to your actual MongoDB URI (local Docker or Atlas)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["sensor_db"]
events_col = db["motion_events"]   # motion / occupancy events
readings_col = db["readings"]      # raw sensor readings (from sensor.py)

# ── Auth token ────────────────────────────────────────────────────────────────
API_TOKEN = os.environ.get("API_TOKEN", "changeme-supersecret-token")

def require_token(req):
    auth = req.headers.get("Authorization", "")
    return auth == f"Bearer {API_TOKEN}"

# ─────────────────────────────────────────────────────────────────────────────
# API ROUTES  (used by the Pi to POST data, and by the dashboard JS to GET data)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/event", methods=["POST"])
def receive_event():
    """Pi POSTs motion events here."""
    if not require_token(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    event = {
        "timestamp": datetime.utcnow(),
        "duration_sec": data.get("duration_sec", 0),
        "label": data.get("label", "motion"),   # "human" | "motion" | "noise"
    }
    events_col.insert_one(event)
    return jsonify({"status": "ok"}), 201


@app.route("/api/status")
def status():
    """Is the desk currently occupied? Based on last event within 30 s."""
    last = events_col.find_one(sort=[("timestamp", -1)])
    if last and (datetime.utcnow() - last["timestamp"]).total_seconds() < 30:
        occupied = True
        label = last.get("label", "motion")
        ts = last["timestamp"].strftime("%H:%M:%S")
    else:
        occupied = False
        label = "none"
        ts = "—"
    return jsonify({"occupied": occupied, "label": label, "last_event": ts})


@app.route("/api/log")
def log():
    """Last 10 motion events for the Security Log table."""
    docs = list(events_col.find(sort=[("timestamp", -1)], limit=10))
    rows = []
    for d in docs:
        rows.append({
            "time": d["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "duration": round(d.get("duration_sec", 0), 1),
            "label": d.get("label", "motion"),
        })
    return jsonify(rows)


@app.route("/api/hourly")
def hourly():
    """Events-per-hour for the last 24 hours (for the bar chart)."""
    since = datetime.utcnow() - timedelta(hours=24)
    docs = list(events_col.find({"timestamp": {"$gte": since}}))

    counts = [0] * 24
    now_hour = datetime.utcnow().hour
    for d in docs:
        h = d["timestamp"].hour
        bucket = (h - now_hour - 1) % 24
        counts[bucket] += 1

    # Build labels: "3h ago", "2h ago", "1h ago", "Now"
    labels = []
    for i in range(24):
        hrs_ago = 23 - i
        labels.append("Now" if hrs_ago == 0 else f"{hrs_ago}h ago")

    return jsonify({"labels": labels, "counts": counts})


@app.route("/api/total")
def total():
    since = datetime.utcnow() - timedelta(hours=24)
    count = events_col.count_documents({"timestamp": {"$gte": since}})
    return jsonify({"total_24h": count})


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD PAGE
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True, port=5050)
    