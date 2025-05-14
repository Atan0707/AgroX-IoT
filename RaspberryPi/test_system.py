"""
Test script to verify the sensor/camera system is working correctly.
This script communicates directly with the API server to control the system.
"""

import requests
import time
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_DURATION = 60  # How long to run each test (seconds)

def test_system():
    print("\n=== SYSTEM TEST SCRIPT ===")
    
    # 1. Check if API server is running
    print("\n1. Checking if API server is running...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/control/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ API server is running")
            print(f"   Current status: Sensor={(status['sensor_active'])}, Camera={status['camera_active']}")
        else:
            print(f"❌ API server returned unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Failed to connect to API server at {API_BASE_URL}")
        print(f"   Is the server running? Try starting it with: python start_system.py")
        return False
    
    # 2. Turn everything off first
    print("\n2. Turning all systems OFF...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/control/off")
        if response.status_code == 200:
            print(f"✅ Successfully turned all systems OFF")
        else:
            print(f"❌ Failed to turn systems off: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error")
        return False
    
    # Wait a moment to ensure changes take effect
    time.sleep(5)
    
    # 3. Check status again to confirm OFF
    print("\n3. Verifying systems are OFF...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/control/status")
        status = response.json()
        if not status['sensor_active'] and not status['camera_active']:
            print(f"✅ Confirmed both systems are OFF")
        else:
            print(f"❌ Systems did not turn OFF properly: {status}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error")
        return False
    
    # 4. Turn everything ON
    print("\n4. Turning all systems ON...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/control/on")
        if response.status_code == 200:
            print(f"✅ Successfully turned all systems ON")
        else:
            print(f"❌ Failed to turn systems on: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error")
        return False
    
    # Wait a moment to ensure changes take effect
    time.sleep(5)
    
    # 5. Check status to confirm ON
    print("\n5. Verifying systems are ON...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/control/status")
        status = response.json()
        if status['sensor_active'] and status['camera_active']:
            print(f"✅ Confirmed both systems are ON")
        else:
            print(f"❌ Systems did not turn ON properly: {status}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error")
        return False
    
    # 6. Check if sensor data is being collected
    print(f"\n6. Waiting {TEST_DURATION} seconds for sensor data...")
    start_time = time.time()
    sensor_data_received = False
    
    while time.time() - start_time < TEST_DURATION:
        try:
            response = requests.get(f"{API_BASE_URL}/api/sensor")
            if response.status_code == 200:
                data = response.json()
                print(f"   Received sensor data: Temp={data['temperature_c']:.1f}°C, Humidity={data['humidity']:.1f}%")
                sensor_data_received = True
                # Break early if we have data
                break
            else:
                print(f"   No sensor data yet, waiting... ({int(time.time() - start_time)} seconds elapsed)")
        except requests.exceptions.ConnectionError:
            print(f"   Connection error, retrying...")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        time.sleep(5)
    
    if sensor_data_received:
        print(f"✅ Successfully received sensor data")
    else:
        print(f"❌ Failed to receive any sensor data within {TEST_DURATION} seconds")
    
    # 7. Turn everything OFF again
    print("\n7. Turning all systems OFF again...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/control/off")
        if response.status_code == 200:
            print(f"✅ Successfully turned all systems OFF")
        else:
            print(f"❌ Failed to turn systems off: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error")
    
    # 8. Final status check
    print("\n8. Final status check...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/control/status")
        status = response.json()
        print(f"   Final system status: Sensor={(status['sensor_active'])}, Camera={status['camera_active']}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error")
    
    print("\n=== TEST COMPLETE ===")
    return True

if __name__ == "__main__":
    test_system() 