from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/realtime", tags=["Real-time Live Notifications & Study Rooms"])

ROOMS_METADATA = [
    {
        "id": "silent-library",
        "name": "Silent Library (Deep Work)",
        "description": "Strict silence. Best for intensive studying, reading, and deep concentration.",
        "icon": "BookOpen",
        "timer_type": "Pomodoro 25/5",
        "tags": ["Silent", "Study", "No Distractions"]
    },
    {
        "id": "code-sprint",
        "name": "Code & Build Sprint",
        "description": "High-octane programming and building sprints with synchronized focus blocks.",
        "icon": "Code",
        "timer_type": "Pomodoro 50/10",
        "tags": ["Engineering", "Sprints", "Coding"]
    },
    {
        "id": "night-owls",
        "name": "Night Owls Focus Room",
        "description": "Late night quiet focus sanctuary with ambient brown noise.",
        "icon": "Moon",
        "timer_type": "Pomodoro 25/5",
        "tags": ["Late Night", "Calm", "Ambient Audio"]
    },
    {
        "id": "creative-flow",
        "name": "Creative Flow & Design",
        "description": "Mindful creative blocks for writers, artists, and UI designers.",
        "icon": "Palette",
        "timer_type": "Flowtime (Uncapped)",
        "tags": ["Design", "Writing", "Flow"]
    }
]

class RoomConnectionManager:
    def __init__(self):
        # Mapping room_id -> list of (WebSocket, participant_dict)
        self.rooms: Dict[str, List[Dict[str, Any]]] = {
            r["id"]: [] for r in ROOMS_METADATA
        }
        self.global_connections: List[WebSocket] = []

    async def connect_room(self, room_id: str, websocket: WebSocket, participant: Dict[str, Any]):
        await websocket.accept()
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        self.rooms[room_id].append({"ws": websocket, "user": participant})
        await self.broadcast_room(room_id, {
            "type": "member_joined",
            "user": participant,
            "members_count": len(self.rooms[room_id]),
            "members": [c["user"] for c in self.rooms[room_id]]
        })

    def disconnect_room(self, room_id: str, websocket: WebSocket):
        if room_id in self.rooms:
            leaving_user = None
            for item in self.rooms[room_id]:
                if item["ws"] == websocket:
                    leaving_user = item["user"]
                    break
            self.rooms[room_id] = [c for c in self.rooms[room_id] if c["ws"] != websocket]
            return leaving_user
        return None

    async def broadcast_room(self, room_id: str, message: dict):
        if room_id in self.rooms:
            dead_sockets = []
            for item in self.rooms[room_id]:
                try:
                    await item["ws"].send_json(message)
                except Exception:
                    dead_sockets.append(item["ws"])
            if dead_sockets:
                self.rooms[room_id] = [c for c in self.rooms[room_id] if c["ws"] not in dead_sockets]

    async def connect_global(self, websocket: WebSocket):
        await websocket.accept()
        self.global_connections.append(websocket)

    def disconnect_global(self, websocket: WebSocket):
        if websocket in self.global_connections:
            self.global_connections.remove(websocket)

    async def broadcast_global(self, message: dict):
        dead = []
        for ws in self.global_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        if dead:
            self.global_connections = [ws for ws in self.global_connections if ws not in dead]

room_manager = RoomConnectionManager()

@router.get("/rooms")
async def get_study_rooms():
    result = []
    # Seed mock active count + real live count
    mock_base_members = {
        "silent-library": 8,
        "code-sprint": 12,
        "night-owls": 5,
        "creative-flow": 6
    }
    for r in ROOMS_METADATA:
        live_count = len(room_manager.rooms.get(r["id"], []))
        total_members = mock_base_members.get(r["id"], 4) + live_count
        result.append({
            **r,
            "current_members": total_members,
            "active_now": live_count
        })
    return result

@router.websocket("/rooms/{room_id}/ws")
async def study_room_websocket(websocket: WebSocket, room_id: str):
    # Temporary guest/member identifier
    import uuid
    user_id = str(uuid.uuid4())[:8]
    participant = {
        "id": user_id,
        "name": f"Focus Pioneer #{user_id[:4]}",
        "avatar": "🧘",
        "status": "focusing",
        "joined_at": datetime.utcnow().isoformat()
    }
    
    await room_manager.connect_room(room_id, websocket, participant)
    try:
        # Initial greeting with room members
        current_members = [c["user"] for c in room_manager.rooms.get(room_id, [])]
        await websocket.send_json({
            "type": "room_state",
            "room_id": room_id,
            "you": participant,
            "members": current_members,
            "members_count": len(current_members)
        })
        
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "update_status":
                participant["status"] = data.get("status", "focusing")
                participant["task"] = data.get("task", "")
                await room_manager.broadcast_room(room_id, {
                    "type": "member_status_changed",
                    "user_id": participant["id"],
                    "status": participant["status"],
                    "task": participant["task"]
                })
            elif msg_type == "reaction":
                await room_manager.broadcast_room(room_id, {
                    "type": "reaction_sent",
                    "emoji": data.get("emoji", "🔥"),
                    "from_name": participant["name"],
                    "timestamp": datetime.utcnow().isoformat()
                })
            elif msg_type == "timer_sync":
                await room_manager.broadcast_room(room_id, {
                    "type": "timer_tick",
                    "remaining_seconds": data.get("remaining_seconds", 1500),
                    "is_running": data.get("is_running", True),
                    "synced_by": participant["name"]
                })
    except WebSocketDisconnect:
        leaving = room_manager.disconnect_room(room_id, websocket)
        if leaving:
            await room_manager.broadcast_room(room_id, {
                "type": "member_left",
                "user_id": leaving["id"],
                "members_count": len(room_manager.rooms.get(room_id, []))
            })
    except Exception:
        room_manager.disconnect_room(room_id, websocket)

@router.websocket("/ws")
async def global_websocket_endpoint(websocket: WebSocket):
    await room_manager.connect_global(websocket)
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to PhoneBalance Live Realtime Engine",
            "active_clients": len(room_manager.global_connections)
        })
        while True:
            data = await websocket.receive_json()
            await room_manager.broadcast_global({
                "type": data.get("type", "notification"),
                "payload": data.get("payload", {}),
                "timestamp": data.get("timestamp")
            })
    except WebSocketDisconnect:
        room_manager.disconnect_global(websocket)
    except Exception:
        room_manager.disconnect_global(websocket)
