from fastapi import APIRouter
from typing import List
from backend.models import WellbeingTip

router = APIRouter(prefix="/api/tips", tags=["Wellbeing Tips"])

TIPS_DATA = [
    {
        "id": "tip_1",
        "title": "The 20-20-20 Rule for Eye Strain",
        "category": "Rest",
        "description": "Every 20 minutes spent looking at a digital screen, look away at an object 20 feet away for at least 20 seconds to relax your eye muscles and avoid fatigue.",
        "action_text": "Start 20-Sec Rest",
        "action_type": "breathing"
    },
    {
        "id": "tip_2",
        "title": "Designate Phone-Free Zones",
        "category": "Habit",
        "description": "Keep your bedroom and dining table phone-free. Charge your phone outside your reach while sleeping to improve melatonin levels and deep sleep quality.",
        "action_text": "Set Bedtime Reminder",
        "action_type": "break"
    },
    {
        "id": "tip_3",
        "title": "5-Minute Physical Reset Walk",
        "category": "Focus",
        "description": "Sitting and continuously scrolling drains mental stamina. Step outside or walk around your room for 5 minutes without holding your smartphone.",
        "action_text": "Launch 5-Min Walk Timer",
        "action_type": "walk"
    },
    {
        "id": "tip_4",
        "title": "Turn On Grayscale Mode",
        "category": "Mindset",
        "description": "Smartphones use bright neon colors to stimulate dopamine. Switching your phone to Grayscale makes apps less stimulating and reduces compulsive checking.",
        "action_text": "Learn How to Enable",
        "action_type": "reading"
    },
    {
        "id": "tip_5",
        "title": "Mindful Notification Cleanup",
        "category": "Habit",
        "description": "Disable non-essential push notifications for social media and shopping apps. Batch checking notifications twice a day saves up to 90 minutes daily.",
        "action_text": "Audit Notifications",
        "action_type": "reading"
    },
    {
        "id": "tip_6",
        "title": "Re-Discover Physical Reading",
        "category": "Focus",
        "description": "Replace late-night scrolling with 15 minutes of physical book reading. Reading calms the nervous system and improves brain focus endurance.",
        "action_text": "15-Min Reading Timer",
        "action_type": "reading"
    }
]

@router.get("", response_model=List[WellbeingTip])
async def get_tips():
    return [WellbeingTip(**t) for t in TIPS_DATA]
