from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
import uuid

from backend.database import get_db
from backend.models import UserRegister, UserLogin, UserProfileUpdate, UserOut, Token
from backend.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])

INITIAL_ACHIEVEMENTS = [
    {
        "badge_id": "first_focus",
        "title": "Focus Novice",
        "description": "Completed your first focus session",
        "icon": "Target",
        "category": "Focus",
        "target": 1
    },
    {
        "badge_id": "focus_master",
        "title": "Deep Focus Master",
        "description": "Completed 10 focus sessions",
        "icon": "Zap",
        "category": "Focus",
        "target": 10
    },
    {
        "badge_id": "streak_3",
        "title": "3-Day Warrior",
        "description": "Maintained a 3-day wellbeing streak",
        "icon": "Flame",
        "category": "Streak",
        "target": 3
    },
    {
        "badge_id": "streak_7",
        "title": "Weekly Zen",
        "description": "Maintained a 7-day streak",
        "icon": "Crown",
        "category": "Streak",
        "target": 7
    },
    {
        "badge_id": "goal_crusher",
        "title": "Goal Crusher",
        "description": "Stayed under daily screen time goal 5 times",
        "icon": "ShieldCheck",
        "category": "Goals",
        "target": 5
    },
    {
        "badge_id": "mindful_checker",
        "title": "Mindful Reflector",
        "description": "Completed 5 daily check-ins",
        "icon": "Smile",
        "category": "Mindfulness",
        "target": 5
    }
]

DEFAULT_REMINDERS = [
    {
        "title": "Take a 5-Min Walk & Rest Eyes",
        "time": "14:00",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "reminder_type": "Break",
        "enabled": True
    },
    {
        "title": "Evening Wind-Down Check-in",
        "time": "21:00",
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "reminder_type": "Check-in",
        "enabled": True
    }
]

@router.post("/register", response_model=Token)
async def register(user_in: UserRegister):
    db = get_db()
    users_coll = db["users"]
    
    existing = await users_coll.find_one({"email": user_in.email.lower()})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )
    
    user_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    
    user_doc = {
        "_id": user_id,
        "email": user_in.email.lower(),
        "hashed_password": hash_password(user_in.password),
        "full_name": user_in.full_name,
        "daily_goal_minutes": user_in.daily_goal_minutes or 180,
        "avatar": "",
        "created_at": now_iso
    }
    
    await users_coll.insert_one(user_doc)
    
    # Initialize default achievements for this user
    achievements_coll = db["achievements"]
    for ach in INITIAL_ACHIEVEMENTS:
        await achievements_coll.insert_one({
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "badge_id": ach["badge_id"],
            "title": ach["title"],
            "description": ach["description"],
            "icon": ach["icon"],
            "category": ach["category"],
            "unlocked": False,
            "unlocked_at": None,
            "progress": 0,
            "target": ach["target"]
        })
        
    # Initialize default reminders
    reminders_coll = db["reminders"]
    for rem in DEFAULT_REMINDERS:
        await reminders_coll.insert_one({
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": rem["title"],
            "time": rem["time"],
            "days": rem["days"],
            "reminder_type": rem["reminder_type"],
            "enabled": rem["enabled"],
            "created_at": now_iso
        })

    access_token = create_access_token(data={"sub": user_id})
    
    user_out = UserOut(
        id=user_id,
        email=user_doc["email"],
        full_name=user_doc["full_name"],
        daily_goal_minutes=user_doc["daily_goal_minutes"],
        avatar=user_doc["avatar"],
        created_at=user_doc["created_at"]
    )
    
    return Token(access_token=access_token, user=user_out)

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin):
    db = get_db()
    users_coll = db["users"]
    
    user = await users_coll.find_one({"email": user_in.email.lower()})
    if not user or not verify_password(user_in.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user["_id"]})
    user_out = UserOut(
        id=user["_id"],
        email=user["email"],
        full_name=user.get("full_name", "User"),
        daily_goal_minutes=user.get("daily_goal_minutes", 180),
        avatar=user.get("avatar", ""),
        created_at=user.get("created_at", "")
    )
    return Token(access_token=access_token, user=user_out)

@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return UserOut(**current_user)

@router.put("/profile", response_model=UserOut)
async def update_profile(
    profile_in: UserProfileUpdate, 
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    users_coll = db["users"]
    
    updates = {}
    if profile_in.full_name is not None:
        updates["full_name"] = profile_in.full_name
    if profile_in.daily_goal_minutes is not None:
        updates["daily_goal_minutes"] = profile_in.daily_goal_minutes
    if profile_in.avatar is not None:
        updates["avatar"] = profile_in.avatar
        
    if updates:
        await users_coll.update_one({"_id": current_user["id"]}, {"$set": updates})
        
    updated_user = await users_coll.find_one({"_id": current_user["id"]})
    return UserOut(
        id=updated_user["_id"],
        email=updated_user["email"],
        full_name=updated_user.get("full_name", "User"),
        daily_goal_minutes=updated_user.get("daily_goal_minutes", 180),
        avatar=updated_user.get("avatar", ""),
        created_at=updated_user.get("created_at", "")
    )
