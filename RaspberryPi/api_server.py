from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import glob
from typing import Dict, List, Optional
import time
import threading
import json
from pydantic import BaseModel

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
latest_sensor_data = {
    "temperature_c": None,
    "temperature_f": None,
    "humidity": None,
    "timestamp": None
}

# Model for sensor data response
class SensorData(BaseModel):
    temperature_c: float
    temperature_f: float
    humidity: float
    timestamp: float

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

# This function will be imported by dht22_with_camera.py
def update_sensor_data(temp_c: float, temp_f: float, humidity: float):
    global latest_sensor_data
    latest_sensor_data = {
        "temperature_c": temp_c,
        "temperature_f": temp_f,
        "humidity": humidity,
        "timestamp": time.time()
    }

# To start the server, run: uvicorn api_server:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 