import time
import board
import adafruit_dht
import os
import csv
import signal
import sys
import glob
import threading
import RPi.GPIO as GPIO
import requests
import json
from datetime import datetime
from picamera2 import Picamera2
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS  # Import CORS

# Create directories for storing images and logs if they don't exist
IMAGE_DIR = "images"
LOG_DIR = "logs"

# GPIO setup for LEDs
CAMERA_PIN = 17
RED_LED_PIN = 27    # LED to indicate system is OFF
GREEN_LED_PIN = 22  # LED to indicate system is ON

GPIO.setmode(GPIO.BCM)
GPIO.setup(CAMERA_PIN, GPIO.OUT)
GPIO.setup(RED_LED_PIN, GPIO.OUT)
GPIO.setup(GREEN_LED_PIN, GPIO.OUT)

GPIO.output(CAMERA_PIN, GPIO.LOW)
GPIO.output(RED_LED_PIN, GPIO.HIGH)  # System starts OFF, so turn on red LED
GPIO.output(GREEN_LED_PIN, GPIO.LOW)

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
machine_id = "AgroX-37"
# Initialize CSV log file
csv_log_file = os.path.join(LOG_DIR, f"sensor_log_{datetime.now().strftime('%Y%m%d')}.csv")
csv_header = ['timestamp', 'temperature_c', 'temperature_f', 'humidity']

# Create/prepare the CSV file with headers if it doesn't exist
if not os.path.exists(csv_log_file):
    with open(csv_log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

# Control flags and data storage
sensor_active = False
camera_active = False
latest_sensor_data = {
    "temperature_c": None,
    "temperature_f": None,
    "humidity": None,
    "timestamp": None
}

# Server settings
SERVER_URL = "http://192.168.1.26:3005"  # Change this to your server URL

# Override settings from environment variables if available
if os.environ.get("SERVER_URL"):
    SERVER_URL = os.environ.get("SERVER_URL")

# Debug state tracking
state_change_count = 0

# Function to log messages with timestamp
def log_message(message, error=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_type = "ERROR" if error else "INFO"
    print(f"{timestamp} - {log_type} - {message}")

# Function to log sensor data to CSV
def log_to_csv(temp_c, temp_f, humidity):
    # Only log if we have actual data and sensor is active
    if not sensor_active:
        log_message(f"Skipping CSV log: sensor_active={sensor_active}")
        return
        
    if temp_c is None or temp_f is None or humidity is None:
        log_message("Skipping CSV log: missing data values")
        return
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, temp_c, temp_f, humidity])
    log_message(f"Data logged to CSV: {temp_c}°C, {temp_f}°F, {humidity}%")

# Function to update the latest sensor data
def update_sensor_data(temp_c, temp_f, humidity):
    global latest_sensor_data
    # Only update data if sensor is active
    if sensor_active:
        latest_sensor_data = {
            "temperature_c": temp_c,
            "temperature_f": temp_f,
            "humidity": humidity,
            "timestamp": time.time()
        }

# Function to send data to the server
def send_to_server(temp_c, humidity, image_path=None):
    """
    Send sensor data to the server.
    
    Args:
        temp_c (float): Temperature in Celsius
        humidity (float): Humidity percentage
        image_path (str, optional): Path to the image file to upload
    
    Returns:
        dict: Response from the server
    """
    if not temp_c or not humidity:
        log_message("Missing temperature or humidity data, skipping data upload", error=True)
        return None
        
    log_message(f"Sending data to server: Temp={temp_c}°C, Humidity={humidity}%")
    
    # Prepare the simplified payload - only temperature and humidity
    payload = {
        "temperature": temp_c,
        "humidity": humidity
    }
    
    # Add image path if provided
    if image_path and os.path.exists(image_path):
        payload["imagePath"] = image_path
        log_message(f"Including image in data: {image_path}")
    
    try:
        # Send the data to our server
        response = requests.post(
            f"{SERVER_URL}/api/upload-image",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30  # Longer timeout as image upload may take time
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            response_data = response.json()
            log_message(f"Data successfully sent: {response_data['message']}")
            return response_data
        else:
            log_message(f"Error from server: {response.status_code} - {response.text}", error=True)
            return {
                "success": False,
                "error": f"Server error: {response.status_code}"
            }
    except requests.RequestException as e:
        log_message(f"Failed to send data to server: {str(e)}", error=True)
        return {
            "success": False,
            "error": str(e)
        }

# Function to update status LEDs
def update_status_leds(is_on=False):
    """Update status LEDs based on system state"""
    if is_on:
        GPIO.output(GREEN_LED_PIN, GPIO.HIGH)
        GPIO.output(RED_LED_PIN, GPIO.LOW)
        log_message("Status LEDs: GREEN ON (System active)")
    else:
        GPIO.output(GREEN_LED_PIN, GPIO.LOW)
        GPIO.output(RED_LED_PIN, GPIO.HIGH)
        log_message("Status LEDs: RED ON (System inactive)")

# Function to blink LED
def blink_led(count=3, delay=0.2):
    """Blink LED the specified number of times with the given delay."""
    for _ in range(count):
        GPIO.output(CAMERA_PIN, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(CAMERA_PIN, GPIO.LOW)
        time.sleep(delay)

# Function to clean up resources
def cleanup_resources():
    try:
        if 'sensor' in globals():
            sensor.exit()
    except:
        pass
    try:
        if 'picam2' in globals() and 'camera_available' in locals() and camera_available:
            picam2.close()
    except:
        pass
    # Clean up GPIO
    GPIO.cleanup()
    log_message("Resources cleaned up")

# Setup signal handler for graceful shutdown
def signal_handler(sig, frame):
    log_message("Shutting down gracefully...")
    cleanup_resources()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# API routes
@app.route("/")
def root():
    return jsonify({"message": "AgroX-IoT System API is running"})

@app.route("/api/control/on")
def turn_on_system():
    global sensor_active, camera_active, state_change_count
    
    state_change_count += 1
    log_message(f"STATE CHANGE #{state_change_count}: Turning ON all systems")
    log_message(f"Previous state: Sensor={sensor_active}, Camera={camera_active}")
    
    sensor_active = True
    camera_active = True
    
    # Update status LEDs
    update_status_leds(True)
    
    log_message(f"New state: Sensor={sensor_active}, Camera={camera_active}")
    return jsonify({
        "sensor_active": sensor_active,
        "camera_active": camera_active,
        "message": "All systems turned on"
    })

@app.route("/api/control/off")
def turn_off_system():
    global sensor_active, camera_active, state_change_count
    
    state_change_count += 1
    log_message(f"STATE CHANGE #{state_change_count}: Turning OFF all systems")
    log_message(f"Previous state: Sensor={sensor_active}, Camera={camera_active}")
    
    sensor_active = False
    camera_active = False
    
    # Update status LEDs
    update_status_leds(False)
    
    log_message(f"New state: Sensor={sensor_active}, Camera={camera_active}")
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

@app.route("/api/manual-upload", methods=["POST"])
def manual_upload():
    """
    Manually trigger sensor data and image upload to the server
    and return the IPFS image URI
    """
    try:
        # Check if sensor is active
        if not sensor_active:
            return jsonify({
                "success": False,
                "error": "Sensor is inactive. Please activate the sensor first."
            }), 400
            
        # Get the latest sensor data
        temperature_c = latest_sensor_data.get("temperature_c")
        humidity = latest_sensor_data.get("humidity")
        
        if temperature_c is None or humidity is None:
            return jsonify({
                "success": False,
                "error": "No sensor data available. Please wait for sensor readings."
            }), 400
            
        # Get the latest image if camera is active and available
        image_to_upload = None
        if camera_active:
            # Check if camera hardware is available
            camera_available = 'picam2' in globals() and hasattr(picam2, 'capture_file')
            
            if camera_available:
                images = sorted(glob.glob(f"{IMAGE_DIR}/*.jpg"))
                if images:
                    image_to_upload = images[-1]
                    log_message(f"Using latest image for manual upload: {image_to_upload}")
                else:
                    log_message("No images available for upload", error=True)
            else:
                log_message("Camera hardware is unavailable, continuing without image")
        else:
            log_message("Camera is inactive, no image will be uploaded")
            
        # Send data to server
        server_result = send_to_server(temperature_c, humidity, image_to_upload)
        
        if server_result and "data" in server_result and "imageUrl" in server_result["data"]:
            return jsonify({
                "success": True,
                "message": "Data uploaded successfully",
                "temperature": temperature_c,
                "humidity": humidity,
                "imageUrl": server_result["data"]["imageUrl"],
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to get image URL from server",
                "server_response": server_result
            }), 500
            
    except Exception as e:
        log_message(f"Error in manual upload: {str(e)}", error=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/manual-upload/get", methods=["GET"])
def manual_upload_get():
    """
    GET endpoint to manually trigger sensor data and image upload to the server
    and return the IPFS image URI
    """
    try:
        # Check if sensor is active
        if not sensor_active:
            return jsonify({
                "success": False,
                "error": "Sensor is inactive. Please activate the sensor first."
            }), 400
            
        # Get the latest sensor data
        temperature_c = latest_sensor_data.get("temperature_c")
        humidity = latest_sensor_data.get("humidity")
        
        if temperature_c is None or humidity is None:
            return jsonify({
                "success": False,
                "error": "No sensor data available. Please wait for sensor readings."
            }), 400
            
        # Get the latest image if camera is active and available
        image_to_upload = None
        if camera_active:
            # Check if camera hardware is available
            camera_available = 'picam2' in globals() and hasattr(picam2, 'capture_file')
            
            if camera_available:
                images = sorted(glob.glob(f"{IMAGE_DIR}/*.jpg"))
                if images:
                    image_to_upload = images[-1]
                    log_message(f"Using latest image for GET manual upload: {image_to_upload}")
                else:
                    log_message("No images available for upload", error=True)
            else:
                log_message("Camera hardware is unavailable, continuing without image")
        else:
            log_message("Camera is inactive, no image will be uploaded")
            
        # Send data to server
        server_result = send_to_server(temperature_c, humidity, image_to_upload)
        
        if server_result and "data" in server_result and "imageUrl" in server_result["data"]:
            return jsonify({
                "success": True,
                "message": "Data uploaded successfully",
                "temperature": temperature_c,
                "humidity": humidity,
                "imageUrl": server_result["data"]["imageUrl"],
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to get image URL from server",
                "server_response": server_result
            }), 500
            
    except Exception as e:
        log_message(f"Error in manual upload GET: {str(e)}", error=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/control/status")
def get_status():
    return jsonify({
        "sensor_active": sensor_active,
        "camera_active": camera_active,
        "message": "Current system status"
    })

@app.route("/api/server/settings", methods=["POST"])
def update_server_settings():
    global SERVER_URL
    
    # Parse JSON data from request
    settings = request.get_json()
    if not settings:
        return jsonify({
            "success": False,
            "message": "No settings provided"
        }), 400
    
    # Track what was changed
    changes = []
    
    # Update settings if provided
    if "server_url" in settings:
        SERVER_URL = settings["server_url"]
        changes.append(f"Server URL set to {SERVER_URL}")
    
    if not changes:
        message = "No changes made to server settings"
    else:
        message = ". ".join(changes)
    
    log_message(f"Server settings updated: {message}")
    return jsonify({
        "success": True,
        "message": message,
        "settings": {
            "server_url": SERVER_URL
        }
    })

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
    prev_both_active = sensor_active and camera_active
    
    # Update sensor status if provided
    if "sensor" in control and control["sensor"] != sensor_active:
        state_change_count += 1
        state_changed = True
        log_message(f"STATE CHANGE #{state_change_count}: Sensor {sensor_active} -> {control['sensor']}")
        sensor_active = control["sensor"]
        status = "started" if control["sensor"] else "stopped"
        changes.append(f"Sensor data collection {status}")
    
    # Update camera status if provided
    if "camera" in control and control["camera"] != camera_active:
        if not state_changed:
            state_change_count += 1
        state_changed = True
        log_message(f"STATE CHANGE #{state_change_count}: Camera {camera_active} -> {control['camera']}")
        camera_active = control["camera"]
        status = "started" if control["camera"] else "stopped"
        changes.append(f"Camera capture {status}")
    
    # If nothing was changed, inform the user
    if not changes:
        message = "No changes made. Specify 'sensor' and/or 'camera' with boolean values."
    else:
        message = ". ".join(changes)
    
    # Update LEDs based on current state
    both_active_now = sensor_active and camera_active
    both_inactive_now = not sensor_active and not camera_active
    
    if both_active_now:
        update_status_leds(True)
    elif both_inactive_now:
        update_status_leds(False)
    else:
        # Partial state - blink both LEDs to indicate mixed state
        GPIO.output(GREEN_LED_PIN, GPIO.HIGH if sensor_active else GPIO.LOW)
        GPIO.output(RED_LED_PIN, GPIO.HIGH if camera_active else GPIO.LOW)
    
    log_message(f"Current state: Sensor={sensor_active}, Camera={camera_active}")
    return jsonify({
        "sensor_active": sensor_active,
        "camera_active": camera_active,
        "message": message
    })

# Sensor monitoring function - runs in a separate thread
def sensor_monitoring_loop():
    global sensor, picam2
    
    # Initialize the camera with error handling
    camera_available = False
    try:
        picam2 = Picamera2()
        camera_config = picam2.create_still_configuration()
        picam2.configure(camera_config)
        picam2.start()
        camera_available = True
        log_message("Camera initialized successfully")
    except Exception as e:
        log_message(f"Camera initialization failed: {str(e)}", error=True)
        log_message("System will continue without camera functionality")
        camera_available = False

    # Initialize DHT22 sensor
    sensor = adafruit_dht.DHT22(board.D4)

    # Time tracking for camera
    last_capture_time = 0
    CAPTURE_INTERVAL = 60  # Capture every 60 seconds (1 minute)

    # Debug state change counter
    previous_sensor_state = sensor_active
    previous_camera_state = camera_active
    state_changes = 0

    log_message("Sensor monitoring thread started")
    
    running = True
    while running:
        try:
            # Get current status
            sensor_status = sensor_active
            camera_status = camera_active and camera_available
            
            # Track state changes for debugging
            if (previous_sensor_state != sensor_status) or (previous_camera_state != camera_status):
                state_changes += 1
                log_message(f"MONITOR: STATE CHANGE #{state_changes}: Sensor {previous_sensor_state}->{sensor_status}, Camera {previous_camera_state}->{camera_status}")
                previous_sensor_state = sensor_status
                previous_camera_state = camera_status
            
            # Log current status periodically
            status_text = f"Status: Sensor {'ACTIVE' if sensor_status else 'INACTIVE'}, Camera {'ACTIVE' if camera_status else 'INACTIVE'}"
            if camera_active and not camera_available:
                status_text += " (Camera hardware unavailable)"
            log_message(status_text)
            
            # If both sensor and camera are inactive, just sleep and continue the loop
            if not sensor_status and not camera_status:
                log_message("Both sensor and camera are inactive. Monitoring paused.")
                time.sleep(5)  # Check every 5 seconds
                continue
            
            current_time = time.time()
            temperature_c = None
            temperature_f = None
            humidity = None
            latest_image_path = None
            
            # Only read from sensor if sensor is active
            if sensor_status:
                try:
                    # Read sensor data
                    temperature_c = sensor.temperature
                    temperature_f = temperature_c * (9 / 5) + 32
                    humidity = sensor.humidity
                    
                    # Print data
                    log_message(f"Temp={temperature_c:0.1f}ºC, Temp={temperature_f:0.1f}ºF, Humidity={humidity:0.1f}%")
                    
                    # Update latest sensor data
                    update_sensor_data(temperature_c, temperature_f, humidity)
                    
                    # Log to CSV
                    log_to_csv(temperature_c, temperature_f, humidity)
                except RuntimeError as error:
                    # Errors happen fairly often, DHT's are hard to read, just keep going
                    log_message(f"Sensor read error: {error.args[0]}", error=True)
                    time.sleep(2.0)
                    continue
                except Exception as error:
                    log_message(f"Critical error: {str(error)}", error=True)
                    cleanup_resources()
                    sys.exit(1)
            else:
                log_message("Sensor is inactive, skipping sensor reading")
            
            # Check if camera is active and available, and it's time to capture an image
            if camera_status and camera_available and current_time - last_capture_time >= CAPTURE_INTERVAL:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_path = f"{IMAGE_DIR}/image_{timestamp}.jpg"
                    
                    # Double-check camera is still active
                    if camera_active:
                        # Blink LED to indicate picture is being taken
                        blink_led()
                        
                        # Capture image
                        picam2.capture_file(image_path)
                        log_message(f"Image captured: {image_path}")
                        latest_image_path = image_path
                        
                        # Update last capture time
                        last_capture_time = current_time
                        
                        # Calculate time until next capture
                        next_capture = last_capture_time + CAPTURE_INTERVAL
                        next_capture_time = datetime.fromtimestamp(next_capture).strftime("%H:%M:%S")
                        log_message(f"Next image scheduled for: {next_capture_time}")
                    else:
                        log_message("Camera was deactivated during capture preparation, skipping")
                except Exception as error:
                    log_message(f"Camera error: {str(error)}", error=True)
                    camera_available = False  # Mark camera as unavailable after error
                    log_message("Camera marked as unavailable due to error")
            elif camera_status and not camera_available:
                log_message("Camera is active but hardware is unavailable, skipping image capture")
            
            # Short sleep between readings
            time.sleep(3.0)
        except Exception as e:
            log_message(f"Unexpected error in monitoring loop: {str(e)}", error=True)
            time.sleep(5)  # Wait a bit before retrying

def main():
    """Main function to start both the API server and sensor monitoring."""
    log_message("Starting AgroX-IoT All-in-One System...")
    
    # Initial LED state - start with system off
    update_status_leds(False)
    
    # Start sensor monitoring thread
    sensor_thread = threading.Thread(target=sensor_monitoring_loop, daemon=True)
    sensor_thread.start()
    log_message("Sensor monitoring thread started")
    
    # Start Flask API server
    log_message("Starting API server on http://0.0.0.0:8000")
    log_message("Control your system using the following endpoints:")
    log_message("- Turn ON: http://[ip]:8000/api/control/on")
    log_message("- Turn OFF: http://[ip]:8000/api/control/off")
    log_message("- Check status: http://[ip]:8000/api/control/status")
    log_message("- Manual upload (POST): POST http://[ip]:8000/api/manual-upload (returns IPFS image URL)")
    log_message("- Manual upload (GET): http://[ip]:8000/api/manual-upload/get (returns IPFS image URL)")
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

if __name__ == "__main__":
    main() 