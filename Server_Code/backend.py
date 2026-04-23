from pymongo import MongoClient
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, request, Response
import cv2
import numpy as np
import os


### Setup Data Base ###
load_dotenv("../../.env/.env")
uri = os.getenv("MONGO_URI")

client = MongoClient(uri)
db = client["EyeDataPoints"]
database = db["LiveData"]


app = Flask(__name__)
@app.route("/frame", methods=["POST"])
def receive_frame():
    file = request.files["frame"].read()
      
    # convert to numpy array
    np_arr = np.frombuffer(file, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # show or process
    cv2.imshow("Backend Stream", frame)
    cv2.waitKey(1)

    return "OK", 200


     
        

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



