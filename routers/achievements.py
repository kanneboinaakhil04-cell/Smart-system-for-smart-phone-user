from fastapi import APIRouter, Depends
from typing import List
from datetime import datetime, date, timedelta

from backend.database import get_db
from backend.models import AchievementOut
from backend.auth import get_current_user

router = APIRouter(prefix="/api/achievements", tags=["Achievements"])

@router.get("", response_model=List[AchievementOut])
async def get_achievements(current_user: dict = Depends(get_current_user)):
    db = get_db()
    achievements_coll = db["achievements"]
    screentime_coll = db["screentime"]
    focus_coll = db["focus_sessions"]
    checkins_coll = db["daily_checkins"]
    
    user_id = current_user["id"]
    now_iso = datetime.utcnow().isoformat()
    
    # Recalculate streak & metrics
    focus_sessions = await focus_coll.find({"user_id": user_id, "completed": True, "session_type": "Focus"}).to_list(length=1000)
    checkins = await checkins_coll.find({"user_id": user_id}).to_list(length=1000)
    st_items = await screentime_coll.find({"user_id": user_id}).to_list(length=1000)
    
    # Calculate streak (consecutive days with either focus session or check-in or low screen time)
    active_dates = set()
    for f in focus_sessions:
        if f.get("date"):
            active_dates.add(f["date"])
    for c in checkins:
        if c.get("date"):
            active_dates.add(c["date"])
            
    today = date.today()
    streak = 0
    check_d = today
    while check_d.isoformat() in active_dates or (check_d == today and len(active_dates) > 0):
        if check_d.isoformat() in active_dates:
            streak += 1
            check_d -= timedelta(days=1)
        elif check_d == today:
            # If haven't logged today yet, check yesterday
            check_d -= timedelta(days=1)
        else:
            break
            
    # Calculate goal crusher count (days where total screen time <= daily_goal_minutes)
    days_st = {}
    for st in st_items:
        d = st.get("date")
        if d:
            days_st[d] = days_st.get(d, 0) + st.get("duration_minutes", 0)
            
    goal_met_count = sum(1 for d, mins in days_st.items() if mins <= current_user["daily_goal_minutes"])
    
    # Fetch badges
    user_achievements = await achievements_coll.find({"user_id": user_id}).to_list(length=100)
    
    # Update badges in database dynamically
    result = []
    for ach in user_achievements:
        badge_id = ach.get("badge_id")
        unlocked = ach.get("unlocked", False)
        progress = ach.get("progress", 0)
        target = ach.get("target", 1)
        
        if badge_id == "first_focus":
            progress = min(len(focus_sessions), 1)
            unlocked = progress >= 1
        elif badge_id == "focus_master":
            progress = min(len(focus_sessions), 10)
            unlocked = progress >= 10
        elif badge_id == "streak_3":
            progress = min(streak, 3)
            unlocked = streak >= 3
        elif badge_id == "streak_7":
            progress = min(streak, 7)
            unlocked = streak >= 7
        elif badge_id == "goal_crusher":
            progress = min(goal_met_count, 5)
            unlocked = goal_met_count >= 5
        elif badge_id == "mindful_checker":
            progress = min(len(checkins), 5)
            unlocked = progress >= 5
            
        unlocked_at = ach.get("unlocked_at")
        if unlocked and not unlocked_at:
            unlocked_at = now_iso
            
        # Update db if changed
        if progress != ach.get("progress") or unlocked != ach.get("unlocked"):
            await achievements_coll.update_one(
                {"_id": ach["_id"]},
                {"$set": {"progress": progress, "unlocked": unlocked, "unlocked_at": unlocked_at}}
            )
            
        result.append(AchievementOut(
            id=ach["_id"],
            badge_id=badge_id,
            title=ach.get("title", ""),
            description=ach.get("description", ""),
            icon=ach.get("icon", "Award"),
            category=ach.get("category", "General"),
            unlocked=unlocked,
            unlocked_at=unlocked_at,
            progress=progress,
            target=target
        ))
        
    return result
