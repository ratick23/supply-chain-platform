import pytest
import requests

BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_unknown_shipment_404():
    resp = requests.get(f"{BASE_URL}/shipments/UNKNOWN_ID_9999", timeout=5)
    assert resp.status_code == 404
    assert "detail" in resp.json()

def test_predict_delay_endpoint():
    payload = {
        "shipment_id": "SHP-TEST-01",
        "origin_port": "CNSHA",
        "destination_port": "NLRTM",
        "cargo_type": "DRY",
        "weight_tons": 22.5,
        "container_count": 4
    }
    resp = requests.post(f"{BASE_URL}/predict-delay", json=payload, timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["shipment_id"] == "SHP-TEST-01"
    assert "predicted_delayed" in data
    assert 0.0 <= data["delay_risk_score"] <= 1.0

def test_data_quality_report_endpoint():
    resp = requests.get(f"{BASE_URL}/data-quality/report", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert "report_file" in data
    assert "issues" in data