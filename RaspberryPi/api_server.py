from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import glob
from typing import Dict, List, Optional
import time
import threading
import json
from pydantic import BaseModel
from datetime import datetime

# Create a FastAPI instance
app = FastAPI(title="RaspberryPi Sensor API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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
sensor_active = True
camera_active = True

# Model for sensor data response
class SensorData(BaseModel):
    temperature_c: float
    temperature_f: float
    humidity: float
    timestamp: float

# Model for status response
class StatusResponse(BaseModel):
    sensor_active: bool
    camera_active: bool
    message: str

# Model for system control
class SystemControl(BaseModel):
    sensor: Optional[bool] = None
    camera: Optional[bool] = None

# Routes
@app.get("/")
async def root():
    return {"message": "RaspberryPi Sensor API is running"}

@app.get("/api/sensor", response_model=SensorData)
async def get_sensor_data():
    if latest_sensor_data["timestamp"] is None:
        raise HTTPException(status_code=503, detail="Sensor data not yet available")
    return latest_sensor_data

@app.get("/api/images/latest")
async def get_latest_image():
    try:
        # Get the latest image
        images = sorted(glob.glob(f"{IMAGE_DIR}/*.jpg"))
        if not images:
            raise HTTPException(status_code=404, detail="No images found")
        latest_image = images[-1]
        return FileResponse(latest_image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/images/list")
async def list_images():
    try:
        images = sorted(glob.glob(f"{IMAGE_DIR}/*.jpg"))
        # Return just the filenames, not full paths
        return {"images": [os.path.basename(img) for img in images]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/images/{image_name}")
async def get_image(image_name: str):
    image_path = os.path.join(IMAGE_DIR, image_name)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)

# Log endpoints
@app.get("/api/logs/list")
async def list_logs():
    try:
        if not os.path.exists(LOG_DIR):
            return {"logs": []}
        
        logs = sorted(glob.glob(f"{LOG_DIR}/*.csv"))
        return {"logs": [os.path.basename(log) for log in logs]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/{log_name}")
async def get_log(log_name: str):
    log_path = os.path.join(LOG_DIR, log_name)
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Log file not found")
    return FileResponse(log_path, media_type="text/csv")

@app.get("/api/logs/today")
async def get_today_log():
    try:
        today = datetime.now().strftime("%Y%m%d")
        log_name = f"sensor_log_{today}.csv"
        log_path = os.path.join(LOG_DIR, log_name)
        
        if not os.path.exists(log_path):
            raise HTTPException(status_code=404, detail="Today's log file not found")
            
        return FileResponse(log_path, media_type="text/csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Control endpoints
@app.get("/api/control/status", response_model=StatusResponse)
async def get_status():
    return StatusResponse(
        sensor_active=sensor_active,
        camera_active=camera_active,
        message="Current system status"
    )

# Unified control endpoint
@app.post("/api/control", response_model=StatusResponse)
async def control_system(control: SystemControl):
    global sensor_active, camera_active
    
    # Track what was changed for the response message
    changes = []
    
    # Update sensor status if provided
    if control.sensor is not None:
        sensor_active = control.sensor
        status = "started" if control.sensor else "stopped"
        changes.append(f"Sensor data collection {status}")
    
    # Update camera status if provided
    if control.camera is not None:
        camera_active = control.camera
        status = "started" if control.camera else "stopped"
        changes.append(f"Camera capture {status}")
    
    # If nothing was changed, inform the user
    if not changes:
        message = "No changes made. Specify 'sensor' and/or 'camera' with boolean values."
    else:
        message = ". ".join(changes)
    
    return StatusResponse(
        sensor_active=sensor_active,
        camera_active=camera_active,
        message=message
    )

# This function will be imported by dht22_with_camera.py
def update_sensor_data(temp_c: float, temp_f: float, humidity: float):
    global latest_sensor_data
    # The sensor_active check is now handled in dht22_with_camera.py
    latest_sensor_data = {
        "temperature_c": temp_c,
        "temperature_f": temp_f,
        "humidity": humidity,
        "timestamp": time.time()
    }

# Function to check if camera is active
def is_camera_active():
    return camera_active

# To start the server, run: uvicorn api_server:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 