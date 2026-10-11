from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime, date
import uuid

from backend.database import get_db
from backend.auth import get_current_user
from backend.models import (
    AccountabilityPartnerCreate,
    AccountabilityPartnerOut,
    EmergencyUnlockRequest,
    FrictionRuleCreate,
    FrictionRuleOut
)

router = APIRouter(prefix="/api/accountability", tags=["Accountability & Friction"])

DEFAULT_FRICTION_RULES = [
    {
        "app_name": "YouTube",
        "domain_or_package": "youtube.com",
        "breathing_seconds": 7,
        "intent_options": ["Habit / Muscle Memory", "Boredom", "Intentional Video", "Work / Tutorial"],
        "active": True,
        "interceptions_count": 14,
        "aborted_opens_count": 9
    },
    {
        "app_name": "Instagram",
        "domain_or_package": "instagram.com",
        "breathing_seconds": 10,
        "intent_options": ["Mindless Scroll", "Urgent Message", "Boredom", "Quick Post Check"],
        "active": True,
        "interceptions_count": 22,
        "aborted_opens_count": 16
    },
    {
        "app_name": "Reddit",
        "domain_or_package": "reddit.com",
        "breathing_seconds": 8,
        "intent_options": ["Doomscrolling", "Looking up Solution", "Procrastination"],
        "active": True,
        "interceptions_count": 8,
        "aborted_opens_count": 5
    },
    {
        "app_name": "Twitter / X",
        "domain_or_package": "x.com",
        "breathing_seconds": 7,
        "intent_options": ["Checking News", "Habit", "Replying to Mention"],
        "active": True,
        "interceptions_count": 11,
        "aborted_opens_count": 7
    }
]

@router.get("/partner", response_model=Optional[AccountabilityPartnerOut])
async def get_accountability_partner(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    partner = await db["accountability_partners"].find_one({"user_id": user_id})
    if not partner:
        return None
    return AccountabilityPartnerOut(
        id=partner["_id"],
        user_id=partner["user_id"],
        partner_name=partner["partner_name"],
        partner_email=partner["partner_email"],
        phone_number=partner.get("phone_number", ""),
        notify_on_limit_exceeded=partner.get("notify_on_limit_exceeded", True),
        hard_lock_mode=partner.get("hard_lock_mode", False),
        created_at=partner.get("created_at", "")
    )

@router.post("/partner", response_model=AccountabilityPartnerOut)
async def save_accountability_partner(
    req: AccountabilityPartnerCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    existing = await db["accountability_partners"].find_one({"user_id": user_id})
    now_iso = datetime.utcnow().isoformat()
    
    if existing:
        await db["accountability_partners"].update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "partner_name": req.partner_name,
                "partner_email": req.partner_email,
                "phone_number": req.phone_number,
                "notify_on_limit_exceeded": req.notify_on_limit_exceeded,
                "hard_lock_mode": req.hard_lock_mode,
                "updated_at": now_iso
            }}
        )
        partner_id = existing["_id"]
    else:
        partner_id = str(uuid.uuid4())
        await db["accountability_partners"].insert_one({
            "_id": partner_id,
            "user_id": user_id,
            "partner_name": req.partner_name,
            "partner_email": req.partner_email,
            "phone_number": req.phone_number,
            "notify_on_limit_exceeded": req.notify_on_limit_exceeded,
            "hard_lock_mode": req.hard_lock_mode,
            "created_at": now_iso
        })
        
    return AccountabilityPartnerOut(
        id=partner_id,
        user_id=user_id,
        partner_name=req.partner_name,
        partner_email=req.partner_email,
        phone_number=req.phone_number,
        notify_on_limit_exceeded=req.notify_on_limit_exceeded,
        hard_lock_mode=req.hard_lock_mode,
        created_at=now_iso
    )

@router.delete("/partner")
async def delete_accountability_partner(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    await db["accountability_partners"].delete_many({"user_id": user_id})
    return {"message": "Accountability partner removed successfully"}

@router.post("/emergency-unlock")
async def emergency_unlock_app(
    req: EmergencyUnlockRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    partner = await db["accountability_partners"].find_one({"user_id": user_id})
    
    if not req.reflection_note or len(req.reflection_note.strip()) < 10:
        raise HTTPException(
            status_code=400, 
            detail="Mindful reflection note must be at least 10 characters explaining why you need to unblock this app."
        )
        
    unlock_log_id = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    
    log_doc = {
        "_id": unlock_log_id,
        "user_id": user_id,
        "app_name": req.app_name,
        "unlock_duration_minutes": req.unlock_duration_minutes,
        "reflection_note": req.reflection_note,
        "partner_notified": bool(partner),
        "partner_email": partner.get("partner_email") if partner else None,
        "created_at": now_iso,
        "status": "granted_temporary"
    }
    await db["emergency_unlocks"].insert_one(log_doc)
    
    # Temporarily unblock in app_limits
    limits_coll = db["app_limits"]
    await limits_coll.update_many(
        {"user_id": user_id, "app_name": {"$regex": f"^{req.app_name}$", "$options": "i"}},
        {"$set": {"is_blocked": False, "temporary_unblock_until": (datetime.utcnow()).isoformat()}}
    )
    
    return {
        "status": "success",
        "message": f"Temporary {req.unlock_duration_minutes}-min emergency pass granted for {req.app_name}.",
        "partner_notified": bool(partner),
        "partner_name": partner.get("partner_name") if partner else "None configured",
        "log_id": unlock_log_id
    }

@router.get("/emergency-unlocks")
async def get_emergency_unlock_logs(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    logs = await db["emergency_unlocks"].find({"user_id": user_id}).to_list(50)
    return logs

@router.get("/friction-rules", response_model=List[FrictionRuleOut])
async def get_friction_rules(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    rules = await db["friction_rules"].find({"user_id": user_id}).to_list(100)
    
    if not rules:
        # Seed defaults
        created_rules = []
        now_iso = datetime.utcnow().isoformat()
        for r in DEFAULT_FRICTION_RULES:
            rule_id = str(uuid.uuid4())
            doc = {
                "_id": rule_id,
                "user_id": user_id,
                "app_name": r["app_name"],
                "domain_or_package": r["domain_or_package"],
                "breathing_seconds": r["breathing_seconds"],
                "intent_options": r["intent_options"],
                "active": r["active"],
                "interceptions_count": r["interceptions_count"],
                "aborted_opens_count": r["aborted_opens_count"],
                "created_at": now_iso
            }
            await db["friction_rules"].insert_one(doc)
            created_rules.append(FrictionRuleOut(
                id=doc["_id"],
                user_id=doc["user_id"],
                app_name=doc["app_name"],
                domain_or_package=doc["domain_or_package"],
                breathing_seconds=doc["breathing_seconds"],
                intent_options=doc["intent_options"],
                active=doc["active"],
                interceptions_count=doc["interceptions_count"],
                aborted_opens_count=doc["aborted_opens_count"]
            ))
        return created_rules
        
    return [
        FrictionRuleOut(
            id=r["_id"],
            user_id=r["user_id"],
            app_name=r["app_name"],
            domain_or_package=r["domain_or_package"],
            breathing_seconds=r["breathing_seconds"],
            intent_options=r.get("intent_options", ["Habit", "Boredom", "Work"]),
            active=r.get("active", True),
            interceptions_count=r.get("interceptions_count", 0),
            aborted_opens_count=r.get("aborted_opens_count", 0)
        )
        for r in rules
    ]

@router.post("/friction-rules", response_model=FrictionRuleOut)
async def create_or_update_friction_rule(
    req: FrictionRuleCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    existing = await db["friction_rules"].find_one({
        "user_id": user_id,
        "domain_or_package": req.domain_or_package.lower()
    })
    now_iso = datetime.utcnow().isoformat()
    
    if existing:
        await db["friction_rules"].update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "app_name": req.app_name,
                "breathing_seconds": req.breathing_seconds,
                "intent_options": req.intent_options,
                "active": req.active
            }}
        )
        return FrictionRuleOut(
            id=existing["_id"],
            user_id=user_id,
            app_name=req.app_name,
            domain_or_package=req.domain_or_package,
            breathing_seconds=req.breathing_seconds,
            intent_options=req.intent_options,
            active=req.active,
            interceptions_count=existing.get("interceptions_count", 0),
            aborted_opens_count=existing.get("aborted_opens_count", 0)
        )
    else:
        rule_id = str(uuid.uuid4())
        doc = {
            "_id": rule_id,
            "user_id": user_id,
            "app_name": req.app_name,
            "domain_or_package": req.domain_or_package.lower(),
            "breathing_seconds": req.breathing_seconds,
            "intent_options": req.intent_options,
            "active": req.active,
            "interceptions_count": 0,
            "aborted_opens_count": 0,
            "created_at": now_iso
        }
        await db["friction_rules"].insert_one(doc)
        return FrictionRuleOut(
            id=rule_id,
            user_id=user_id,
            app_name=req.app_name,
            domain_or_package=req.domain_or_package,
            breathing_seconds=req.breathing_seconds,
            intent_options=req.intent_options,
            active=req.active,
            interceptions_count=0,
            aborted_opens_count=0
        )

@router.post("/friction-rules/log-interception")
async def log_friction_interception(
    domain: str,
    action: str, # "aborted" or "proceeded"
    intent: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = current_user.get("_id") or current_user.get("id")
    rule = await db["friction_rules"].find_one({"user_id": user_id, "domain_or_package": domain.lower()})
    
    if rule:
        update_fields = {"interceptions_count": rule.get("interceptions_count", 0) + 1}
        if action == "aborted":
            update_fields["aborted_opens_count"] = rule.get("aborted_opens_count", 0) + 1
        await db["friction_rules"].update_one({"_id": rule["_id"]}, {"$set": update_fields})
        
    # Also log event in history
    await db["friction_events"].insert_one({
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "domain": domain,
        "action": action,
        "intent": intent,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {"status": "recorded", "action": action}
