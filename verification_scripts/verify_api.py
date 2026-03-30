import requests
import time
import subprocess
import sys
import os

def run_tests():
    print("🚀 Starting API Verification...")
    
    # 1. Start Server
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api:app", "--port", "8001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(10)
    
    BASE_URL = "http://127.0.0.1:8001"
    
    try:
        # 2. Check Health
        print("\nTesting / (Health Check)...")
        try:
            resp = requests.get(f"{BASE_URL}/")
            if resp.status_code == 200:
                print("✅ Health check passed")
            else:
                print(f"❌ Health check failed: {resp.status_code}")
        except Exception as e:
             print(f"❌ Connection failed: {e}")
             return

        # 3. Test Multi-file Upload
        print("\nTesting /upload (Multi-file)...")
        dummy_log1 = "test_log1.txt"
        dummy_log2 = "test_log2.txt"
        with open(dummy_log1, "w") as f: f.write("2023-10-27 10:00:00 ERROR Connection failed\n")
        with open(dummy_log2, "w") as f: f.write("2023-10-27 10:05:00 INFO User logged in\n")
            
        files = [
            ('files', (dummy_log1, open(dummy_log1, "rb"))),
            ('files', (dummy_log2, open(dummy_log2, "rb")))
        ]
        resp = requests.post(f"{BASE_URL}/upload", files=files)
            
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Upload passed. Uploaded {len(data.get('uploads', []))} files.")
        else:
            print(f"❌ Upload failed: {resp.text}")
            
        os.remove(dummy_log1)
        os.remove(dummy_log2)

        # 4. Test List Files
        print("\nTesting /files...")
        resp = requests.get(f"{BASE_URL}/files")
        if resp.status_code == 200:
            print(f"✅ List files passed. Found {len(resp.json()['files'])} files.")
        else:
            print(f"❌ List files failed: {resp.text}")

        # 5. Test Scan
        print("\nTesting /scan...")
        resp = requests.post(f"{BASE_URL}/scan")
        if resp.status_code == 200:
            print(f"✅ Scan passed: {resp.json()['message']}")
        else:
            print(f"❌ Scan failed: {resp.text}")

        # 6. Test Chat (Optional - depends on API Key)
        # print("\nTesting /chat (Mock)...")
        # resp = requests.post(f"{BASE_URL}/chat", json={"message": "Hello"})
        # print(f"Chat Response: {resp.json()}")

    finally:
        print("\n🛑 Stopping Server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    run_tests()
