import time
import board
import adafruit_dht
import os
from datetime import datetime
from picamera2 import Picamera2
import api_server  # Import the API server module

# Create directory for storing images if it doesn't exist
IMAGE_DIR = "images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

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

print("Starting combined DHT22 and camera monitoring...")

while True:
    current_time = time.time()
    
    try:
        # Read sensor data
        temperature_c = sensor.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = sensor.humidity
        print("Temp={0:0.1f}ºC, Temp={1:0.1f}ºF, Humidity={2:0.1f}%".format(
            temperature_c, temperature_f, humidity))
        
        # Update API server with latest sensor data
        api_server.update_sensor_data(temperature_c, temperature_f, humidity)
        
        # Check if it's time to capture an image
        if current_time - last_capture_time >= CAPTURE_INTERVAL:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"{IMAGE_DIR}/image_{timestamp}.jpg"
            
            # Capture image
            picam2.capture_file(image_path)
            print(f"Image captured: {image_path}")
            
            # Update last capture time
            last_capture_time = current_time

    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print(error.args[0])
        time.sleep(2.0)
        continue
    except Exception as error:
        sensor.exit()
        picam2.close()
        raise error
 
    # Short sleep between readings
    time.sleep(3.0) 