from flask import Blueprint, request, jsonify, Response
import datetime
import pymongo
from videoStream import generate_video

anomaly_api = Blueprint('anomaly_api', __name__)

# Temporary in-memory store (can be replaced with DB)
robot_streams = {}  
from pymongo import MongoClient
import os

mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://seecure:your_encoded_password@cluster0.p1pyx18.mongodb.net/?retryWrites=true&w=majority")
client = MongoClient(mongo_uri)
db = client["SSRCP"]
robot_collection = db["robot"]

@anomaly_api.route('/getRobotAnomaly', methods=['GET'])
def get_robot_anomaly():
    robot_id = request.args.get("robotId")
    if not robot_id:
        return jsonify({"error": "robotId is required"}), 400

    try:
        robot_doc = robot_collection.find_one({"userId": robot_id}, sort=[("time", -1)])

        if not robot_doc:
            return jsonify({"error": f"No data found for robotId: {robot_id}"}), 404

        # Extract necessary metadata
        car_meta = robot_doc.get("carMeta", {
            "model": robot_doc.get("car_type", "unknown"),
            "velocity": robot_doc.get("velocity"),
            "location": robot_doc.get("location", {}),
            "orientation": robot_doc.get("orientation", {})
        })

        stream_url = f"http://localhost:5000/video/{robot_id}"
        timestamp = robot_doc.get("time", datetime.datetime.utcnow()).isoformat()

        return jsonify({
            "robotId": robot_id,
            "status": "Anomaly Detected",
            "threatType": "Unauthorized Person",
            "confidence": 0.92,
            "anomalyLocation": {
                "x": car_meta["location"]["x"] + 0.22,
                "y": car_meta["location"]["y"] + 0.20,
                "z": car_meta["location"]["z"]
            },
            "cameraView": "front",
            "robotLocation": car_meta["location"],
            "orientation": car_meta["orientation"],
            "mjpegStreamUrl": stream_url,
            "timestamp": timestamp
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@anomaly_api.route('/video/<robotId>', methods=['GET'])
def video_feed(robotId):
    return Response(generate_video(), mimetype='multipart/x-mixed-replace; boundary=frame')
