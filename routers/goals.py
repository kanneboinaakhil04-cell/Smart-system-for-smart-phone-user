from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
import uuid

from backend.database import get_db
from backend.models import GoalUpdate, ReminderCreate, ReminderUpdate, ReminderOut, RoutineCreate, RoutineOut
from backend.auth import get_current_user

router = APIRouter(prefix="/api/goals", tags=["Goals & Reminders"])

DEFAULT_ROUTINES = [
    {
        "title": "Deep Work Focus Block",
        "start_time": "09:00",
        "end_time": "17:00",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "blocked_categories": ["Social", "Gaming", "Entertainment"]
    },
    {
        "title": "Night Wind-Down Routine",
        "start_time": "22:30",
        "end_time": "06:00",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "blocked_categories": ["Social", "Entertainment"]
    }
]

def check_routine_active(start_time: str, end_time: str, days: List[str]) -> bool:
    now = datetime.now()
    day_name = now.strftime("%a")
    if days and day_name not in days:
        return False

    current_time = now.strftime("%H:%M")
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return current_time >= start_time or current_time <= end_time


@router.get("")
async def get_goals_and_reminders(current_user: dict = Depends(get_current_user)):
    db = get_db()
    reminders_coll = db["reminders"]
    
    reminders = await reminders_coll.find({"user_id": current_user["id"]}).to_list(length=100)
    
    formatted_reminders = [
        ReminderOut(
            id=r["_id"],
            user_id=r["user_id"],
            title=r["title"],
            time=r["time"],
            days=r.get("days", []),
            reminder_type=r.get("reminder_type", "Break"),
            enabled=r.get("enabled", True),
            created_at=r.get("created_at", "")
        )
        for r in reminders
    ]
    
    return {
        "daily_goal_minutes": current_user["daily_goal_minutes"],
        "reminders": formatted_reminders
    }

@router.put("/goal")
async def update_daily_goal(
    goal_in: GoalUpdate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    users_coll = db["users"]
    
    await users_coll.update_one(
        {"_id": current_user["id"]},
        {"$set": {"daily_goal_minutes": goal_in.daily_goal_minutes}}
    )
    
    return {"message": "Goal updated", "daily_goal_minutes": goal_in.daily_goal_minutes}

@router.post("/reminders", response_model=ReminderOut)
async def create_reminder(
    rem_in: ReminderCreate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    reminders_coll = db["reminders"]
    
    rem_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    
    doc = {
        "_id": rem_id,
        "user_id": current_user["id"],
        "title": rem_in.title,
        "time": rem_in.time,
        "days": rem_in.days,
        "reminder_type": rem_in.reminder_type,
        "enabled": rem_in.enabled,
        "created_at": now_iso
    }
    
    await reminders_coll.insert_one(doc)
    
    return ReminderOut(
        id=doc["_id"],
        user_id=doc["user_id"],
        title=doc["title"],
        time=doc["time"],
        days=doc["days"],
        reminder_type=doc["reminder_type"],
        enabled=doc["enabled"],
        created_at=doc["created_at"]
    )

@router.put("/reminders/{reminder_id}", response_model=ReminderOut)
async def update_reminder(
    reminder_id: str,
    rem_in: ReminderUpdate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    reminders_coll = db["reminders"]
    
    rem = await reminders_coll.find_one({"_id": reminder_id, "user_id": current_user["id"]})
    if not rem:
        raise HTTPException(status_code=404, detail="Reminder not found")
        
    updates = {}
    if rem_in.enabled is not None:
        updates["enabled"] = rem_in.enabled
    if rem_in.title is not None:
        updates["title"] = rem_in.title
    if rem_in.time is not None:
        updates["time"] = rem_in.time
    if rem_in.days is not None:
        updates["days"] = rem_in.days
    if rem_in.reminder_type is not None:
        updates["reminder_type"] = rem_in.reminder_type
        
    if updates:
        await reminders_coll.update_one({"_id": reminder_id}, {"$set": updates})
        
    updated = await reminders_coll.find_one({"_id": reminder_id})
    return ReminderOut(
        id=updated["_id"],
        user_id=updated["user_id"],
        title=updated["title"],
        time=updated["time"],
        days=updated["days"],
        reminder_type=updated.get("reminder_type", "Break"),
        enabled=updated.get("enabled", True),
        created_at=updated.get("created_at", "")
    )

@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    reminders_coll = db["reminders"]
    
    rem = await reminders_coll.find_one({"_id": reminder_id, "user_id": current_user["id"]})
    if not rem:
        raise HTTPException(status_code=404, detail="Reminder not found")
        
    await reminders_coll.delete_one({"_id": reminder_id})
    return {"message": "Reminder deleted"}

@router.get("/routines", response_model=List[RoutineOut])
async def get_routines(current_user: dict = Depends(get_current_user)):
    db = get_db()
    routines_coll = db["routines"]
    
    user_routines = await routines_coll.find({"user_id": current_user["id"]}).to_list(length=100)
    
    # Pre-seed default routines if user has none
    if not user_routines:
        now_iso = datetime.utcnow().isoformat()
        for default_r in DEFAULT_ROUTINES:
            doc = {
                "_id": str(uuid.uuid4()),
                "user_id": current_user["id"],
                "title": default_r["title"],
                "start_time": default_r["start_time"],
                "end_time": default_r["end_time"],
                "days": default_r["days"],
                "blocked_categories": default_r["blocked_categories"],
                "enabled": True,
                "created_at": now_iso
            }
            await routines_coll.insert_one(doc)
        user_routines = await routines_coll.find({"user_id": current_user["id"]}).to_list(length=100)

    results = []
    for r in user_routines:
        enabled = r.get("enabled", True)
        start_t = r.get("start_time", "09:00")
        end_t = r.get("end_time", "17:00")
        days = r.get("days", [])
        
        is_active = enabled and check_routine_active(start_t, end_t, days)
        
        results.append(RoutineOut(
            id=r["_id"],
            user_id=r["user_id"],
            title=r.get("title", "Routine"),
            start_time=start_t,
            end_time=end_t,
            days=days,
            blocked_categories=r.get("blocked_categories", ["Social"]),
            enabled=enabled,
            is_currently_active=is_active,
            created_at=r.get("created_at", "")
        ))

    return results

@router.post("/routines", response_model=RoutineOut)
async def create_routine(
    entry: RoutineCreate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    routines_coll = db["routines"]
    
    doc_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    
    doc = {
        "_id": doc_id,
        "user_id": current_user["id"],
        "title": entry.title,
        "start_time": entry.start_time,
        "end_time": entry.end_time,
        "days": entry.days,
        "blocked_categories": entry.blocked_categories,
        "enabled": entry.enabled,
        "created_at": now_iso
    }
    
    await routines_coll.insert_one(doc)
    
    is_active = entry.enabled and check_routine_active(entry.start_time, entry.end_time, entry.days)
    return RoutineOut(
        id=doc["_id"],
        user_id=doc["user_id"],
        title=doc["title"],
        start_time=doc["start_time"],
        end_time=doc["end_time"],
        days=doc["days"],
        blocked_categories=doc["blocked_categories"],
        enabled=doc["enabled"],
        is_currently_active=is_active,
        created_at=doc["created_at"]
    )

@router.delete("/routines/{routine_id}")
async def delete_routine(
    routine_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    routines_coll = db["routines"]
    
    r = await routines_coll.find_one({"_id": routine_id, "user_id": current_user["id"]})
    if not r:
        raise HTTPException(status_code=404, detail="Routine not found")
        
    await routines_coll.delete_one({"_id": routine_id})
    return {"message": "Routine deleted"}

