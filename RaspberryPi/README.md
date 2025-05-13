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
- Log sensor data to CSV files in the "logs" directory

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
This script starts both the API server and the sensor monitoring simultaneously and keeps them running. It displays live logs from both processes in the terminal.

To start the complete system:
```
python3 start_system.py
```

## API Documentation

### Data Endpoints
- `GET /api/sensor` - Get latest sensor data (temperature and humidity)
- `GET /api/images/latest` - Get the latest captured image
- `GET /api/images/list` - List all available images
- `GET /api/images/{image_name}` - Get a specific image

### Control Endpoints
- `GET /api/control/status` - Check the current status of sensor and camera
- `POST /api/control` - Unified endpoint to control both sensor and camera (JSON body)

### Log Endpoints
- `GET /api/logs/list` - List all available log files
- `GET /api/logs/today` - Get today's sensor log file (CSV)
- `GET /api/logs/{log_name}` - Get a specific log file by name

### Example API Usage

#### Get sensor data:
```bash
curl http://raspberry-pi-ip:8000/api/sensor
```

#### Control both sensor and camera with a single request:
```bash
# Start both sensor and camera
curl -X POST http://raspberry-pi-ip:8000/api/control \
  -H "Content-Type: application/json" \
  -d '{"sensor": true, "camera": true}'

# Stop both sensor and camera
curl -X POST http://raspberry-pi-ip:8000/api/control \
  -H "Content-Type: application/json" \
  -d '{"sensor": false, "camera": false}'

# Only control sensor (leave camera unchanged)
curl -X POST http://raspberry-pi-ip:8000/api/control \
  -H "Content-Type: application/json" \
  -d '{"sensor": false}'
```

#### Stop Everything with curl:
```bash
# Stop both sensor and camera completely
curl -X POST http://localhost:8000/api/control \
  -H "Content-Type: application/json" \
  -d '{"sensor": false, "camera": false}'
```

#### JavaScript Examples for API Usage

```javascript
// Get sensor data
async function getSensorData() {
  try {
    const response = await fetch('http://raspberry-pi-ip:8000/api/sensor');
    const data = await response.json();
    console.log('Sensor Data:', data);
    return data;
  } catch (error) {
    console.error('Error getting sensor data:', error);
  }
}

// Control sensor and camera
async function controlSystem(sensorActive, cameraActive) {
  try {
    // Create control object - only include properties that need to be changed
    const controlData = {};
    if (sensorActive !== undefined) controlData.sensor = sensorActive;
    if (cameraActive !== undefined) controlData.camera = cameraActive;
    
    const response = await fetch('http://raspberry-pi-ip:8000/api/control', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(controlData)
    });
    
    const result = await response.json();
    console.log('Control result:', result);
    return result;
  } catch (error) {
    console.error('Error controlling system:', error);
  }
}

// Examples:
// Start both sensor and camera
controlSystem(true, true);

// Stop sensor only (leave camera unchanged)
controlSystem(false);

// Stop camera only (leave sensor unchanged)
controlSystem(undefined, false);

// Get the latest image URL
function getLatestImageUrl() {
  return 'http://raspberry-pi-ip:8000/api/images/latest';
}

// Display the latest image in an <img> element
function displayLatestImage() {
  document.getElementById('sensorImage').src = getLatestImageUrl() + '?t=' + new Date().getTime();
}

// Get today's log file
async function getTodayLog() {
  try {
    const response = await fetch('http://raspberry-pi-ip:8000/api/logs/today');
    const csvText = await response.text();
    console.log('Today\'s log:', csvText);
    // Process CSV data as needed
    return csvText;
  } catch (error) {
    console.error('Error getting log:', error);
  }
}
```

#### Download today's log file:
```bash
curl http://raspberry-pi-ip:8000/api/logs/today --output today_log.csv
```

## Data Storage

### Image Storage
The camera script saves images to an "images" directory with the naming format:
```
image_YYYYMMDD_HHMMSS.jpg
```

### Log Storage
Sensor data is logged to CSV files in the "logs" directory with the naming format:
```
sensor_log_YYYYMMDD.csv
```

Each log entry contains:
- Timestamp
- Temperature (Celsius and Fahrenheit)
- Humidity
- Sensor status (active/inactive)
- Camera status (active/inactive)

The script automatically creates the "images" and "logs" directories if they don't exist.

## Installation

### Basic Setup
```bash
python -m venv --system-site-packages venv
source venv/bin/activate
```

### Manual Package Installation
```bash
python3 -m pip install RPi.GPIO
python3 -m pip install adafruit-circuitpython-dht
python3 -m pip install fastapi uvicorn
```