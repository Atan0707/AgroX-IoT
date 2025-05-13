import subprocess
import sys
import time
import os

def start_api_server():
    """Start the FastAPI server as a subprocess."""
    print("Starting API server...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))  # Run from the current script's directory
    )
    return api_process

def start_sensor_monitoring():
    """Start the DHT22 with camera monitoring as a subprocess."""
    print("Starting sensor monitoring...")
    sensor_process = subprocess.Popen(
        [sys.executable, "dht22_with_camera.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))  # Run from the current script's directory
    )
    return sensor_process

def main():
    """Main function to start and monitor both processes."""
    print("Starting AgroX-IoT system...")
    
    # Start API server
    api_process = start_api_server()
    print("API server started with PID:", api_process.pid)
    
    # Wait a moment to ensure the API server is up
    time.sleep(2)
    
    # Start sensor monitoring
    sensor_process = start_sensor_monitoring()
    print("Sensor monitoring started with PID:", sensor_process.pid)
    
    print("\nSystem is now running!")
    print("- API is available at http://localhost:8000")
    print("- Endpoints:")
    print("  - GET /api/sensor - Get latest sensor data")
    print("  - GET /api/images/latest - Get the latest captured image")
    print("  - GET /api/images/list - List all available images")
    print("  - GET /api/images/{image_name} - Get a specific image\n")
    
    try:
        # Keep the script running and monitor the subprocesses
        while True:
            # Check if processes are still running
            if api_process.poll() is not None:
                print("API server has stopped. Restarting...")
                api_process = start_api_server()
                print("API server restarted with PID:", api_process.pid)
            
            if sensor_process.poll() is not None:
                print("Sensor monitoring has stopped. Restarting...")
                sensor_process = start_sensor_monitoring()
                print("Sensor monitoring restarted with PID:", sensor_process.pid)
            
            time.sleep(10)  # Check every 10 seconds
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        api_process.terminate()
        sensor_process.terminate()
        api_process.wait()
        sensor_process.wait()
        print("System shutdown complete.")

if __name__ == "__main__":
    main() 