import time
import board
import adafruit_dht
import os
import csv
from datetime import datetime
from picamera2 import Picamera2
import api_server  # Import the API server module
import sys
import signal

# Setup signal handler for graceful shutdown
def signal_handler(sig, frame):
    log_message("Shutting down gracefully...")
    try:
        sensor.exit()
        picam2.close()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
csv_header = ['timestamp', 'temperature_c', 'temperature_f', 'humidity']

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

# Print initial API server state for debugging
print(f"API Server initial state: Sensor active = {api_server.sensor_active}, Camera active = {api_server.is_camera_active()}")

print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Starting combined DHT22 and camera monitoring (initially inactive)...")

# Function to log messages with timestamp
def log_message(message, error=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_type = "ERROR" if error else "INFO"
    print(f"{timestamp} - {log_type} - {message}")

# Function to log sensor data to CSV
def log_to_csv(temp_c, temp_f, humidity):
    # Only log if we have actual data and sensor is active
    if not api_server.sensor_active:
        log_message(f"Skipping CSV log: sensor_active={api_server.sensor_active}")
        return
        
    if temp_c is None or temp_f is None or humidity is None:
        log_message("Skipping CSV log: missing data values")
        return
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(csv_log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, temp_c, temp_f, humidity])
    log_message(f"Data logged to CSV: {temp_c}°C, {temp_f}°F, {humidity}%")

# Function to clean up resources
def cleanup_resources():
    try:
        sensor.exit()
    except:
        pass
    try:
        picam2.close()
    except:
        pass
    log_message("Resources cleaned up")

# Debug state change counter
previous_sensor_state = api_server.sensor_active
previous_camera_state = api_server.is_camera_active()
state_changes = 0

running = True
while running:
    # Get current status directly from API server
    sensor_status = api_server.sensor_active
    camera_status = api_server.is_camera_active()
    
    # Track state changes for debugging
    if (previous_sensor_state != sensor_status) or (previous_camera_state != camera_status):
        state_changes += 1
        log_message(f"STATE CHANGE #{state_changes}: Sensor {previous_sensor_state}->{sensor_status}, Camera {previous_camera_state}->{camera_status}")
        previous_sensor_state = sensor_status
        previous_camera_state = camera_status
    
    # Log current status
    status_text = f"Status: Sensor {'ACTIVE' if sensor_status else 'INACTIVE'}, Camera {'ACTIVE' if camera_status else 'INACTIVE'}"
    log_message(status_text)
    
    # If both sensor and camera are inactive, just sleep and check for reactivation
    if not sensor_status and not camera_status:
        log_message("Both sensor and camera are inactive. System paused until reactivated.")
        
        # Check periodically if either has been reactivated
        inactive_check_interval = 5  # seconds - checking more frequently now
        start_inactive = time.time()
        
        while not api_server.sensor_active and not api_server.is_camera_active():
            # Sleep for a short time to avoid busy waiting
            time.sleep(inactive_check_interval)
            
            # If we've been inactive for too long (5 minutes), exit the script
            if time.time() - start_inactive > 300:  # 5 minutes
                log_message("System inactive for 5 minutes. Shutting down sensor and camera.")
                cleanup_resources()
                sys.exit(0)
        
        # If we exit the loop, it means one of the components was reactivated
        log_message("System reactivated")
        continue
    
    current_time = time.time()
    temperature_c = None
    temperature_f = None
    humidity = None
    
    # Only read from sensor if sensor is active
    if sensor_status:
        try:
            # Read sensor data
            temperature_c = sensor.temperature
            temperature_f = temperature_c * (9 / 5) + 32
            humidity = sensor.humidity
            
            # Print data
            log_message(f"Temp={temperature_c:0.1f}ºC, Temp={temperature_f:0.1f}ºF, Humidity={humidity:0.1f}%")
            
            # Update API server with latest sensor data
            api_server.update_sensor_data(temperature_c, temperature_f, humidity)
            
            # Log to CSV (the function will check sensor_active internally as well)
            log_to_csv(temperature_c, temperature_f, humidity)
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
    else:
        log_message("Sensor is inactive, skipping sensor reading")
    
    # Check if camera is active and it's time to capture an image
    if camera_status and current_time - last_capture_time >= CAPTURE_INTERVAL:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"{IMAGE_DIR}/image_{timestamp}.jpg"
            
            # Double-check camera is still active before capturing
            if api_server.is_camera_active():
                # Capture image
                picam2.capture_file(image_path)
                log_message(f"Image captured: {image_path}")
                
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
 
    # Short sleep between readings
    time.sleep(3.0) 