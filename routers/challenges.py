from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
import uuid

from backend.database import get_db
from backend.models import ChallengeOut, LeaderboardEntry
from backend.auth import get_current_user

router = APIRouter(prefix="/api/challenges", tags=["Social Challenges & Leaderboard"])

DEFAULT_CHALLENGES = [
  {
    "id": "chal-1",
    "title": "🌙 No Night Scrolling Challenge",
    "description": "Stop smartphone usage after 9:30 PM for 7 consecutive days to restore deep sleep.",
    "category": "Sleep & Rest",
    "duration_days": 7,
    "reward_badge": "Night Owl Restored 🦉",
    "participants_count": 42
  },
  {
    "id": "chal-2",
    "title": "⚡ 2-Hour Daily Screen Time Cap",
    "description": "Keep your total smartphone usage under 120 minutes per day for 5 days.",
    "category": "Digital Wellbeing",
    "duration_days": 5,
    "reward_badge": "Screen Master 🛡️",
    "participants_count": 89
  },
  {
    "id": "chal-3",
    "title": "🧘 500 Focus Minutes Challenge",
    "description": "Complete 500 minutes of Pomodoro focus sessions this week.",
    "category": "Deep Focus",
    "duration_days": 7,
    "reward_badge": "Monk Focus 🧘",
    "participants_count": 64
  },
  {
    "id": "chal-4",
    "title": "🌱 Weekend Digital Detox",
    "description": "Keep phone usage under 45 minutes on Saturday & Sunday.",
    "category": "Detox",
    "duration_days": 2,
    "reward_badge": "Nature Reconnect 🌲",
    "participants_count": 31
  }
]

@router.get("", response_model=List[ChallengeOut])
async def get_challenges(current_user: dict = Depends(get_current_user)):
    db = get_db()
    user_chals_coll = db["user_challenges"]
    
    user_joined = await user_chals_coll.find({"user_id": current_user["id"]}).to_list(length=100)
    joined_ids = {u["challenge_id"]: u for u in user_joined}
    
    results = []
    for c in DEFAULT_CHALLENGES:
        is_joined = c["id"] in joined_ids
        user_data = joined_ids.get(c["id"], {})
        
        results.append(ChallengeOut(
            id=c["id"],
            title=c["title"],
            description=c["description"],
            category=c["category"],
            duration_days=c["duration_days"],
            joined=is_joined,
            progress_days=user_data.get("progress_days", 0 if not is_joined else 3),
            streak_count=user_data.get("streak_count", 0 if not is_joined else 3),
            reward_badge=c["reward_badge"],
            participants_count=c["participants_count"] + (1 if is_joined else 0)
        ))
        
    return results

@router.post("/{challenge_id}/join")
async def toggle_join_challenge(
    challenge_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    user_chals_coll = db["user_challenges"]
    
    existing = await user_chals_coll.find_one({"user_id": current_user["id"], "challenge_id": challenge_id})
    if existing:
        await user_chals_coll.delete_one({"_id": existing["_id"]})
        return {"message": "Left challenge", "joined": False}
    else:
        doc = {
            "_id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "challenge_id": challenge_id,
            "progress_days": 1,
            "streak_count": 1,
            "created_at": datetime.utcnow().isoformat()
        }
        await user_chals_coll.insert_one(doc)
        return {"message": "Joined challenge!", "joined": True}

@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(current_user: dict = Depends(get_current_user)):
    db = get_db()
    users_coll = db["users"]
    focus_coll = db["focus_sessions"]
    screentime_coll = db["screentime"]
    
    users = await users_coll.find({}).to_list(length=100)
    
    leaderboard = [
        LeaderboardEntry(rank=1, user_name="Aarav Sharma", avatar="🧘‍♂️", screen_time_mins=85, focus_mins=240, streak_days=14),
        LeaderboardEntry(rank=2, user_name="Priya Patel", avatar="⚡", screen_time_mins=110, focus_mins=210, streak_days=12),
        LeaderboardEntry(rank=3, user_name=current_user["full_name"], avatar=current_user.get("avatar", "😎"), screen_time_mins=135, focus_mins=180, streak_days=7),
        LeaderboardEntry(rank=4, user_name="Vikram Singh", avatar="🚀", screen_time_mins=160, focus_mins=150, streak_days=5),
        LeaderboardEntry(rank=5, user_name="Ananya Roy", avatar="🌱", screen_time_mins=190, focus_mins=120, streak_days=4),
        LeaderboardEntry(rank=6, user_name="Rohan Verma", avatar="🎧", screen_time_mins=220, focus_mins=90, streak_days=3),
    ]
    
    return leaderboard
