"""Provider manager: dynamic resolution, health checks, and hot-swappable settings."""
import os
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Device, SystemSetting
from app.services.providers.base import ASRProvider, LLMProvider, TTSProvider
from app.services.providers.asr import OpenAIWhisperProvider, FasterWhisperProvider, MockASRProvider
from app.services.providers.llm import (
    OpenAILLMProvider, GeminiLLMProvider, OpenAICompatibleProvider, OllamaProvider, MockLLMProvider
)
from app.services.providers.tts import (
    EdgeTTSProvider, OpenAITTSProvider, PiperTTSProvider, MockTTSProvider
)

class ProviderManager:
    """Central registry and dynamic resolver for AI providers."""

    def __init__(self):
        pass

    @staticmethod
    def get_setting(db: Session, key: str, default: str = "") -> str:
        """Fetch setting from database with environment variable fallback."""
        row = db.query(SystemSetting).filter_by(key=key).first()
        if row and row.value:
            return row.value
        return os.getenv(key.upper(), default)

    @staticmethod
    def set_setting(db: Session, key: str, value: str):
        """Update or insert a setting in database."""
        row = db.query(SystemSetting).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            db.add(SystemSetting(key=key, value=value))
        db.commit()

    @classmethod
    def resolve_asr(cls, db: Session, device: Optional[Device] = None) -> ASRProvider:
        """Resolve effective ASR provider for device or global fallback."""
        provider_name = (device.asr_provider if device and device.asr_provider else None)
        if not provider_name:
            provider_name = cls.get_setting(db, "default_asr_provider", "openai").lower()

        if provider_name == "mock":
            return MockASRProvider()
        elif provider_name in ("faster-whisper", "faster_whisper"):
            return FasterWhisperProvider()
        else:
            api_key = cls.get_setting(db, "openai_api_key", os.getenv("OPENAI_API_KEY", ""))
            return OpenAIWhisperProvider(api_key=api_key)

    @classmethod
    def resolve_llm(cls, db: Session, device: Optional[Device] = None) -> tuple[LLMProvider, str]:
        """Resolve effective LLM provider and target model for device or assigned agent."""
        provider_name = None
        model_name = None

        if device and device.agent_id:
            from app.models import AIAgent
            agent = db.query(AIAgent).filter(AIAgent.id == device.agent_id).first()
            if agent:
                provider_name = agent.model_provider
                model_name = agent.model_name

        if not provider_name and device:
            provider_name = device.llm_provider
        if not model_name and device:
            model_name = device.llm_model

        if not provider_name:
            provider_name = cls.get_setting(db, "default_llm_provider", "gemini").lower()
        if not model_name:
            model_name = cls.get_setting(db, "default_llm_model", "gemini-1.5-flash")

        if provider_name == "mock":
            return MockLLMProvider(), model_name or "mock"
        elif provider_name == "gemini":
            api_key = cls.get_setting(db, "gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
            return GeminiLLMProvider(api_key=api_key, model=model_name or "gemini-1.5-flash"), model_name
        elif provider_name == "ollama":
            base_url = cls.get_setting(db, "ollama_base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
            return OllamaProvider(base_url=base_url, model=model_name or "llama3.2"), model_name
        elif provider_name in ("openai-compatible", "custom"):
            base_url = cls.get_setting(db, "openai_compatible_base_url", os.getenv("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:8000/v1"))
            api_key = cls.get_setting(db, "openai_compatible_api_key", os.getenv("OPENAI_COMPATIBLE_API_KEY", ""))
            return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model_name or "default"), model_name
        else:
            api_key = cls.get_setting(db, "openai_api_key", os.getenv("OPENAI_API_KEY", ""))
            return OpenAILLMProvider(api_key=api_key, model=model_name or "gpt-4o-mini"), model_name

    @classmethod
    def resolve_tts(cls, db: Session, device: Optional[Device] = None) -> tuple[TTSProvider, str]:
        """Resolve effective TTS provider and voice for device or assigned agent."""
        provider_name = None
        voice_name = None

        if device and device.agent_id:
            from app.models import AIAgent
            agent = db.query(AIAgent).filter(AIAgent.id == device.agent_id).first()
            if agent:
                provider_name = agent.tts_provider
                voice_name = agent.tts_voice

        if not provider_name and device:
            provider_name = device.tts_provider
        if not voice_name and device:
            voice_name = device.tts_voice

        if not provider_name:
            provider_name = cls.get_setting(db, "default_tts_provider", "edge-tts").lower()
        if not voice_name:
            voice_name = cls.get_setting(db, "default_tts_voice", "en-US-AriaNeural")


        if provider_name == "mock":
            return MockTTSProvider(), voice_name or "mock"
        elif provider_name == "openai":
            api_key = cls.get_setting(db, "openai_api_key", os.getenv("OPENAI_API_KEY", ""))
            return OpenAITTSProvider(api_key=api_key, voice=voice_name or "alloy"), voice_name
        elif provider_name == "piper":
            return PiperTTSProvider(), voice_name
        else:
            return EdgeTTSProvider(voice=voice_name or "en-US-AriaNeural"), voice_name

    @classmethod
    async def test_provider(cls, ptype: str, pname: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Run connectivity check against a provider."""
        pname = pname.lower()
        try:
            if ptype == "asr":
                if pname == "openai":
                    provider = OpenAIWhisperProvider(api_key=options.get("api_key"))
                    return await provider.health_check()
                elif pname in ("faster-whisper", "faster_whisper"):
                    provider = FasterWhisperProvider(model_size=options.get("model", "base"))
                    return await provider.health_check()
                elif pname == "mock":
                    return await MockASRProvider().health_check()
                return {"ok": False, "error": f"Unknown ASR provider: {pname}"}

            elif ptype == "llm":
                if pname == "openai":
                    provider = OpenAILLMProvider(api_key=options.get("api_key"), model=options.get("model", "gpt-4o-mini"))
                    return await provider.health_check()
                elif pname == "gemini":
                    provider = GeminiLLMProvider(api_key=options.get("api_key"), model=options.get("model", "gemini-1.5-flash"))
                    return await provider.health_check()
                elif pname == "ollama":
                    provider = OllamaProvider(base_url=options.get("base_url", "http://localhost:11434"), model=options.get("model", "llama3.2"))
                    return await provider.health_check()
                elif pname in ("openai-compatible", "custom"):
                    provider = OpenAICompatibleProvider(
                        base_url=options.get("base_url", "http://localhost:8000/v1"),
                        api_key=options.get("api_key")
                    )
                    return await provider.health_check()
                elif pname == "mock":
                    return await MockLLMProvider().health_check()
                return {"ok": False, "error": f"Unknown LLM provider: {pname}"}

            elif ptype == "tts":
                if pname == "edge-tts":
                    provider = EdgeTTSProvider(voice=options.get("voice", "en-US-AriaNeural"))
                    return await provider.health_check()
                elif pname == "openai":
                    provider = OpenAITTSProvider(api_key=options.get("api_key"), voice=options.get("voice", "alloy"))
                    return await provider.health_check()
                elif pname == "piper":
                    provider = PiperTTSProvider(model_path=options.get("model_path"))
                    return await provider.health_check()
                elif pname == "mock":
                    return await MockTTSProvider().health_check()
                return {"ok": False, "error": f"Unknown TTS provider: {pname}"}

            return {"ok": False, "error": f"Invalid provider type: {ptype}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
