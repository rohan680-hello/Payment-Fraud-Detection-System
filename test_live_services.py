import json
import subprocess
import sys
import time
import requests

def run_live_test():
    print("--- Starting live server integration test ---")
    
    # Start FastAPI backend via uvicorn
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "app:app",
        "--host", "127.0.0.1",
        "--port", "8008"
    ]
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        # Wait for backend to be ready
        url = "http://127.0.0.1:8008"
        ready = False
        for attempt in range(15):
            try:
                r = requests.get(f"{url}/health", timeout=2)
                if r.status_code == 200:
                    ready = True
                    print(f"[PASS] FastAPI live server is UP on {url}:", r.json())
                    break
            except Exception:
                time.sleep(1)
        
        if not ready:
            stdout, stderr = proc.communicate(timeout=3)
            raise RuntimeError(f"Server failed to start:\nstdout: {stdout}\nstderr: {stderr}")
        
        # Test /predict live
        with open("sample_request.json", "r", encoding="utf-8") as f:
            sample_payload = json.load(f)
            
        r_pred = requests.post(f"{url}/predict", json=sample_payload, timeout=5)
        assert r_pred.status_code == 200, f"Expected 200, got {r_pred.status_code}: {r_pred.text}"
        pred_data = r_pred.json()
        print(f"[PASS] Live /predict endpoint returned:", pred_data)
        
        # Test invalid input rejected with 422
        bad_payload = {"features": {"Time": 0.0}}
        r_bad = requests.post(f"{url}/predict", json=bad_payload, timeout=5)
        assert r_bad.status_code == 422
        print(f"[PASS] Live /predict rejected incomplete payload with 422 as expected")
        
        print("\nAll live HTTP integration tests PASSED!")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Server process stopped cleanly.")

if __name__ == "__main__":
    run_live_test()
