import subprocess
import sys
import time
import requests

def test_streamlit_dashboard():
    print("--- Starting Streamlit Dashboard live test ---")
    cmd = [
        sys.executable,
        "-m", "streamlit",
        "run", "dashboard.py",
        "--server.headless", "true",
        "--server.port", "8502"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        url = "http://127.0.0.1:8502/_stcore/health"
        ready = False
        for attempt in range(15):
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    ready = True
                    print(f"[PASS] Streamlit Dashboard server is UP on port 8502 (Health response: {r.text})")
                    break
            except Exception:
                time.sleep(1)
        
        if not ready:
            stdout, stderr = proc.communicate(timeout=3)
            raise RuntimeError(f"Streamlit failed to start:\nstdout: {stdout}\nstderr: {stderr}")
            
        print("[PASS] Streamlit dashboard successfully initialized and served without errors!")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Streamlit dashboard process stopped cleanly.")

if __name__ == "__main__":
    test_streamlit_dashboard()
