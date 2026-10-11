from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, date
import uuid

from backend.database import get_db
from backend.models import DailyCheckInCreate, DailyCheckInOut
from backend.auth import get_current_user

router = APIRouter(prefix="/api/checkins", tags=["CheckIns"])

@router.post("", response_model=DailyCheckInOut)
async def create_daily_checkin(
    checkin_in: DailyCheckInCreate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    checkins_coll = db["daily_checkins"]
    
    today_str = checkin_in.date if checkin_in.date else date.today().isoformat()
    now_iso = datetime.utcnow().isoformat()
    
    # Check if entry for date exists
    existing = await checkins_coll.find_one({"user_id": current_user["id"], "date": today_str})
    
    if existing:
        doc_id = existing["_id"]
        update_data = {
            "focus_rating": checkin_in.focus_rating,
            "mood": checkin_in.mood,
            "sleep_hours": checkin_in.sleep_hours,
            "phone_habit_rating": checkin_in.phone_habit_rating,
            "notes": checkin_in.notes or "",
            "created_at": now_iso
        }
        await checkins_coll.update_one({"_id": doc_id}, {"$set": update_data})
        doc = {**existing, **update_data}
    else:
        doc_id = str(uuid.uuid4())
        doc = {
            "_id": doc_id,
            "user_id": current_user["id"],
            "date": today_str,
            "focus_rating": checkin_in.focus_rating,
            "mood": checkin_in.mood,
            "sleep_hours": checkin_in.sleep_hours,
            "phone_habit_rating": checkin_in.phone_habit_rating,
            "notes": checkin_in.notes or "",
            "created_at": now_iso
        }
        await checkins_coll.insert_one(doc)
        
    # Update achievement progress for daily checkins
    achievements_coll = db["achievements"]
    total_checkins = await checkins_coll.count_documents({"user_id": current_user["id"]})
    
    mindful_badge = await achievements_coll.find_one({
        "user_id": current_user["id"],
        "badge_id": "mindful_checker"
    })
    if mindful_badge:
        new_prog = min(total_checkins, 5)
        is_unlocked = new_prog >= 5
        await achievements_coll.update_one(
            {"_id": mindful_badge["_id"]},
            {"$set": {
                "progress": new_prog,
                "unlocked": is_unlocked,
                "unlocked_at": now_iso if is_unlocked and not mindful_badge.get("unlocked") else mindful_badge.get("unlocked_at")
            }}
        )
        
    return DailyCheckInOut(
        id=doc["_id"],
        user_id=doc["user_id"],
        date=doc["date"],
        focus_rating=doc["focus_rating"],
        mood=doc["mood"],
        sleep_hours=doc["sleep_hours"],
        phone_habit_rating=doc["phone_habit_rating"],
        notes=doc["notes"],
        created_at=doc["created_at"]
    )

@router.get("", response_model=List[DailyCheckInOut])
async def get_checkins(current_user: dict = Depends(get_current_user)):
    db = get_db()
    checkins_coll = db["daily_checkins"]
    
    items = await checkins_coll.find({"user_id": current_user["id"]}).to_list(length=500)
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return [
        DailyCheckInOut(
            id=item["_id"],
            user_id=item["user_id"],
            date=item["date"],
            focus_rating=item["focus_rating"],
            mood=item["mood"],
            sleep_hours=item["sleep_hours"],
            phone_habit_rating=item["phone_habit_rating"],
            notes=item.get("notes", ""),
            created_at=item.get("created_at", "")
        )
        for item in items
    ]

@router.get("/today", response_model=Optional[DailyCheckInOut])
async def get_today_checkin(current_user: dict = Depends(get_current_user)):
    db = get_db()
    checkins_coll = db["daily_checkins"]
    today_str = date.today().isoformat()
    
    doc = await checkins_coll.find_one({"user_id": current_user["id"], "date": today_str})
    if not doc:
        return None
        
    return DailyCheckInOut(
        id=doc["_id"],
        user_id=doc["user_id"],
        date=doc["date"],
        focus_rating=doc["focus_rating"],
        mood=doc["mood"],
        sleep_hours=doc["sleep_hours"],
        phone_habit_rating=doc["phone_habit_rating"],
        notes=doc.get("notes", ""),
        created_at=doc.get("created_at", "")
    )
