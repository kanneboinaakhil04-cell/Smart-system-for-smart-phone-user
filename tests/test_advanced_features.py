import pytest
from fastapi.testclient import TestClient
import uuid

from backend.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    unique_email = f"adv_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "full_name": "Adv User",
        "daily_goal_minutes": 180
    })
    assert reg_res.status_code == 200
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_study_rooms():
    res = client.get("/api/realtime/rooms")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 4
    assert any(r["id"] == "silent-library" for r in data)

def test_predictive_ai_analysis(auth_headers):
    res = client.get("/api/ai/predictive-analysis", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "doomscroll_risk_score" in data
    assert "vulnerability_window" in data
    assert "correlations" in data

def test_accountability_partner_and_unlock(auth_headers):
    # Save partner
    res = client.post("/api/accountability/partner", headers=auth_headers, json={
        "partner_name": "Mentor Sarah",
        "partner_email": "sarah@example.com",
        "phone_number": "+1234567890",
        "notify_on_limit_exceeded": True,
        "hard_lock_mode": True
    })
    assert res.status_code == 200
    assert res.json()["partner_name"] == "Mentor Sarah"

    # Fetch partner
    get_res = client.get("/api/accountability/partner", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["partner_email"] == "sarah@example.com"

    # Emergency unlock
    unlock_res = client.post("/api/accountability/emergency-unlock", headers=auth_headers, json={
        "app_name": "Instagram",
        "unlock_duration_minutes": 15,
        "reflection_note": "Need to urgently coordinate project details with client on Instagram direct message."
    })
    assert unlock_res.status_code == 200
    assert unlock_res.json()["status"] == "success"

def test_friction_rules(auth_headers):
    res = client.get("/api/accountability/friction-rules", headers=auth_headers)
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 4

def test_telemetry_heartbeat(auth_headers):
    res = client.post("/api/screentime/agent-heartbeat", headers=auth_headers, json={
        "app_name": "VS Code",
        "window_title": "Dashboard.jsx - PhoneBalance",
        "duration_seconds": 60,
        "category": "Productivity",
        "source": "desktop_agent"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "recorded"

def test_executive_report(auth_headers):
    res = client.get("/api/export/report", headers=auth_headers)
    assert res.status_code == 200
    assert "PhoneBalance Executive Digital Wellbeing Report" in res.text
