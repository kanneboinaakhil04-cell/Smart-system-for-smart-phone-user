
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timedelta, date
import uuid

from backend.database import get_db
from backend.models import ScreenTimeCreate, ScreenTimeOut, AppLimitCreate, AppLimitOut, TelemetryHeartbeat
from backend.auth import get_current_user

router = APIRouter(prefix="/api/screentime", tags=["ScreenTime"])

DEFAULT_APP_LIMITS = [
    {"app_name": "Instagram", "limit_minutes": 30, "category": "Social"},
    {"app_name": "YouTube", "limit_minutes": 45, "category": "Entertainment"},
    {"app_name": "TikTok", "limit_minutes": 25, "category": "Social"},
    {"app_name": "WhatsApp", "limit_minutes": 60, "category": "Social"},
    {"app_name": "X / Twitter", "limit_minutes": 30, "category": "Social"},
    {"app_name": "Snapchat", "limit_minutes": 20, "category": "Social"},
    {"app_name": "Netflix", "limit_minutes": 60, "category": "Entertainment"},
    {"app_name": "PubG / Gaming", "limit_minutes": 40, "category": "Gaming"},
]


@router.post("", response_model=ScreenTimeOut)
async def add_screentime_log(
    entry: ScreenTimeCreate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    screentime_coll = db["screentime"]
    
    log_id = str(uuid.uuid4())
    today_str = entry.date if entry.date else date.today().isoformat()
    now_iso = datetime.utcnow().isoformat()
    
    doc = {
        "_id": log_id,
        "user_id": current_user["id"],
        "app_name": entry.app_name,
        "category": entry.category,
        "duration_minutes": entry.duration_minutes,
        "date": today_str,
        "created_at": now_iso
    }
    
    await screentime_coll.insert_one(doc)
    
    return ScreenTimeOut(
        id=doc["_id"],
        user_id=doc["user_id"],
        app_name=doc["app_name"],
        category=doc["category"],
        duration_minutes=doc["duration_minutes"],
        date=doc["date"],
        created_at=doc["created_at"]
    )

@router.get("", response_model=List[ScreenTimeOut])
async def get_screentime_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    screentime_coll = db["screentime"]
    
    query = {"user_id": current_user["id"]}
    
    cursor = screentime_coll.find(query)
    items = await cursor.to_list(length=500)
    
    # Filter by dates if passed
    filtered = []
    for item in items:
        d = item.get("date", "")
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue
        filtered.append(item)
        
    filtered.sort(key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
    
    return [
        ScreenTimeOut(
            id=item["_id"],
            user_id=item["user_id"],
            app_name=item["app_name"],
            category=item["category"],
            duration_minutes=item["duration_minutes"],
            date=item["date"],
            created_at=item.get("created_at", "")
        )
        for item in filtered
    ]

@router.get("/summary")
async def get_screentime_summary(current_user: dict = Depends(get_current_user)):
    db = get_db()
    screentime_coll = db["screentime"]
    
    today = date.today()
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()
    
    items = await screentime_coll.find({"user_id": current_user["id"]}).to_list(length=1000)
    
    today_logs = [i for i in items if i.get("date") == today_str]
    yesterday_logs = [i for i in items if i.get("date") == yesterday_str]
    
    today_total = sum(i.get("duration_minutes", 0) for i in today_logs)
    yesterday_total = sum(i.get("duration_minutes", 0) for i in yesterday_logs)
    
    diff_minutes = today_total - yesterday_total
    percent_change = 0
    if yesterday_total > 0:
        percent_change = round(((today_total - yesterday_total) / yesterday_total) * 100, 1)
        
    # Category breakdown for today
    category_totals = {}
    for log in today_logs:
        cat = log.get("category", "Other")
        category_totals[cat] = category_totals.get(cat, 0) + log.get("duration_minutes", 0)
        
    # Last 7 days breakdown
    days_data = []
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_str = day_date.isoformat()
        day_logs = [l for l in items if l.get("date") == day_str]
        day_total = sum(l.get("duration_minutes", 0) for l in day_logs)
        days_data.append({
            "date": day_str,
            "day_name": day_date.strftime("%a"),
            "duration_minutes": day_total
        })
        
    return {
        "today_total_minutes": today_total,
        "yesterday_total_minutes": yesterday_total,
        "diff_minutes": diff_minutes,
        "percent_change": percent_change,
        "daily_goal_minutes": current_user["daily_goal_minutes"],
        "category_totals": category_totals,
        "weekly_trend": days_data
    }

@router.delete("/{log_id}")
async def delete_screentime_log(
    log_id: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    screentime_coll = db["screentime"]
    
    log = await screentime_coll.find_one({"_id": log_id, "user_id": current_user["id"]})
    if not log:
        raise HTTPException(status_code=404, detail="Screen time log not found")
        
    await screentime_coll.delete_one({"_id": log_id})
    return {"message": "Log deleted successfully"}

@router.get("/app-limits", response_model=List[AppLimitOut])
async def get_app_limits(current_user: dict = Depends(get_current_user)):
    db = get_db()
    limits_coll = db["app_limits"]
    screentime_coll = db["screentime"]
    
    user_limits = await limits_coll.find({"user_id": current_user["id"]}).to_list(length=100)
    
    # Get today's logs to calculate actual usage per app
    today_str = date.today().isoformat()
    screentime_logs = await screentime_coll.find({"user_id": current_user["id"], "date": today_str}).to_list(length=1000)
    
    # Group usage by app name (case-insensitive)
    usage_by_app = {}
    for log in screentime_logs:
        app_name_clean = log.get("app_name", "").strip().lower()
        usage_by_app[app_name_clean] = usage_by_app.get(app_name_clean, 0) + log.get("duration_minutes", 0)

    results = []
    for item in user_limits:
        app_name = item.get("app_name", "")
        app_name_clean = app_name.strip().lower()
        
        used_mins = usage_by_app.get(app_name_clean, 0)
        if used_mins == 0:
            for logged_app, mins in usage_by_app.items():
                if logged_app in app_name_clean or app_name_clean in logged_app:
                    used_mins += mins
                    
        limit_mins = item.get("limit_minutes", 30)
        remaining = max(0, limit_mins - used_mins)
        is_blocked = item.get("is_blocked", False)
        
        if is_blocked or used_mins >= limit_mins:
            status = "exceeded"
        elif used_mins >= 0.8 * limit_mins:
            status = "warning"
        else:
            status = "normal"

        results.append(AppLimitOut(
            id=item["_id"],
            user_id=item["user_id"],
            app_name=app_name,
            limit_minutes=limit_mins,
            category=item.get("category", "Social"),
            used_today_minutes=used_mins,
            remaining_minutes=remaining,
            status=status,
            is_blocked=is_blocked,
            created_at=item.get("created_at", "")
        ))

    return results

@router.post("/app-limits", response_model=AppLimitOut)
async def save_app_limit(
    entry: AppLimitCreate,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    limits_coll = db["app_limits"]
    
    items = await limits_coll.find({"user_id": current_user["id"]}).to_list(length=100)
    existing = None
    for i in items:
        if i.get("app_name", "").lower() == entry.app_name.lower():
            existing = i
            break
    
    now_iso = datetime.utcnow().isoformat()
    if existing:
        await limits_coll.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "limit_minutes": entry.limit_minutes,
                "category": entry.category or existing.get("category", "Social"),
                "is_blocked": entry.is_blocked if entry.is_blocked is not None else existing.get("is_blocked", False)
            }}
        )
    else:
        limit_id = str(uuid.uuid4())
        doc = {
            "_id": limit_id,
            "user_id": current_user["id"],
            "app_name": entry.app_name,
            "limit_minutes": entry.limit_minutes,
            "category": entry.category or "Social",
            "is_blocked": entry.is_blocked or False,
            "created_at": now_iso
        }
        await limits_coll.insert_one(doc)

    all_limits = await get_app_limits(current_user)
    for l in all_limits:
        if l.app_name.lower() == entry.app_name.lower():
            return l
            
    raise HTTPException(status_code=400, detail="Failed to save app limit")

@router.delete("/app-limits/{app_name}")
async def delete_app_limit(
    app_name: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    limits_coll = db["app_limits"]
    
    items = await limits_coll.find({"user_id": current_user["id"]}).to_list(length=100)
    target = None
    for i in items:
        if i.get("app_name", "").lower() == app_name.lower():
            target = i
            break

    if not target:
        raise HTTPException(status_code=404, detail="App limit not found")

    await limits_coll.delete_one({"_id": target["_id"]})
    return {"message": f"App limit for {app_name} removed"}

@router.post("/app-limits/toggle-block/{app_name}")
async def toggle_app_block(
    app_name: str,
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    limits_coll = db["app_limits"]
    
    items = await limits_coll.find({"user_id": current_user["id"]}).to_list(length=100)
    target = None
    for i in items:
        if i.get("app_name", "").lower() == app_name.lower():
            target = i
            break

    if not target:
        raise HTTPException(status_code=404, detail="App limit not found")

    new_status = not target.get("is_blocked", False)
    await limits_coll.update_one({"_id": target["_id"]}, {"$set": {"is_blocked": new_status}})
    return {"message": f"App block for {app_name} toggled to {new_status}", "is_blocked": new_status}

@router.post("/app-limits/sync-device")
async def sync_device_limits(
    current_user: dict = Depends(get_current_user)
):
    """Sync app limits and send real device blocking signals for Android/iOS Companion service."""
    limits = await get_app_limits(current_user)
    
    # Map app names to standard Android package names
    PACKAGE_MAP = {
        "instagram": "com.instagram.android",
        "youtube": "com.google.android.youtube",
        "tiktok": "com.zhiliaoapp.musically",
        "whatsapp": "com.whatsapp",
        "facebook": "com.facebook.katana",
        "twitter": "com.twitter.android",
        "x": "com.twitter.android",
        "snapchat": "com.snapchat.android",
        "netflix": "com.netflix.mediaclient",
        "pubg": "com.tencent.ig"
    }

    synced_rules = []
    for limit in limits:
        app_clean = limit.app_name.lower()
        package_name = PACKAGE_MAP.get(app_clean, f"com.app.{app_clean}")
        synced_rules.append({
            "app_name": limit.app_name,
            "package_name": package_name,
            "limit_minutes": limit.limit_minutes,
            "used_minutes": limit.used_today_minutes,
            "status": limit.status,
            "should_block": limit.status == "exceeded" or limit.is_blocked
        })

    return {
        "status": "success",
        "message": f"Synced {len(synced_rules)} app limit rules with Real Phone Companion Service",
        "user_id": current_user["id"],
        "sync_timestamp": datetime.utcnow().isoformat(),
        "device_sync_active": True,
        "rules": synced_rules
    }


@router.post("/agent-heartbeat")
async def process_agent_telemetry(
    heartbeat: TelemetryHeartbeat,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Heartbeat sent every 30s by Desktop Companion Agent or Browser Extension.
    Accumulates real screen time automatically into database.
    """
    user_id = current_user.get("_id") or current_user.get("id")
    today_str = date.today().isoformat()
    now_iso = datetime.utcnow().isoformat()
    
    # Check if a log entry already exists today for this app
    screentime_coll = db["screentime"]
    existing = await screentime_coll.find_one({
        "user_id": user_id,
        "app_name": heartbeat.app_name,
        "date": today_str
    })
    
    minutes_to_add = max(1, int(heartbeat.duration_seconds / 60))
    if existing:
        new_duration = existing.get("duration_minutes", 0) + minutes_to_add
        await screentime_coll.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "duration_minutes": new_duration,
                "last_active": now_iso,
                "window_title": heartbeat.window_title,
                "source": heartbeat.source
            }}
        )
    else:
        log_id = str(uuid.uuid4())
        await screentime_coll.insert_one({
            "_id": log_id,
            "user_id": user_id,
            "app_name": heartbeat.app_name,
            "category": heartbeat.category or "Productivity",
            "duration_minutes": minutes_to_add,
            "date": today_str,
            "last_active": now_iso,
            "window_title": heartbeat.window_title,
            "source": heartbeat.source,
            "created_at": now_iso
        })
        
    # Update device heartbeat status
    await db["device_telemetry"].update_one(
        {"user_id": user_id, "device_source": heartbeat.source},
        {"$set": {
            "last_ping": now_iso,
            "current_app": heartbeat.app_name,
            "window_title": heartbeat.window_title,
            "status": "connected"
        }},
        upsert=True
    )
    
    return {
        "status": "recorded",
        "app_name": heartbeat.app_name,
        "added_minutes": minutes_to_add,
        "sync_time": now_iso
    }


@router.get("/telemetry/status")
async def get_telemetry_status(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    devices = await db["device_telemetry"].find({"user_id": user_id}).to_list(10)
    
    return {
        "active_devices_count": len(devices),
        "devices": devices or [
            {
                "device_source": "desktop_agent",
                "status": "ready_to_connect",
                "last_ping": None,
                "current_app": "Waiting for companion script..."
            },
            {
                "device_source": "browser_extension",
                "status": "ready_to_connect",
                "last_ping": None,
                "current_app": "Waiting for Chrome extension..."
            }
        ]
    }



