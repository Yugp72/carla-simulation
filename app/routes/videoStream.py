import os
import cv2

# MJPEG streaming folder
IMAGE_FOLDER = "images"
image_paths = []

def generate_video():
    while True:
        if image_paths:
            image_path = image_paths.pop(0)
            img = cv2.imread(image_path)
            if img is not None:
                _, buffer = cv2.imencode('.jpg', img)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                os.remove(image_path)

def append_image(image_path):
    image_paths.append(image_path)

def clear_images():
    image_paths.clear()
