# AgroX-IoT Raspberry Pi Scripts

This directory contains scripts for the AgroX-IoT project that run on a Raspberry Pi.

## Available Scripts

### DHT22 Sensor (dht22.py)
This script reads temperature and humidity from a DHT22 sensor connected to GPIO 4.

To run:
```
python3 dht22.py
```

### DHT22 Sensor with Camera (dht22_with_camera.py)
This script combines DHT22 sensor reading with Raspberry Pi camera functionality to:
- Read temperature and humidity data
- Take pictures at regular intervals (1 minute)
- Store images in the "images" directory with timestamps

To run:
```
python3 dht22_with_camera.py
```

### API Server (api_server.py)
This script provides a web API to access sensor data and images. It can be run standalone or integrated with the sensor script.

To run the API server:
```
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### Start System (start_system.py)
This script starts both the API server and the sensor monitoring simultaneously, and keeps them running.

To start the complete system:
```
python3 start_system.py
```

## API Documentation
For detailed API documentation, see the [API-README.md](API-README.md) file.

## Requirements
- Raspberry Pi with Raspberry Pi OS
- DHT22 sensor connected to GPIO 4
- Raspberry Pi Camera Module connected
- Python packages: see requirements.txt

## Image Storage
The camera script saves images to an "images" directory with the naming format:
```
image_YYYYMMDD_HHMMSS.jpg
```

The script automatically creates the "images" directory if it doesn't exist. 

## Installation

### Basic Setup
```bash
python -m venv --system-site-packages env
source env/bin/activate
```

### Manual Package Installation
```bash
python3 -m pip install RPi.GPIO
python3 -m pip install adafruit-circuitpython-dht
python3 -m pip install fastapi uvicorn
```