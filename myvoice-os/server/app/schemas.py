"""Pydantic schemas for request validation and response serialization."""
from typing import Optional, Literal
from pydantic import BaseModel, Field

class BootstrapBody(BaseModel):
    device_id: str = Field(pattern=r"^[0-9A-Fa-f:]{12,17}$")
    firmware: str = Field(default="0.1.0", max_length=32)

class PairBody(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    name: str = Field(default="My ESP32", min_length=1, max_length=50)

class SettingsBody(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    city: str = Field(default="Dhaka", min_length=1, max_length=80)
    latitude: float = Field(default=23.8103, ge=-90.0, le=90.0)
    longitude: float = Field(default=90.4125, ge=-180.0, le=180.0)
    timezone: str = Field(default="Asia/Dhaka", max_length=64)
    
    # Phase 1 Optional per-device configuration with defaults
    language: str = Field(default="en", max_length=16)
    oled_brightness: int = Field(default=128, ge=0, le=255)
    idle_display_mode: Literal["clock", "weather", "blank"] = "clock"
    clock_format: Literal["12h", "24h"] = "24h"
    speaker_volume: int = Field(default=80, ge=0, le=100)
    mic_gain: int = Field(default=50, ge=0, le=100)
    wake_mode: Literal["button", "wakeword"] = "button"
    weather_enabled: bool = True
    search_enabled: bool = True
    timers_enabled: bool = True
    
    # Phase 2 Per-device AI overrides
    system_prompt: Optional[str] = None
    assistant_name: Optional[str] = Field(default="MyVoice", max_length=64)
    personality: Optional[str] = Field(default="helpful, concise voice assistant", max_length=128)
    history_length: int = Field(default=6, ge=0, le=50)
    asr_provider: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_voice: Optional[str] = None
    vad_mode: Literal["manual", "vad"] = "manual"

class AskBody(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    device_id: Optional[str] = None

class HeartbeatBody(BaseModel):
    free_heap: Optional[int] = None
    wifi_rssi: Optional[int] = None

class DeviceConfigOut(BaseModel):
    config_version: int
    name: str
    timezone: str
    language: str
    city: str
    latitude: float
    longitude: float
    oled_brightness: int
    idle_display_mode: str
    clock_format: str
    speaker_volume: int
    mic_gain: int
    wake_mode: str
    weather_enabled: bool
    search_enabled: bool
    timers_enabled: bool
    system_prompt: Optional[str] = None
    assistant_name: str = "MyVoice"
    personality: Optional[str] = None
    history_length: int = 6
    asr_provider: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_voice: Optional[str] = None
    vad_mode: str = "manual"

class ProviderTestBody(BaseModel):
    provider_type: Literal["asr", "llm", "tts"]
    provider_name: str
    model: Optional[str] = None
    voice: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class GlobalAISettingsBody(BaseModel):
    default_asr_provider: Optional[str] = None
    default_llm_provider: Optional[str] = None
    default_tts_provider: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    openai_compatible_base_url: Optional[str] = None
    openai_compatible_api_key: Optional[str] = None
    default_llm_model: Optional[str] = None
    default_tts_voice: Optional[str] = None
    default_language: Optional[str] = None

class MessageOut(BaseModel):
    id: str
    conversation_id: str
    device_id: str
    role: str
    content: str
    latency_ms: Optional[int] = None
    provider_info: Optional[str] = None
    created_at: str

class ConversationOut(BaseModel):
    id: str
    device_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
