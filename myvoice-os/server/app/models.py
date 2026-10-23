"""SQLAlchemy models for MyVoice OS."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text
from app.db import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(32), primary_key=True, index=True) # MAC address
    name = Column(String(100), nullable=False, default="My ESP32")
    token_hash = Column(String(64), nullable=False)
    pair_hash = Column(String(64), nullable=True)
    pair_expires = Column(String(64), nullable=True)
    paired = Column(Integer, nullable=False, default=0)
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    last_seen = Column(String(64), nullable=True)
    firmware = Column(String(32), nullable=False, default="0.1.0")
    
    # Geolocation and timezone
    city = Column(String(80), nullable=False, default="Dhaka")
    latitude = Column(Float, nullable=False, default=23.8103)
    longitude = Column(Float, nullable=False, default=90.4125)
    timezone = Column(String(64), nullable=False, default="Asia/Dhaka")

    # Phase 1 Per-device configuration
    config_version = Column(Integer, nullable=False, default=1)
    language = Column(String(16), nullable=False, default="en")
    oled_brightness = Column(Integer, nullable=False, default=128)
    idle_display_mode = Column(String(32), nullable=False, default="clock")
    clock_format = Column(String(8), nullable=False, default="24h")
    speaker_volume = Column(Integer, nullable=False, default=80)
    mic_gain = Column(Integer, nullable=False, default=50)
    wake_mode = Column(String(32), nullable=False, default="button")
    weather_enabled = Column(Integer, nullable=False, default=1)
    search_enabled = Column(Integer, nullable=False, default=1)
    timers_enabled = Column(Integer, nullable=False, default=1)
    # Phase 2 AI and Conversation settings
    system_prompt = Column(Text, nullable=True)
    assistant_name = Column(String(64), nullable=False, default="MyVoice")
    personality = Column(String(128), nullable=True, default="helpful, concise voice assistant")
    history_length = Column(Integer, nullable=False, default=6)
    asr_provider = Column(String(32), nullable=True)
    llm_provider = Column(String(32), nullable=True)
    llm_model = Column(String(64), nullable=True)
    tts_provider = Column(String(32), nullable=True)
    tts_voice = Column(String(64), nullable=True)
    vad_mode = Column(String(16), nullable=False, default="manual")
    revoked = Column(Integer, nullable=False, default=0)
    tools_enabled = Column(String(255), nullable=False, default="clock,weather,search,timer,alarm,device_settings")
    agent_id = Column(String(36), nullable=True)

    def to_dict(self):
        """Convert model instance to standard dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "paired": bool(self.paired),
            "created_at": self.created_at,
            "last_seen": self.last_seen,
            "firmware": self.firmware,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "config_version": self.config_version,
            "language": self.language,
            "oled_brightness": self.oled_brightness,
            "idle_display_mode": self.idle_display_mode,
            "clock_format": self.clock_format,
            "speaker_volume": self.speaker_volume,
            "mic_gain": self.mic_gain,
            "wake_mode": self.wake_mode,
            "weather_enabled": bool(self.weather_enabled),
            "search_enabled": bool(self.search_enabled),
            "timers_enabled": bool(self.timers_enabled),
            "system_prompt": self.system_prompt,
            "assistant_name": self.assistant_name,
            "personality": self.personality,
            "history_length": self.history_length,
            "asr_provider": self.asr_provider,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "tts_provider": self.tts_provider,
            "tts_voice": self.tts_voice,
            "vad_mode": self.vad_mode,
            "revoked": bool(self.revoked),
            "tools_enabled": self.tools_enabled or "clock,weather,search,timer,alarm,device_settings",
            "agent_id": self.agent_id,
        }


class AIAgent(Base):
    __tablename__ = "ai_agents"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, default="Falcon Assistant")
    avatar = Column(String(255), nullable=False, default="🦅")
    description = Column(Text, nullable=True, default="Primary Falcon AI Voice Agent")
    personality = Column(String(255), nullable=False, default="helpful, concise voice assistant")
    system_prompt = Column(Text, nullable=True, default="You are Falcon AI, an intelligent, concise voice assistant. Keep answers under 50 words.")
    language = Column(String(16), nullable=False, default="en")
    model_provider = Column(String(32), nullable=False, default="gemini")
    model_name = Column(String(64), nullable=False, default="gemini-1.5-flash")
    tts_provider = Column(String(32), nullable=False, default="edge-tts")
    tts_voice = Column(String(64), nullable=False, default="en-US-AriaNeural")
    response_style = Column(String(32), nullable=False, default="concise")
    temperature = Column(Float, nullable=False, default=0.7)
    tools_enabled = Column(String(255), nullable=False, default="clock,weather,search,timer,alarm,device_settings")
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar,
            "description": self.description,
            "personality": self.personality,
            "system_prompt": self.system_prompt,
            "language": self.language,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "tts_provider": self.tts_provider,
            "tts_voice": self.tts_voice,
            "response_style": self.response_style,
            "temperature": self.temperature,
            "tools_enabled": self.tools_enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(128), unique=True, nullable=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="admin")
    full_name = Column(String(100), nullable=True, default="Administrator")
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "is_active": bool(self.is_active),
            "created_at": self.created_at,
        }



class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, index=True)
    device_id = Column(String(32), index=True, nullable=False)
    title = Column(String(200), nullable=False, default="Voice Chat")
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self, include_messages=False):
        res = {
            "id": self.id,
            "device_id": self.device_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return res


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), index=True, nullable=False)
    device_id = Column(String(32), index=True, nullable=False)
    role = Column(String(16), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    latency_ms = Column(Integer, nullable=True)
    provider_info = Column(Text, nullable=True)  # JSON metadata
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "device_id": self.device_id,
            "role": self.role,
            "content": self.content,
            "latency_ms": self.latency_ms,
            "provider_info": self.provider_info,
            "created_at": self.created_at,
        }


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at,
        }


class Timer(Base):
    __tablename__ = "timers"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(32), index=True, nullable=False)
    label = Column(String(100), nullable=False, default="Timer")
    duration_seconds = Column(Integer, nullable=False)
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    expires_at = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active, completed, cancelled
    alert_acknowledged = Column(Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "label": self.label,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "alert_acknowledged": bool(self.alert_acknowledged),
        }


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(32), index=True, nullable=False)
    time_str = Column(String(10), nullable=False)  # HH:MM format
    label = Column(String(100), nullable=False, default="Alarm")
    timezone = Column(String(64), nullable=False, default="Asia/Dhaka")
    repeat_days = Column(String(64), nullable=False, default="")  # e.g. "mon,tue,wed"
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    next_trigger_at = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active, dismissed, cancelled

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "time_str": self.time_str,
            "label": self.label,
            "timezone": self.timezone,
            "repeat_days": self.repeat_days,
            "created_at": self.created_at,
            "next_trigger_at": self.next_trigger_at,
            "status": self.status,
        }


class FirmwareRelease(Base):
    __tablename__ = "firmware_releases"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    version = Column(String(32), unique=True, nullable=False, index=True)
    target_hardware = Column(String(32), nullable=False, default="esp32dev")
    file_path = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    release_notes = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    is_active = Column(Integer, nullable=False, default=1)

    def to_dict(self):
        return {
            "id": self.id,
            "version": self.version,
            "target_hardware": self.target_hardware,
            "file_size": self.file_size,
            "sha256": self.sha256,
            "release_notes": self.release_notes,
            "created_at": self.created_at,
            "is_active": bool(self.is_active),
        }


class DeviceTelemetry(Base):
    __tablename__ = "device_telemetry"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(32), index=True, nullable=False)
    rssi = Column(Integer, nullable=True)
    free_heap = Column(Integer, nullable=True)
    min_free_heap = Column(Integer, nullable=True)
    uptime_s = Column(Integer, nullable=True)
    dropped_frames = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "device_id": self.device_id,
            "rssi": self.rssi,
            "free_heap": self.free_heap,
            "min_free_heap": self.min_free_heap,
            "uptime_s": self.uptime_s,
            "dropped_frames": self.dropped_frames,
            "error_count": self.error_count,
            "created_at": self.created_at,
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user = Column(String(64), nullable=False, default="admin")
    action = Column(String(64), nullable=False)
    target = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(String(64), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user,
            "action": self.action,
            "target": self.target,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at,
        }

