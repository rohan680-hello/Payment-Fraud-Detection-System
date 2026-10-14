import json
from pathlib import Path
from fastapi.testclient import TestClient

from app import app, threshold, artifact

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model"] == artifact["model_name"]
    print("[PASS] /health:", data)

def test_predict_with_sample_request():
    sample_path = Path("sample_request.json")
    assert sample_path.exists(), "sample_request.json must exist"
    
    with open(sample_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "risk_score" in data
    assert "flagged_for_review" in data
    assert "threshold" in data
    assert "model" in data
    assert isinstance(data["risk_score"], float)
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["threshold"] == threshold
    assert data["flagged_for_review"] == (data["risk_score"] >= threshold)
    print("[PASS] /predict with sample_request.json:", data)

def test_predict_missing_features():
    invalid_payload = {
        "features": {
            "Time": 100.0,
            "Amount": 50.0
            # Missing V1-V28
        }
    }
    response = client.post("/predict", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "missing_features" in data["detail"]
    assert len(data["detail"]["missing_features"]) == 28
    print("[PASS] /predict missing features rejected (HTTP 422):", data)

def test_predict_invalid_value():
    with open("sample_request.json", "r", encoding="utf-8") as f:
        payload = json.load(f)
    
    # Introduce non-numeric value
    payload["features"]["V1"] = "invalid_string_value"
    response = client.post("/predict", json=payload)
    assert response.status_code == 422
    print("[PASS] /predict non-numeric value rejected (HTTP 422)")

def test_dashboard_helpers():
    sample_path = Path("sample_request.json")
    assert sample_path.exists()
    with open(sample_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "features" in data
    assert len(data["features"]) == 30
    print("[PASS] Dashboard data helper verified successfully")

if __name__ == "__main__":
    print("\n--- Running Payment Fraud Detection Automated Tests ---\n")
    test_health_endpoint()
    test_predict_with_sample_request()
    test_predict_missing_features()
    test_predict_invalid_value()
    test_dashboard_helpers()
    print("\nAll automated tests passed successfully!\n")
