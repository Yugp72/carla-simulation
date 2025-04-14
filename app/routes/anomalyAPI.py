from flask import Blueprint, request, jsonify, Response
import datetime

from videoStream import generate_video

anomaly_api = Blueprint('anomaly_api', __name__)

# Temporary in-memory store (can be replaced with DB)
robot_streams = {}

@anomaly_api.route('/submitData', methods=['POST'])
def submit_data():
    data = request.json

    robot_id = data.get("robotId")
    stream_url = data.get("mjpegStreamUrl")
    car_meta = data.get("carMeta")

    if not robot_id or not stream_url or not car_meta:
        return jsonify({"error": "Missing required fields"}), 400

    robot_streams[robot_id] = {
        "stream_url": stream_url,
        "car_meta": car_meta,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    return jsonify({"message": "Stream and metadata registered successfully"})


@anomaly_api.route('/getAnomalyCoordinates', methods=['GET'])
def get_anomaly_coordinates():
    robot_id = request.args.get("robotId")

    if not robot_id:
        return jsonify({"error": "robotId is required"}), 400

    car_meta = {
        "model": "vehicle.audi.a2",
        "velocity": 22.5,
        "location": {"x": 110.0, "y": -40.0, "z": 0.0},
        "orientation": {"yaw": 60.0, "pitch": 0.0, "roll": 0.0}
    }

    stream_url = f"http://localhost:5000/video/{robot_id}"
    timestamp = datetime.datetime.utcnow().isoformat()

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


@anomaly_api.route('/video/<robotId>', methods=['GET'])
def video_feed(robotId):
    return Response(generate_video(), mimetype='multipart/x-mixed-replace; boundary=frame')
