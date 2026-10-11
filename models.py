from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

# User Schemas
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    daily_goal_minutes: Optional[int] = 180  # Default 3 hours

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    daily_goal_minutes: Optional[int] = None
    avatar: Optional[str] = None

class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    daily_goal_minutes: int
    avatar: Optional[str] = None
    created_at: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# Screen-Time Schemas
class ScreenTimeCreate(BaseModel):
    app_name: str
    category: str  # Social, Productivity, Entertainment, Gaming, Utilities, Other
    duration_minutes: int
    date: Optional[str] = None  # YYYY-MM-DD

class ScreenTimeOut(BaseModel):
    id: str
    user_id: str
    app_name: str
    category: str
    duration_minutes: int
    date: str
    created_at: str

# Daily Check-in Schemas
class DailyCheckInCreate(BaseModel):
    date: Optional[str] = None  # YYYY-MM-DD
    focus_rating: int = Field(..., ge=1, le=5)
    mood: str  # Happy, Neutral, Stressed, Calm, Exhausted, Productive
    sleep_hours: float = Field(..., ge=0, le=24)
    phone_habit_rating: int = Field(..., ge=1, le=5)
    notes: Optional[str] = ""

class DailyCheckInOut(BaseModel):
    id: str
    user_id: str
    date: str
    focus_rating: int
    mood: str
    sleep_hours: float
    phone_habit_rating: int
    notes: str
    created_at: str

# Focus Session Schemas
class FocusSessionCreate(BaseModel):
    duration_minutes: int
    session_type: str = "Focus"  # Focus, Short Break, Long Break
    completed: bool = True
    notes: Optional[str] = ""
    date: Optional[str] = None

class FocusSessionOut(BaseModel):
    id: str
    user_id: str
    duration_minutes: int
    session_type: str
    completed: bool
    notes: str
    date: str
    created_at: str

# Goals & Reminders Schemas
class GoalUpdate(BaseModel):
    daily_goal_minutes: int

class ReminderCreate(BaseModel):
    title: str
    time: str  # HH:MM format
    days: List[str]  # e.g., ["Mon", "Tue", "Wed", "Thu", "Fri"]
    reminder_type: str = "Break"  # Break, Focus, Check-in, Custom
    enabled: bool = True

class ReminderUpdate(BaseModel):
    enabled: Optional[bool] = None
    title: Optional[str] = None
    time: Optional[str] = None
    days: Optional[List[str]] = None
    reminder_type: Optional[str] = None

class ReminderOut(BaseModel):
    id: str
    user_id: str
    title: str
    time: str
    days: List[str]
    reminder_type: str
    enabled: bool
    created_at: str

# Achievement Schema
class AchievementOut(BaseModel):
    id: str
    badge_id: str
    title: str
    description: str
    icon: str
    category: str
    unlocked: bool
    unlocked_at: Optional[str] = None
    progress: int = 0
    target: int = 100

# Wellbeing Tip
class WellbeingTip(BaseModel):
    id: str
    title: str
    category: str  # Habit, Focus, Rest, Mindset
    description: str
    action_text: str
    action_type: str  # walk, breathing, reading, break

# App Limits Schemas
class AppLimitCreate(BaseModel):
    app_name: str
    limit_minutes: int
    category: Optional[str] = "Social"
    is_blocked: Optional[bool] = False

class AppLimitOut(BaseModel):
    id: str
    user_id: str
    app_name: str
    limit_minutes: int
    category: str = "Social"
    used_today_minutes: int = 0
    remaining_minutes: int = 0
    status: str = "normal"
    is_blocked: bool = False
    created_at: Optional[str] = ""


# Scheduled Routines Schemas
class RoutineCreate(BaseModel):
    title: str
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    days: List[str]  # e.g. ["Mon", "Tue", "Wed", "Thu", "Fri"]
    blocked_categories: List[str]  # ["Social", "Gaming", "Entertainment"]
    enabled: bool = True

class RoutineOut(BaseModel):
    id: str
    user_id: str
    title: str
    start_time: str
    end_time: str
    days: List[str]
    blocked_categories: List[str]
    enabled: bool
    is_currently_active: bool
    created_at: str

# Social Challenges Schemas
class ChallengeOut(BaseModel):
    id: str
    title: str
    description: str
    category: str
    duration_days: int
    joined: bool
    progress_days: int
    streak_count: int
    reward_badge: str
    participants_count: int

class LeaderboardEntry(BaseModel):
    rank: int
    user_name: str
    avatar: str
    screen_time_mins: int
    focus_mins: int
    streak_days: int

# Accountability Partner Schemas
class AccountabilityPartnerCreate(BaseModel):
    partner_name: str
    partner_email: str
    phone_number: Optional[str] = ""
    notify_on_limit_exceeded: bool = True
    hard_lock_mode: bool = False

class AccountabilityPartnerOut(BaseModel):
    id: str
    user_id: str
    partner_name: str
    partner_email: str
    phone_number: Optional[str] = ""
    notify_on_limit_exceeded: bool
    hard_lock_mode: bool
    created_at: str

class EmergencyUnlockRequest(BaseModel):
    app_name: str
    unlock_duration_minutes: int = 15
    reflection_note: str
    partner_notified: bool = True

# Mindful Friction Rule Schemas
class FrictionRuleCreate(BaseModel):
    app_name: str
    domain_or_package: str
    breathing_seconds: int = 7
    intent_options: List[str] = ["Boredom", "Habit", "Intentional Work", "Urgent Message"]
    active: bool = True

class FrictionRuleOut(BaseModel):
    id: str
    user_id: str
    app_name: str
    domain_or_package: str
    breathing_seconds: int
    intent_options: List[str]
    active: bool
    interceptions_count: int = 0
    aborted_opens_count: int = 0

# Telemetry Heartbeat Schema
class TelemetryHeartbeat(BaseModel):
    app_name: str
    window_title: Optional[str] = ""
    duration_seconds: int
    category: Optional[str] = "Productivity"
    source: str = "desktop_agent"

# Study Room Schemas
class StudyRoomOut(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    current_members: int
    timer_type: str = "Pomodoro 25/5"
    tags: List[str]



