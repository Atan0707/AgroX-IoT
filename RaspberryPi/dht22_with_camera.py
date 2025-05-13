import time
import board
import adafruit_dht
import os
import csv
from datetime import datetime
from picamera2 import Picamera2
import api_server  # Import the API server module

# Create directory for storing images if it doesn't exist
IMAGE_DIR = "images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# Create directory for storing logs if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Initialize CSV log file
csv_log_file = os.path.join(LOG_DIR, f"sensor_log_{datetime.now().strftime('%Y%m%d')}.csv")
csv_header = ['timestamp', 'temperature_c', 'temperature_f', 'humidity', 'sensor_active', 'camera_active']

# Create/prepare the CSV file with headers if it doesn't exist
if not os.path.exists(csv_log_file):
    with open(csv_log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

# Initialize the camera
picam2 = Picamera2()
camera_config = picam2.create_still_configuration()
picam2.configure(camera_config)
picam2.start()

# Initialize DHT22 sensor
sensor = adafruit_dht.DHT22(board.D4)

# Time tracking for camera
last_capture_time = 0
CAPTURE_INTERVAL = 60  # Capture every 60 seconds (1 minute)

print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Starting combined DHT22 and camera monitoring...")

# Function to log messages with timestamp
def log_message(message, error=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_type = "ERROR" if error else "INFO"
    print(f"{timestamp} - {log_type} - {message}")

# Function to log sensor data to CSV
def log_to_csv(temp_c, temp_f, humidity, sensor_active, camera_active):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, temp_c, temp_f, humidity, sensor_active, camera_active])

while True:
    current_time = time.time()
    
    try:
        # Read sensor data - this runs regardless of active flag to keep sensor alive
        temperature_c = sensor.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = sensor.humidity
        
        # Get status for logging
        sensor_status = api_server.sensor_active
        camera_status = api_server.is_camera_active()
        
        # Log to CSV
        log_to_csv(temperature_c, temperature_f, humidity, sensor_status, camera_status)
        
        # Print and update API only if sensor is active
        log_message(f"Temp={temperature_c:0.1f}ºC, Temp={temperature_f:0.1f}ºF, Humidity={humidity:0.1f}%")
        
        status_text = f"Status: Sensor {'ACTIVE' if sensor_status else 'INACTIVE'}, Camera {'ACTIVE' if camera_status else 'INACTIVE'}"
        log_message(status_text)
        
        # Update API server with latest sensor data
        # The API server will check if sensor is active before updating data
        api_server.update_sensor_data(temperature_c, temperature_f, humidity)
        
        # Check if camera is active and it's time to capture an image
        if camera_status and current_time - last_capture_time >= CAPTURE_INTERVAL:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"{IMAGE_DIR}/image_{timestamp}.jpg"
            
            # Capture image
            picam2.capture_file(image_path)
            log_message(f"Image captured: {image_path}")
            
            # Update last capture time
            last_capture_time = current_time
            
            # Calculate time until next capture
            next_capture = last_capture_time + CAPTURE_INTERVAL
            next_capture_time = datetime.fromtimestamp(next_capture).strftime("%H:%M:%S")
            log_message(f"Next image scheduled for: {next_capture_time}")

    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        log_message(f"Sensor read error: {error.args[0]}", error=True)
        time.sleep(2.0)
        continue
    except Exception as error:
        log_message(f"Critical error: {str(error)}", error=True)
        sensor.exit()
        picam2.close()
        raise error
 
    # Short sleep between readings
    time.sleep(3.0) 