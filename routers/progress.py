from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, date, timedelta
import uuid
import random

from backend.database import get_db
from backend.auth import get_current_user

router = APIRouter(prefix="/api/progress", tags=["Progress & Seed"])

@router.get("/dashboard")
async def get_dashboard_progress(current_user: dict = Depends(get_current_user)):
    db = get_db()
    screentime_coll = db["screentime"]
    focus_coll = db["focus_sessions"]
    checkins_coll = db["daily_checkins"]
    
    user_id = current_user["id"]
    today = date.today()
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()
    
    # Fetch all records
    st_items = await screentime_coll.find({"user_id": user_id}).to_list(length=2000)
    focus_items = await focus_coll.find({"user_id": user_id}).to_list(length=2000)
    checkin_items = await checkins_coll.find({"user_id": user_id}).to_list(length=1000)
    
    # Today screen time
    today_st_logs = [i for i in st_items if i.get("date") == today_str]
    today_st_minutes = sum(i.get("duration_minutes", 0) for i in today_st_logs)
    
    yesterday_st_logs = [i for i in st_items if i.get("date") == yesterday_str]
    yesterday_st_minutes = sum(i.get("duration_minutes", 0) for i in yesterday_st_logs)
    
    # Goal progress
    daily_goal_minutes = current_user["daily_goal_minutes"]
    goal_percent = min(round((today_st_minutes / daily_goal_minutes) * 100, 1), 100) if daily_goal_minutes > 0 else 0
    goal_remaining_minutes = max(0, daily_goal_minutes - today_st_minutes)
    
    # Focus sessions today
    today_focus_sessions = [f for f in focus_items if f.get("date") == today_str and f.get("completed") and f.get("session_type") == "Focus"]
    today_focus_count = len(today_focus_sessions)
    today_focus_minutes = sum(f.get("duration_minutes", 0) for f in today_focus_sessions)
    
    # Calculate streak
    active_dates = set()
    for f in focus_items:
        if f.get("completed") and f.get("session_type") == "Focus" and f.get("date"):
            active_dates.add(f["date"])
    for c in checkin_items:
        if c.get("date"):
            active_dates.add(c["date"])
            
    streak = 0
    check_d = today
    while check_d.isoformat() in active_dates or (check_d == today and len(active_dates) > 0):
        if check_d.isoformat() in active_dates:
            streak += 1
            check_d -= timedelta(days=1)
        elif check_d == today:
            check_d -= timedelta(days=1)
        else:
            break

    # Weekly chart (Last 7 days)
    weekly_chart = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.isoformat()
        day_st = sum(x.get("duration_minutes", 0) for x in st_items if x.get("date") == d_str)
        day_focus = sum(x.get("duration_minutes", 0) for x in focus_items if x.get("date") == d_str and x.get("completed") and x.get("session_type") == "Focus")
        weekly_chart.append({
            "date": d_str,
            "day": d.strftime("%a"),
            "screen_time": day_st,
            "focus_time": day_focus,
            "goal": daily_goal_minutes
        })
        
    # Monthly chart (Last 30 days summary by week/day)
    monthly_chart = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.isoformat()
        day_st = sum(x.get("duration_minutes", 0) for x in st_items if x.get("date") == d_str)
        day_focus = sum(x.get("duration_minutes", 0) for x in focus_items if x.get("date") == d_str and x.get("completed") and x.get("session_type") == "Focus")
        monthly_chart.append({
            "date": d_str,
            "day_label": d.strftime("%b %d"),
            "screen_time": day_st,
            "focus_time": day_focus,
            "met_goal": day_st <= daily_goal_minutes if day_st > 0 else True
        })
        
    # Category totals for today & overall
    today_category_totals = {}
    for item in today_st_logs:
        cat = item.get("category", "Other")
        today_category_totals[cat] = today_category_totals.get(cat, 0) + item.get("duration_minutes", 0)
        
    overall_category_totals = {}
    for item in st_items:
        cat = item.get("category", "Other")
        overall_category_totals[cat] = overall_category_totals.get(cat, 0) + item.get("duration_minutes", 0)
        
    return {
        "today_screentime_minutes": today_st_minutes,
        "yesterday_screentime_minutes": yesterday_st_minutes,
        "daily_goal_minutes": daily_goal_minutes,
        "goal_percent": goal_percent,
        "goal_remaining_minutes": goal_remaining_minutes,
        "today_focus_count": today_focus_count,
        "today_focus_minutes": today_focus_minutes,
        "current_streak": streak,
        "today_category_totals": today_category_totals,
        "overall_category_totals": overall_category_totals,
        "weekly_chart": weekly_chart,
        "monthly_chart": monthly_chart,
        "total_screentime_records": len(st_items),
        "total_focus_sessions": len([f for f in focus_items if f.get("completed")]),
        "total_checkins": len(checkin_items)
    }

@router.post("/seed")
async def seed_sample_data(current_user: dict = Depends(get_current_user)):
    db = get_db()
    screentime_coll = db["screentime"]
    focus_coll = db["focus_sessions"]
    checkins_coll = db["daily_checkins"]
    
    user_id = current_user["id"]
    today = date.today()
    
    apps_pool = [
        ("Instagram", "Social", 35, 60),
        ("YouTube", "Entertainment", 40, 90),
        ("WhatsApp", "Social", 20, 45),
        ("VS Code", "Productivity", 60, 120),
        ("Spotify", "Entertainment", 25, 50),
        ("Twitter / X", "Social", 20, 40),
        ("Gmail", "Productivity", 15, 30),
        ("PUBG Mobile", "Gaming", 30, 75),
        ("Duolingo", "Productivity", 15, 25),
        ("Chrome", "Utilities", 25, 50)
    ]
    
    moods = ["Productive", "Happy", "Calm", "Neutral", "Focused"]
    
    # Generate past 14 days of data
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.isoformat()
        
        # Check if screentime exists for this day
        existing_st = await screentime_coll.find_one({"user_id": user_id, "date": d_str})
        if not existing_st:
            # Add 3-5 random app usage entries
            selected_apps = random.sample(apps_pool, random.randint(3, 5))
            for app_name, cat, min_d, max_d in selected_apps:
                dur = random.randint(min_d, max_d)
                await screentime_coll.insert_one({
                    "_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "app_name": app_name,
                    "category": cat,
                    "duration_minutes": dur,
                    "date": d_str,
                    "created_at": datetime.utcnow().isoformat()
                })
                
        # Focus sessions for day
        existing_focus = await focus_coll.find_one({"user_id": user_id, "date": d_str})
        if not existing_focus and i % 2 == 0:
            for _ in range(random.randint(1, 3)):
                await focus_coll.insert_one({
                    "_id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "duration_minutes": 25,
                    "session_type": "Focus",
                    "completed": True,
                    "notes": "Deep work session",
                    "date": d_str,
                    "created_at": datetime.utcnow().isoformat()
                })
                
        # Check-in for day
        existing_checkin = await checkins_coll.find_one({"user_id": user_id, "date": d_str})
        if not existing_checkin and i % 2 == 0:
            await checkins_coll.insert_one({
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "date": d_str,
                "focus_rating": random.randint(3, 5),
                "mood": random.choice(moods),
                "sleep_hours": round(random.uniform(6.5, 8.5), 1),
                "phone_habit_rating": random.randint(3, 5),
                "notes": "Good productive day, managed screen time well.",
                "created_at": datetime.utcnow().isoformat()
            })
            
    return {"message": "Sample data seeded successfully for 14 days!"}
