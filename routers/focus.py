from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, date, timedelta
import uuid

from backend.database import get_db
from backend.models import FocusSessionCreate, FocusSessionOut
from backend.auth import get_current_user

router = APIRouter(prefix="/api/focus", tags=["Focus"])

@router.post("", response_model=FocusSessionOut)
async def create_focus_session(
    session_in: FocusSessionCreate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    focus_coll = db["focus_sessions"]
    
    session_id = str(uuid.uuid4())
    today_str = session_in.date if session_in.date else date.today().isoformat()
    now_iso = datetime.utcnow().isoformat()
    
    doc = {
        "_id": session_id,
        "user_id": current_user["id"],
        "duration_minutes": session_in.duration_minutes,
        "session_type": session_in.session_type,
        "completed": session_in.completed,
        "notes": session_in.notes or "",
        "date": today_str,
        "created_at": now_iso
    }
    
    await focus_coll.insert_one(doc)
    
    # Check and update achievements if session completed
    if session_in.completed and session_in.session_type == "Focus":
        achievements_coll = db["achievements"]
        
        # Count focus sessions completed
        total_sessions = await focus_coll.count_documents({
            "user_id": current_user["id"],
            "session_type": "Focus",
            "completed": True
        })
        
        # Check first focus badge
        first_badge = await achievements_coll.find_one({
            "user_id": current_user["id"],
            "badge_id": "first_focus"
        })
        if first_badge and not first_badge.get("unlocked"):
            await achievements_coll.update_one(
                {"_id": first_badge["_id"]},
                {"$set": {"unlocked": True, "unlocked_at": now_iso, "progress": 1}}
            )
            
        # Check 10 focus sessions badge
        focus_10 = await achievements_coll.find_one({
            "user_id": current_user["id"],
            "badge_id": "focus_master"
        })
        if focus_10:
            new_prog = min(total_sessions, 10)
            is_unlocked = new_prog >= 10
            await achievements_coll.update_one(
                {"_id": focus_10["_id"]},
                {"$set": {
                    "progress": new_prog,
                    "unlocked": is_unlocked,
                    "unlocked_at": now_iso if is_unlocked and not focus_10.get("unlocked") else focus_10.get("unlocked_at")
                }}
            )
            
    return FocusSessionOut(
        id=doc["_id"],
        user_id=doc["user_id"],
        duration_minutes=doc["duration_minutes"],
        session_type=doc["session_type"],
        completed=doc["completed"],
        notes=doc["notes"],
        date=doc["date"],
        created_at=doc["created_at"]
    )

@router.get("", response_model=List[FocusSessionOut])
async def get_focus_sessions(current_user: dict = Depends(get_current_user)):
    db = get_db()
    focus_coll = db["focus_sessions"]
    
    items = await focus_coll.find({"user_id": current_user["id"]}).to_list(length=500)
    items.sort(key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
    
    return [
        FocusSessionOut(
            id=item["_id"],
            user_id=item["user_id"],
            duration_minutes=item["duration_minutes"],
            session_type=item["session_type"],
            completed=item["completed"],
            notes=item.get("notes", ""),
            date=item["date"],
            created_at=item.get("created_at", "")
        )
        for item in items
    ]

@router.get("/stats")
async def get_focus_stats(current_user: dict = Depends(get_current_user)):
    db = get_db()
    focus_coll = db["focus_sessions"]
    
    today_str = date.today().isoformat()
    items = await focus_coll.find({"user_id": current_user["id"]}).to_list(length=1000)
    
    today_sessions = [i for i in items if i.get("date") == today_str and i.get("completed") and i.get("session_type") == "Focus"]
    today_focus_minutes = sum(i.get("duration_minutes", 0) for i in today_sessions)
    today_focus_count = len(today_sessions)
    
    total_focus_minutes = sum(i.get("duration_minutes", 0) for i in items if i.get("completed") and i.get("session_type") == "Focus")
    total_focus_count = len([i for i in items if i.get("completed") and i.get("session_type") == "Focus"])
    
    return {
        "today_focus_minutes": today_focus_minutes,
        "today_focus_count": today_focus_count,
        "total_focus_minutes": total_focus_minutes,
        "total_focus_count": total_focus_count
    }
