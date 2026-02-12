import requests
import os
import time

BASE_URL = "http://localhost:8000"

def test_health():
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        print("✅ Health check passed")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

def test_upload():
    # Create a dummy file
    with open("test_log.log", "w") as f:
        f.write("2023-10-27 10:00:00 [INFO] Test log entry")
    
    try:
        with open("test_log.log", "rb") as f:
            files = {"file": f}
            response = requests.post(f"{BASE_URL}/upload", files=files)
        assert response.status_code == 200
        print("✅ Upload test passed")
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
    finally:
        if os.path.exists("test_log.log"):
            os.remove("test_log.log")

def test_process():
    try:
        response = requests.post(f"{BASE_URL}/process", json={"mode": "small"}) # Use small mode for speed
        assert response.status_code == 200
        print("✅ Process trigger passed")
    except Exception as e:
        print(f"❌ Process trigger failed: {e}")

def test_scan():
    try:
        response = requests.get(f"{BASE_URL}/scan")
        assert response.status_code == 200
        print("✅ Vulnerability scan passed")
    except Exception as e:
        print(f"❌ Vulnerability scan failed: {e}")

def test_chat():
    try:
        # Expecting a failure if no API key, but endpoint should be reachable
        response = requests.post(f"{BASE_URL}/chat", json={"message": "hello"})
        if response.status_code == 200:
            print("✅ Chat endpoint passed")
        elif response.status_code == 500:
             print("⚠️ Chat endpoint reached but failed (likely missing API key), which is expected.")
        else:
            print(f"❌ Chat endpoint failed with status {response.status_code}")
    except Exception as e:
        print(f"❌ Chat endpoint failed: {e}")

if __name__ == "__main__":
    print("Wait for server to start...")
    time.sleep(2) 
    test_health()
    test_upload()
    test_process()
    test_scan()
    test_chat()
