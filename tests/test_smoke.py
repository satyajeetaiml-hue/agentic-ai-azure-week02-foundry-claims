"""Smoke tests for Week 2 — Microsoft Foundry & Foundry Agent Service."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_endpoint_accepts_input():
    r = client.post("/api/v1/claims/intake", json={"claim_text": "I had a minor car accident on June 3rd, policy POL-12345, front bumper damaged."})
    assert r.status_code == 200


def test_endpoint_rejects_empty():
    r = client.post("/api/v1/claims/intake", json={"claim_text": ""})
    assert r.status_code == 422
