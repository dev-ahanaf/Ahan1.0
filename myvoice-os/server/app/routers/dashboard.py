"""Admin dashboard API router."""
import secrets
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Device
from app.schemas import SettingsBody, AskBody
from app.auth import admin, digest
from app.services.llm import answer_question, fallback_profile

router = APIRouter(prefix="/api/admin", tags=["Dashboard"])

def is_device_online(last_seen_iso: str | None) -> bool:
    """Check if device has reported heartbeat within the last 120 seconds."""
    if not last_seen_iso:
        return False
    try:
        dt = datetime.fromisoformat(last_seen_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = (datetime.now(timezone.utc) - dt).total_seconds()
        return diff < 120
    except Exception:
        return False

@router.get("/devices")
def list_devices(_: bool = Depends(admin), db: Session = Depends(get_db)):
    """List all registered devices with online status and telemetry."""
    from datetime import timedelta
    from app.routers.pairing import ACTIVE_PAIR_CODES
    from app.auth import code_digest
    rows = db.query(Device).order_by(Device.created_at.desc()).all()
    device_list = []
    now = datetime.now(timezone.utc)
    for r in rows:
        d = r.to_dict()
        d["online"] = is_device_online(r.last_seen)
        if not r.paired:
            code = ACTIVE_PAIR_CODES.get(r.id)
            if not code or not r.pair_expires or datetime.fromisoformat(r.pair_expires) < now:
                code = str(secrets.randbelow(900000) + 100000)
                ACTIVE_PAIR_CODES[r.id] = code
                r.pair_hash = code_digest(code)
                r.pair_expires = (now + timedelta(minutes=15)).isoformat()
                db.commit()
            d["pair_code"] = code
        device_list.append(d)
    return {"devices": device_list}

@router.post("/devices/{device_id}/settings")
def update_settings(
    device_id: str,
    body: SettingsBody,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Update per-device configuration and increment config_version."""
    try:
        ZoneInfo(body.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid IANA timezone, e.g. Asia/Dhaka")
        
    device = db.query(Device).filter(Device.id == device_id.upper(), Device.paired == 1).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paired device not found")
        
    device.name = body.name
    device.city = body.city
    device.latitude = body.latitude
    device.longitude = body.longitude
    device.timezone = body.timezone
    device.language = body.language
    device.oled_brightness = body.oled_brightness
    device.idle_display_mode = body.idle_display_mode
    device.clock_format = body.clock_format
    device.speaker_volume = body.speaker_volume
    device.mic_gain = body.mic_gain
    device.wake_mode = body.wake_mode
    device.weather_enabled = 1 if body.weather_enabled else 0
    device.search_enabled = 1 if body.search_enabled else 0
    device.timers_enabled = 1 if body.timers_enabled else 0
    device.system_prompt = body.system_prompt
    device.assistant_name = body.assistant_name or "MyVoice"
    device.personality = body.personality
    device.history_length = body.history_length
    device.asr_provider = body.asr_provider
    device.llm_provider = body.llm_provider
    device.llm_model = body.llm_model
    device.tts_provider = body.tts_provider
    device.tts_voice = body.tts_voice
    device.vad_mode = body.vad_mode
    if body.agent_id is not None:
        device.agent_id = body.agent_id
    
    # Monotonically increment configuration version to trigger device sync

    device.config_version += 1
    db.commit()
    
    # Push config_update to active WebSocket session if connected
    from app.routers.ws_device import ACTIVE_SESSIONS
    if device_id.upper() in ACTIVE_SESSIONS:
        ws_sess = ACTIVE_SESSIONS[device_id.upper()]
        try:
            import asyncio, json
            asyncio.create_task(ws_sess.websocket.send_text(json.dumps({
                "type": "config_update",
                "config": {
                    "language": device.language,
                    "speaker_volume": device.speaker_volume,
                    "mic_gain": device.mic_gain,
                    "idle_display_mode": device.idle_display_mode,
                    "clock_format": device.clock_format,
                    "assistant_name": device.assistant_name
                },
                "config_version": device.config_version
            })))
        except Exception:
            pass

    return {"ok": True, "config_version": device.config_version}

@router.post("/devices/{device_id}/rotate-token")
def rotate_token(
    device_id: str,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Rotate authentication token for a device."""
    device = db.query(Device).filter(Device.id == device_id.upper()).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
        
    new_token = secrets.token_urlsafe(32)
    device.token_hash = digest(new_token)
    device.revoked = 0
    db.commit()
    
    return {"ok": True, "device_id": device.id, "new_token": new_token}

@router.post("/devices/{device_id}/revoke")
def revoke_device(
    device_id: str,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Revoke credentials for a device."""
    device = db.query(Device).filter(Device.id == device_id.upper()).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
        
    device.revoked = 1
    device.paired = 0
    db.commit()

    from app.routers.ws_device import ACTIVE_SESSIONS
    if device.id in ACTIVE_SESSIONS:
        try:
            import asyncio
            asyncio.create_task(ACTIVE_SESSIONS[device.id].websocket.close(code=4003))
        except Exception:
            pass

    return {"ok": True, "revoked": True, "device_id": device.id}

@router.get("/providers")
def get_providers(_: bool = Depends(admin), db: Session = Depends(get_db)):
    """List available AI providers and global configurations with masked secrets."""
    from app.services.providers.manager import ProviderManager
    import os

    def mask(val: str) -> str:
        if not val:
            return ""
        if len(val) <= 8:
            return "********"
        return val[:3] + "..." + val[-4:]

    openai_key = ProviderManager.get_setting(db, "openai_api_key", os.getenv("OPENAI_API_KEY", ""))
    gemini_key = ProviderManager.get_setting(db, "gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
    compat_key = ProviderManager.get_setting(db, "openai_compatible_api_key", os.getenv("OPENAI_COMPATIBLE_API_KEY", ""))

    return {
        "available_asr": [
            {"id": "gemini", "name": "Google Gemini ASR (Recommended)", "description": "Direct multimodal speech recognition via Gemini API"},
            {"id": "groq", "name": "Groq Whisper (Ultra-Fast)", "description": "High-speed Whisper cloud transcription"},
            {"id": "openai", "name": "OpenAI Whisper", "description": "Cloud neural speech recognition"},
            {"id": "faster-whisper", "name": "Faster-Whisper (Local)", "description": "CTranslate2 local transcription"},
            {"id": "mock", "name": "Mock ASR", "description": "Deterministic testing backend"}
        ],
        "available_llm": [
            {"id": "openai", "name": "OpenAI", "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]},
            {"id": "gemini", "name": "Google Gemini", "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]},
            {"id": "ollama", "name": "Ollama (Local)", "models": ["llama3.2", "mistral", "gemma2", "qwen2.5"]},
            {"id": "openai-compatible", "name": "OpenAI-Compatible", "models": ["default"]},
            {"id": "mock", "name": "Mock LLM", "models": ["mock"]}
        ],
        "available_tts": [
            {"id": "edge-tts", "name": "Microsoft Edge-TTS", "voices": ["en-US-AriaNeural", "en-US-GuyNeural", "bn-BD-NabanitaNeural", "bn-BD-PradeepNeural"]},
            {"id": "openai", "name": "OpenAI Speech", "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]},
            {"id": "piper", "name": "Piper (Local)", "voices": ["default"]},
            {"id": "mock", "name": "Mock TTS", "voices": ["mock"]}
        ],
        "defaults": {
            "default_asr_provider": ProviderManager.get_setting(db, "default_asr_provider", "openai"),
            "default_llm_provider": ProviderManager.get_setting(db, "default_llm_provider", "openai"),
            "default_llm_model": ProviderManager.get_setting(db, "default_llm_model", "gpt-4o-mini"),
            "default_tts_provider": ProviderManager.get_setting(db, "default_tts_provider", "edge-tts"),
            "default_tts_voice": ProviderManager.get_setting(db, "default_tts_voice", "en-US-AriaNeural"),
            "ollama_base_url": ProviderManager.get_setting(db, "ollama_base_url", "http://localhost:11434"),
            "openai_compatible_base_url": ProviderManager.get_setting(db, "openai_compatible_base_url", "http://localhost:8000/v1"),
            "openai_api_key_masked": mask(openai_key),
            "gemini_api_key_masked": mask(gemini_key),
            "openai_compatible_api_key_masked": mask(compat_key),
            "has_openai_key": bool(openai_key),
            "has_gemini_key": bool(gemini_key),
            "has_compat_key": bool(compat_key)
        }
    }

@router.post("/providers")
def update_providers(body: dict, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Update global AI provider preferences and write-only API keys."""
    from app.services.providers.manager import ProviderManager

    allowed_keys = [
        "default_asr_provider", "default_llm_provider", "default_llm_model",
        "default_tts_provider", "default_tts_voice", "ollama_base_url",
        "openai_compatible_base_url", "openai_api_key", "gemini_api_key",
        "openai_compatible_api_key"
    ]

    for k, v in body.items():
        if k in allowed_keys and v is not None:
            # Only update secret keys if non-empty string is provided
            if k.endswith("_key") and (not v or v.startswith("***")):
                continue
            ProviderManager.set_setting(db, k, str(v).strip())

    return {"ok": True, "message": "Global provider configurations updated"}

@router.post("/providers/test")
async def test_provider_endpoint(body: dict, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Test connectivity and credentials for an AI provider."""
    from app.services.providers.manager import ProviderManager
    import os

    ptype = body.get("provider_type", "")
    pname = body.get("provider_name", "")
    options = dict(body)

    # If api_key is missing or placeholder, resolve from database / environment
    if not options.get("api_key") or options.get("api_key").startswith("***"):
        if pname == "openai":
            options["api_key"] = ProviderManager.get_setting(db, "openai_api_key", os.getenv("OPENAI_API_KEY", ""))
        elif pname == "gemini":
            options["api_key"] = ProviderManager.get_setting(db, "gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
        elif pname in ("openai-compatible", "custom"):
            options["api_key"] = ProviderManager.get_setting(db, "openai_compatible_api_key", os.getenv("OPENAI_COMPATIBLE_API_KEY", ""))

    result = await ProviderManager.test_provider(ptype, pname, options)
    return result

@router.get("/conversations")
def list_conversations(
    q: str = "",
    device_id: str = "",
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Search and list stored conversation sessions."""
    from app.services.memory import search_conversations
    return {"conversations": search_conversations(db, device_id=device_id or None, query=q)}

@router.get("/conversations/{conv_id}/messages")
def list_messages(
    conv_id: str,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Retrieve full transcript messages for a conversation session."""
    from app.services.memory import get_conversation_messages
    return {"messages": get_conversation_messages(db, conv_id)}

@router.delete("/conversations/{conv_id}")
def delete_conversation_endpoint(
    conv_id: str,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Delete a conversation session and all its messages."""
    from app.services.memory import delete_conversation
    ok = delete_conversation(db, conv_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return {"ok": True, "id": conv_id}

@router.get("/sessions")
def list_active_sessions(_: bool = Depends(admin)):
    """Monitor real-time connected devices, state machines, and dropped frames."""
    from app.routers.ws_device import ACTIVE_SESSIONS
    return {
        "sessions": [s.to_dict() for s in ACTIVE_SESSIONS.values()]
    }

@router.post("/ask")
async def ask_admin(
    body: AskBody,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Test assistant processing via dashboard command interface."""
    profile = None
    if body.device_id:
        dev = db.query(Device).filter(Device.id == body.device_id.upper()).first()
        if dev:
            profile = dev.to_dict()
    if profile is None:
        profile = fallback_profile()
        
    return {"answer": await answer_question(body.text, profile)}


# Phase 3 Tool & Skill Management Endpoints
@router.get("/tools")
def list_available_tools(_: bool = Depends(admin)):
    """List all registered tools with schemas and descriptions."""
    from app.services.tools import tool_registry
    tools = tool_registry.get_all_tools()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
                "timeout_seconds": t.timeout_seconds,
            }
            for t in tools
        ]
    }


@router.post("/tools/test")
async def test_tool_execution(
    payload: dict,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Interactively test any tool directly from the dashboard."""
    from app.services.tools import tool_registry
    from app.services.tools.base import ToolContext
    tool_name = payload.get("tool_name")
    args = payload.get("arguments", {})
    device_id = payload.get("device_id", "SIMULATOR")

    device = db.query(Device).filter(Device.id == device_id.upper()).first()
    context = ToolContext(
        device_id=device_id,
        city=device.city if device else "Dhaka",
        latitude=device.latitude if device else 23.8103,
        longitude=device.longitude if device else 90.4125,
        timezone=device.timezone if device else "Asia/Dhaka",
        speaker_volume=device.speaker_volume if device else 80,
        oled_brightness=device.oled_brightness if device else 128
    )

    result = await tool_registry.execute_tool(tool_name, args, context, db=db)
    return {
        "success": result.success,
        "data": result.data,
        "voice_summary": result.voice_summary,
        "display_data": result.display_data,
        "error": result.error
    }


@router.post("/devices/{device_id}/tools")
def update_device_tools(
    device_id: str,
    payload: dict,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Update enabled tools for a specific device."""
    device = db.query(Device).filter(Device.id == device_id.upper()).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")

    tools_list = payload.get("tools", [])
    if isinstance(tools_list, list):
        device.tools_enabled = ",".join(tools_list)
    else:
        device.tools_enabled = str(tools_list)

    device.config_version += 1
    db.commit()

    return {"status": "success", "tools_enabled": device.tools_enabled}


# Phase 3 Timers & Alarms Management Endpoints
@router.get("/timers")
def list_timers(_: bool = Depends(admin), db: Session = Depends(get_db)):
    """List all timers across devices."""
    from app.models import Timer
    timers = db.query(Timer).order_by(Timer.created_at.desc()).all()
    return {"timers": [t.to_dict() for t in timers]}


@router.delete("/timers/{timer_id}")
def cancel_timer_admin(timer_id: str, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Cancel and delete a timer."""
    from app.models import Timer
    t = db.query(Timer).filter(Timer.id == timer_id).first()
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Timer not found")
    t.status = "cancelled"
    db.commit()
    return {"status": "success", "id": timer_id}


@router.get("/alarms")
def list_alarms(_: bool = Depends(admin), db: Session = Depends(get_db)):
    """List all alarms across devices."""
    from app.models import Alarm
    alarms = db.query(Alarm).order_by(Alarm.created_at.desc()).all()
    return {"alarms": [a.to_dict() for a in alarms]}


@router.post("/alarms")
def create_alarm_admin(payload: dict, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Create a new alarm for a device."""
    from app.models import Alarm
    import uuid
    device_id = payload.get("device_id", "").upper()
    time_str = payload.get("time_str", "08:00")
    label = payload.get("label", "Alarm")

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")

    alarm_id = str(uuid.uuid4())
    alarm = Alarm(
        id=alarm_id,
        device_id=device_id,
        time_str=time_str,
        label=label,
        timezone=device.timezone,
        repeat_days=payload.get("repeat_days", ""),
        created_at=datetime.now(timezone.utc).isoformat(),
        next_trigger_at=datetime.now(timezone.utc).isoformat(),
        status="active"
    )
    db.add(alarm)
    db.commit()
    return {"status": "success", "alarm": alarm.to_dict()}


@router.delete("/alarms/{alarm_id}")
def cancel_alarm_admin(alarm_id: str, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Cancel and delete an alarm."""
    from app.models import Alarm
    a = db.query(Alarm).filter(Alarm.id == alarm_id).first()
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alarm not found")
    a.status = "cancelled"
    db.commit()
    return {"status": "success", "id": alarm_id}


# Phase 3 Remote Actions & Telemetry Endpoints
@router.post("/devices/{device_id}/reboot")
async def reboot_device_admin(device_id: str, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Send remote reboot command to an active device."""
    from app.routers.ws_device import ACTIVE_SESSIONS
    from app.models import AuditLog
    import uuid
    import json
    session = ACTIVE_SESSIONS.get(device_id.upper())
    dispatched = False
    if session and session.websocket:
        try:
            await session.websocket.send_text(json.dumps({"type": "reboot"}))
            dispatched = True
        except Exception:
            pass

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user="admin",
        action="reboot_device",
        target=device_id.upper(),
        details=json.dumps({"dispatched": dispatched})
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "action": "reboot", "device_id": device_id, "dispatched": dispatched}


@router.post("/devices/{device_id}/reset_wifi")
@router.post("/devices/{device_id}/reset-wifi")
async def reset_wifi_device_admin(device_id: str, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Send clear Wi-Fi credentials command to an active device."""
    from app.routers.ws_device import ACTIVE_SESSIONS
    from app.models import AuditLog
    import uuid
    import json
    session = ACTIVE_SESSIONS.get(device_id.upper())
    dispatched = False
    if session and session.websocket:
        try:
            await session.websocket.send_text(json.dumps({"type": "reset_wifi"}))
            dispatched = True
        except Exception:
            pass

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user="admin",
        action="reset_wifi",
        target=device_id.upper(),
        details=json.dumps({"dispatched": dispatched})
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "action": "reset_wifi", "device_id": device_id, "dispatched": dispatched}


@router.post("/devices/{device_id}/revoke")
async def revoke_device_admin(device_id: str, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Revoke a device authorization and terminate active WebSocket session."""
    from app.routers.ws_device import ACTIVE_SESSIONS
    from app.models import AuditLog
    import uuid
    import json
    import secrets
    device = db.query(Device).filter(Device.id == device_id.upper()).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")

    device.revoked = 1
    device.token_hash = "REVOKED_" + secrets.token_hex(16)
    db.commit()

    # Close active WebSocket if present
    session = ACTIVE_SESSIONS.get(device_id.upper())
    if session and session.websocket:
        try:
            await session.websocket.close(code=4003, reason="Device Revoked")
        except Exception:
            pass

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user="admin",
        action="revoke_device",
        target=device_id.upper(),
        details=json.dumps({"status": "revoked"})
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "device_id": device_id, "revoked": True}


@router.get("/devices/{device_id}/telemetry")
def get_device_telemetry(device_id: str, _: bool = Depends(admin), db: Session = Depends(get_db)):
    """Get latest telemetry history for a device."""
    from app.models import DeviceTelemetry
    rows = db.query(DeviceTelemetry).filter(
        DeviceTelemetry.device_id == device_id.upper()
    ).order_by(DeviceTelemetry.created_at.desc()).limit(50).all()
    return {"telemetry": [r.to_dict() for r in rows]}


@router.get("/audit_logs")
@router.get("/audit-logs")
def get_audit_logs(_: bool = Depends(admin), db: Session = Depends(get_db)):
    """Retrieve administrative action audit logs."""
    from app.models import AuditLog
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    dicts = [l.to_dict() for l in logs]
    return {"audit_logs": dicts, "logs": dicts}


