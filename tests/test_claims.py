"""Tests for the Week 2 claims-intake agent (mock backend — hermetic, no Azure)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_mock_backend():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["backend"] == "mock"


def test_active_policy_creates_case():
    r = client.post(
        "/api/v1/claims/intake",
        json={
            "claim_text": "Car accident on 2026-06-03, policy POL-12345, "
            "front bumper damaged, approx $1,200."
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "mock"
    assert body["extracted"]["policy_number"] == "POL-12345"
    assert body["extracted"]["claim_type"] == "auto"
    assert body["extracted"]["incident_date"] == "2026-06-03"
    assert body["extracted"]["estimated_amount"] == 1200.0
    assert body["policy"]["valid"] is True
    assert "collision" in body["policy"]["coverage"]
    assert body["decision"] == "created"
    assert body["case_id"].startswith("CASE-")


def test_lapsed_policy_is_rejected():
    r = client.post(
        "/api/v1/claims/intake",
        json={"claim_text": "Water damage to my home, policy POL-00001."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["policy"]["status"] == "lapsed"
    assert body["decision"] == "rejected"


def test_missing_policy_needs_review():
    r = client.post(
        "/api/v1/claims/intake",
        json={"claim_text": "I had an accident but I can't find my policy number."},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "needs_review"


def test_unknown_policy_needs_review():
    r = client.post(
        "/api/v1/claims/intake",
        json={"claim_text": "Filing a claim under policy POL-99999 for a fender bender."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["policy"]["status"] == "not_found"
    assert body["decision"] == "needs_review"


def test_policy_number_field_overrides_extraction():
    r = client.post(
        "/api/v1/claims/intake",
        json={"claim_text": "Front bumper damage from a parking lot bump.", "policy_number": "POL-12345"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "created"


def test_empty_claim_is_rejected():
    r = client.post("/api/v1/claims/intake", json={"claim_text": ""})
    assert r.status_code == 422
