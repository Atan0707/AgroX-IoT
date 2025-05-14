from flask import Flask, jsonify, request, send_file
import os
import glob
from typing import Dict, Optional
import time
from datetime import datetime
import json

# Create a Flask instance
app = Flask(__name__)

# Data storage
IMAGE_DIR = "images"
LOG_DIR = "logs"
latest_sensor_data = {
    "temperature_c": None,
    "temperature_f": None,
    "humidity": None,
    "timestamp": None
}

# Control flags
sensor_active = False
camera_active = False

# Add state change tracking for debugging
state_change_count = 0

# Routes
@app.route("/")
def root():
    return jsonify({"message": "RaspberryPi Sensor API is running"})

@app.route("/api/control/on")
def turn_on_system():
    global sensor_active, camera_active, state_change_count
    
    state_change_count += 1
    print(f"STATE CHANGE #{state_change_count}: Turning ON all systems")
    print(f"Previous state: Sensor={sensor_active}, Camera={camera_active}")
    
    sensor_active = True
    camera_active = True
    
    print(f"New state: Sensor={sensor_active}, Camera={camera_active}")
    return jsonify({
        "sensor_active": sensor_active,
        "camera_active": camera_active,
        "message": "All systems turned on"
    })

@app.route("/api/control/off")
def turn_off_system():
    global sensor_active, camera_active, state_change_count
    
    state_change_count += 1
    print(f"STATE CHANGE #{state_change_count}: Turning OFF all systems")
    print(f"Previous state: Sensor={sensor_active}, Camera={camera_active}")
    
    sensor_active = False
    camera_active = False
    
    print(f"New state: Sensor={sensor_active}, Camera={camera_active}")
    return jsonify({
        "sensor_active": sensor_active,
        "camera_active": camera_active,
        "message": "All systems turned off"
    })

@app.route("/api/sensor")
def get_sensor_data():
    if latest_sensor_data["timestamp"] is None:
        return jsonify({"detail": "Sensor data not yet available"}), 503
    return jsonify(latest_sensor_data)

@app.route("/api/images/latest")
def get_latest_image():
    try:
        # Get the latest image
        images = sorted(glob.glob(f"{IMAGE_DIR}/*.jpg"))
        if not images:
            return jsonify({"detail": "No images found"}), 404
        latest_image = images[-1]
        return send_file(latest_image)
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/api/images/list")
def list_images():
    try:
        images = sorted(glob.glob(f"{IMAGE_DIR}/*.jpg"))
        # Return just the filenames, not full paths
        return jsonify({"images": [os.path.basename(img) for img in images]})
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/api/images/<image_name>")
def get_image(image_name):
    image_path = os.path.join(IMAGE_DIR, image_name)
    if not os.path.exists(image_path):
        return jsonify({"detail": "Image not found"}), 404
    return send_file(image_path)

# Log endpoints
@app.route("/api/logs/list")
def list_logs():
    try:
        if not os.path.exists(LOG_DIR):
            return jsonify({"logs": []})
        
        logs = sorted(glob.glob(f"{LOG_DIR}/*.csv"))
        return jsonify({"logs": [os.path.basename(log) for log in logs]})
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

@app.route("/api/logs/<log_name>")
def get_log(log_name):
    log_path = os.path.join(LOG_DIR, log_name)
    if not os.path.exists(log_path):
        return jsonify({"detail": "Log file not found"}), 404
    return send_file(log_path, mimetype="text/csv")

@app.route("/api/logs/today")
def get_today_log():
    try:
        today = datetime.now().strftime("%Y%m%d")
        log_name = f"sensor_log_{today}.csv"
        log_path = os.path.join(LOG_DIR, log_name)
        
        if not os.path.exists(log_path):
            return jsonify({"detail": "Today's log file not found"}), 404
            
        return send_file(log_path, mimetype="text/csv")
    except Exception as e:
        return jsonify({"detail": str(e)}), 500

# Control endpoints
@app.route("/api/control/status")
def get_status():
    return jsonify({
        "sensor_active": sensor_active,
        "camera_active": camera_active,
        "message": "Current system status"
    })

# Unified control endpoint
@app.route("/api/control", methods=["POST"])
def control_system():
    global sensor_active, camera_active, state_change_count
    
    # Parse JSON data from request
    control = request.get_json()
    if not control:
        return jsonify({
            "sensor_active": sensor_active,
            "camera_active": camera_active,
            "message": "No data provided"
        }), 400
    
    # Track what was changed for the response message
    changes = []
    state_changed = False
    
    # Update sensor status if provided
    if "sensor" in control and control["sensor"] != sensor_active:
        state_change_count += 1
        state_changed = True
        print(f"STATE CHANGE #{state_change_count}: Sensor {sensor_active} -> {control['sensor']}")
        sensor_active = control["sensor"]
        status = "started" if control["sensor"] else "stopped"
        changes.append(f"Sensor data collection {status}")
    
    # Update camera status if provided
    if "camera" in control and control["camera"] != camera_active:
        if not state_changed:
            state_change_count += 1
        state_changed = True
        print(f"STATE CHANGE #{state_change_count}: Camera {camera_active} -> {control['camera']}")
        camera_active = control["camera"]
        status = "started" if control["camera"] else "stopped"
        changes.append(f"Camera capture {status}")
    
    # If nothing was changed, inform the user
    if not changes:
        message = "No changes made. Specify 'sensor' and/or 'camera' with boolean values."
    else:
        message = ". ".join(changes)
    
    print(f"Current state: Sensor={sensor_active}, Camera={camera_active}")
    return jsonify({
        "sensor_active": sensor_active,
        "camera_active": camera_active,
        "message": message
    })

# This function will be imported by dht22_with_camera.py
def update_sensor_data(temp_c: float, temp_f: float, humidity: float):
    global latest_sensor_data
    # Only update data if sensor is active
    if sensor_active:
        latest_sensor_data = {
            "temperature_c": temp_c,
            "temperature_f": temp_f,
            "humidity": humidity,
            "timestamp": time.time()
        }

# Function to check if camera is active
def is_camera_active():
    return camera_active

# Run the Flask server
if __name__ == "__main__":
    print("Starting Flask API server on http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False) 