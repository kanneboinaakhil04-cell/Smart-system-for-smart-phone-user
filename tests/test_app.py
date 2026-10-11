import pytest
from fastapi.testclient import TestClient
import uuid

from backend.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "full_name": "Pytest User",
        "daily_goal_minutes": 180
    })
    assert reg_res.status_code == 200
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "PhoneBalance API"

def test_auth_flow():
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "email": email,
        "password": "TestPassword123",
        "full_name": "Test Runner"
    })
    assert reg.status_code == 200
    assert "access_token" in reg.json()

    login = client.post("/api/auth/login", json={
        "email": email,
        "password": "TestPassword123"
    })
    assert login.status_code == 200
    assert "access_token" in login.json()

from datetime import date

def test_screentime_flow(auth_headers):
    # Add screentime log
    today_str = date.today().isoformat()
    res = client.post("/api/screentime", headers=auth_headers, json={
        "app_name": "YouTube",
        "category": "Entertainment",
        "duration_minutes": 40,
        "date": today_str
    })
    assert res.status_code == 200
    assert res.json()["app_name"] == "YouTube"

    # Get Summary
    summary = client.get("/api/screentime/summary", headers=auth_headers)
    assert summary.status_code == 200
    assert summary.json()["today_total_minutes"] >= 40


def test_focus_session_flow(auth_headers):
    res = client.post("/api/focus", headers=auth_headers, json={
        "duration_minutes": 25,
        "session_type": "Focus",
        "completed": True,
        "notes": "Pytest Focus Block"
    })
    assert res.status_code == 200
    assert res.json()["completed"] is True

def test_daily_checkin(auth_headers):
    res = client.post("/api/checkins", headers=auth_headers, json={
        "focus_rating": 4,
        "mood": "Productive",
        "sleep_hours": 7.5,
        "phone_habit_rating": 4,
        "notes": "Great focus day"
    })
    assert res.status_code == 200
    assert res.json()["mood"] == "Productive"

def test_ai_insights(auth_headers):
    res = client.get("/api/ai/insights", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "health_score" in data
    assert "insights" in data

def test_ai_chat(auth_headers):
    res = client.post("/api/ai/chat", headers=auth_headers, json={
        "message": "How to reduce social media use before sleep?"
    })
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data

def test_export_csv(auth_headers):
    res = client.get("/api/export/csv?type=screentime", headers=auth_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]

def test_export_json(auth_headers):
    res = client.get("/api/export/json", headers=auth_headers)
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
