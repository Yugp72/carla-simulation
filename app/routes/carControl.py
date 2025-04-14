import base64
from io import BytesIO
import math
import os
import random
import threading
import time
from datetime import datetime
from flask import request, Blueprint

import carla
from PIL import Image

from videoStream import append_image

control_routes = Blueprint('control_routes', __name__)

latest_frame = {}
sensors = {}

def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def camera_callback(image, user_id, vehicle_id, pos):
    array = image.raw_data
    img = Image.frombytes("RGBA", (image.width, image.height), bytes(array))
    img = img.convert("RGB")
    output_file_path = f"./images/{user_id}_{vehicle_id}_{pos}.png"
    img.save(output_file_path, format="PNG")
    append_image(output_file_path)

    if latest_frame[str(user_id)][str(vehicle_id)] is None:
        latest_frame[str(user_id)][str(vehicle_id)] = {pos: image_to_base64(img)}
    else:
        latest_frame[str(user_id)][str(vehicle_id)][pos] = image_to_base64(img)
    time.sleep(2)

def setup_spectator_camera(world, vehicle):
    vehicle_transform = vehicle.get_transform()
    spectator = world.get_spectator()
    spectator_transform = carla.Transform(
        vehicle_transform.location + carla.Location(x=-6, y=0, z=2),
        vehicle_transform.rotation
    )
    spectator.set_transform(spectator_transform)

def update_vehicle_stats(userID, mysqlRobotId, vehicle, camFront, camTop, world):
    try:
        velocity = vehicle.get_velocity()
        location = vehicle.get_location()
        transform = vehicle.get_transform()
        acceleration = vehicle.get_acceleration()
        control = vehicle.get_control()

        vehicle_data = {
            "id": vehicle.id,
            "userId": userID,
            "img": {
                "top": latest_frame[str(userID)][str(vehicle.id)]["top"],
                "front": latest_frame[str(userID)][str(vehicle.id)]["front"],
            },
            "mysqlRobotId": mysqlRobotId,
            "cameraId": {
                "top": camTop,
                "front": camFront,
            },
            "velocity": math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2),
            "location": {
                "x": location.x,
                "y": location.y,
                "z": location.z
            },
            "acceleration": math.sqrt(acceleration.x**2 + acceleration.y**2 + acceleration.z**2),
            "throttle": control.throttle,
            "steering": control.steer,
            "brake": control.brake,
            "gear": control.gear,
            "orientation": {
                "pitch": transform.rotation.pitch,
                "yaw": transform.rotation.yaw,
                "roll": transform.rotation.roll
            },
            "time": datetime.now(),
        }

        return vehicle_data
    except Exception as e:
        print(f"Error updating vehicle stats: {e}")

@control_routes.route("/createVehicle", methods=['GET'])
def create_vehicle():
    userId = request.args.get('id', '1')
    mysqlRobotId = request.args.get('robotId', '1')
    car_type = request.args.get('car_model', 'vehicle.audi.a2')
    weather = request.args.get('weather', 'ClearNoon')

    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    world = client.get_world()
    world.set_weather(getattr(carla.WeatherParameters, weather))

    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.find(car_type)
    spawn_points = world.get_map().get_spawn_points()
    random_spawn_point = random.choice(spawn_points)
    vehicle = world.try_spawn_actor(vehicle_bp, random_spawn_point)

    latest_frame[str(userId)] = {str(vehicle.id): {"top": None, "front": None}}

    camera_bp = blueprint_library.find('sensor.camera.rgb')
    camera_bp.set_attribute('image_size_x', '800')
    camera_bp.set_attribute('image_size_y', '600')

    cameraFront = world.spawn_actor(
        camera_bp,
        carla.Transform(carla.Location(x=-5.0, y=0.0, z=3.0), carla.Rotation(pitch=-15.0)),
        attach_to=vehicle
    )
    cameraTop = world.spawn_actor(
        camera_bp,
        carla.Transform(carla.Location(x=0.0, y=0.0, z=5.0), carla.Rotation(pitch=-90.0)),
        attach_to=vehicle
    )

    sensors[userId] = {vehicle.id: {"front": cameraFront, "top": cameraTop}}
    cameraFront.listen(lambda frame: camera_callback(frame, userId, vehicle.id, "front"))
    cameraTop.listen(lambda frame: camera_callback(frame, userId, vehicle.id, "top"))

    vehicle.set_autopilot(True)

    def generate():
        while True:
            update_vehicle_stats(userId, mysqlRobotId, vehicle, cameraFront.id, cameraTop.id, world)
            setup_spectator_camera(world, vehicle)
            time.sleep(2)

    threading.Thread(target=generate).start()

    return {
        "vehicle": vehicle.id,
        "cameraFront": cameraFront.id,
        "cameraTop": cameraTop.id,
        "car_type": car_type
    }, 200
