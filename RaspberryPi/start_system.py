import subprocess
import sys
import time
import os
import threading

def log_output(process, prefix):
    """Read and print output from the process with a prefix."""
    for line in iter(process.stdout.readline, ''):
        if line:
            print(f"{prefix}: {line.strip()}")
    
    for line in iter(process.stderr.readline, ''):
        if line:
            print(f"{prefix} ERROR: {line.strip()}")

def start_api_server():
    """Start the FastAPI server as a subprocess."""
    print("Starting API server...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        cwd=os.path.dirname(os.path.abspath(__file__))  # Run from the current script's directory
    )
    
    # Start logging thread for this process
    api_log_thread = threading.Thread(target=log_output, args=(api_process, "API"), daemon=True)
    api_log_thread.start()
    
    return api_process

def start_sensor_monitoring():
    """Start the DHT22 with camera monitoring as a subprocess."""
    print("Starting sensor monitoring...")
    sensor_process = subprocess.Popen(
        [sys.executable, "dht22_with_camera.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        cwd=os.path.dirname(os.path.abspath(__file__))  # Run from the current script's directory
    )
    
    # Start logging thread for this process
    sensor_log_thread = threading.Thread(target=log_output, args=(sensor_process, "SENSOR"), daemon=True)
    sensor_log_thread.start()
    
    return sensor_process

def main():
    """Main function to start and monitor both processes."""
    print("\n===== Starting AgroX-IoT system =====\n")
    
    # Start API server
    api_process = start_api_server()
    print(f"API server started with PID: {api_process.pid}")
    
    # Wait a moment to ensure the API server is up
    time.sleep(2)
    
    # Start sensor monitoring
    sensor_process = start_sensor_monitoring()
    print(f"Sensor monitoring started with PID: {sensor_process.pid}")
    
    print("\n===== System is now running! =====")
    print("- API is available at http://localhost:8000")
    print("- Endpoints:")
    print("  DATA ENDPOINTS:")
    print("  - GET /api/sensor - Get latest sensor data")
    print("  - GET /api/images/latest - Get the latest captured image")
    print("  - GET /api/images/list - List all available images")
    print("  - GET /api/images/{image_name} - Get a specific image")
    print("\n  CONTROL ENDPOINTS:")
    print("  - GET /api/control/status - Check sensor and camera status")
    print("  - POST /api/control - Unified endpoint to control both sensor and camera")
    print("    Example: {'sensor': true, 'camera': false}")
    print("  - POST /api/control/sensor/start - Start sensor data collection")
    print("  - POST /api/control/sensor/stop - Stop sensor data collection")
    print("  - POST /api/control/camera/start - Start camera capture")
    print("  - POST /api/control/camera/stop - Stop camera capture")
    print("\n  LOG ENDPOINTS:")
    print("  - GET /api/logs/list - List all available log files")
    print("  - GET /api/logs/today - Get today's sensor log file (CSV)")
    print("  - GET /api/logs/{log_name} - Get a specific log file by name")
    print("\n===== Live logs displayed below =====\n")
    
    try:
        # Keep the script running and monitor the subprocesses
        while True:
            # Check if processes are still running
            if api_process.poll() is not None:
                print("API server has stopped. Restarting...")
                api_process = start_api_server()
                print(f"API server restarted with PID: {api_process.pid}")
            
            if sensor_process.poll() is not None:
                print("Sensor monitoring has stopped. Restarting...")
                sensor_process = start_sensor_monitoring()
                print(f"Sensor monitoring restarted with PID: {sensor_process.pid}")
            
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        print("\n\n===== Shutting down... =====")
        api_process.terminate()
        sensor_process.terminate()
        api_process.wait()
        sensor_process.wait()
        print("System shutdown complete.")

if __name__ == "__main__":
    main() 