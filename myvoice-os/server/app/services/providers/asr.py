"""ASR Provider implementations: OpenAI Whisper, Faster-Whisper, and Mock."""
import os
from typing import Dict, Any, Optional
import httpx
from app.services.providers.base import ASRProvider
from app.services.audio_utils import pcm16_to_wav

class OpenAIWhisperProvider(ASRProvider):
    """Speech transcription using OpenAI Whisper API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Configure OPENAI_API_KEY in server settings.")

        # Ensure WAV format header exists
        if not audio_bytes.startswith(b"RIFF"):
            wav_data = pcm16_to_wav(audio_bytes, sample_rate=16000, channels=1)
        else:
            wav_data = audio_bytes

        data = {"model": self.model}
        if language and language != "auto":
            data["language"] = language

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("speech.wav", wav_data, "audio/wav")},
                data=data
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("text", "").strip()

    async def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"ok": False, "provider": "openai", "error": "API key not configured"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                if resp.status_code == 200:
                    return {"ok": True, "provider": "openai", "model": self.model}
                return {"ok": False, "provider": "openai", "error": f"HTTP {resp.status_code}: {resp.text[:120]}"}
        except Exception as exc:
            return {"ok": False, "provider": "openai", "error": str(exc)}


class FasterWhisperProvider(ASRProvider):
    """Local ASR using faster-whisper CTranslate2 models."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            except ImportError:
                raise RuntimeError(
                    "faster-whisper is not installed. Install via 'pip install faster-whisper' "
                    "or select OpenAI Whisper provider."
                )
        return self._model

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        model = self._get_model()
        import io
        if not audio_bytes.startswith(b"RIFF"):
            audio_bytes = pcm16_to_wav(audio_bytes, sample_rate=16000, channels=1)
        buf = io.BytesIO(audio_bytes)
        segments, _ = model.transcribe(buf, language=language if language != "auto" else None)
        text = " ".join([segment.text for segment in segments]).strip()
        return text

    async def health_check(self) -> Dict[str, Any]:
        try:
            from faster_whisper import WhisperModel  # noqa: F401
            return {"ok": True, "provider": "faster-whisper", "model": self.model_size, "installed": True}
        except ImportError:
            return {
                "ok": False,
                "provider": "faster-whisper",
                "error": "faster-whisper not installed. Server hardware requirements: CPU with AVX or CUDA GPU."
            }


class GroqWhisperProvider(ASRProvider):
    """Ultra-fast Whisper transcription using Groq Cloud API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-large-v3-turbo"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if not self.api_key:
            raise ValueError("Groq API key is missing. Configure GROQ_API_KEY in server settings.")

        if not audio_bytes.startswith(b"RIFF"):
            wav_data = pcm16_to_wav(audio_bytes, sample_rate=16000, channels=1)
        else:
            wav_data = audio_bytes

        data = {"model": self.model}
        if language and language not in ("auto", "en-US", "en-GB"):
            data["language"] = language[:2]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("speech.wav", wav_data, "audio/wav")},
                data=data
            )
            resp.raise_for_status()
            payload = resp.json()
            return payload.get("text", "").strip()

    async def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"ok": False, "provider": "groq", "error": "Groq API key not configured"}
        return {"ok": True, "provider": "groq", "model": self.model}


class GeminiASRProvider(ASRProvider):
    """Speech transcription using Google Gemini multimodal audio recognition."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if not self.api_key:
            raise ValueError("Gemini API key is missing. Configure GEMINI_API_KEY in server settings.")

        import base64
        if not audio_bytes.startswith(b"RIFF"):
            wav_data = pcm16_to_wav(audio_bytes, sample_rate=16000, channels=1)
        else:
            wav_data = audio_bytes

        b64_audio = base64.b64encode(wav_data).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        prompt = (
            f"Transcribe this user speech audio verbatim. "
            f"Language: {language}. "
            f"Return ONLY the exact transcribed text words, with no explanations, no quotes, and no extra text."
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "audio/wav",
                            "data": b64_audio
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 200
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
            return ""

    async def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"ok": False, "provider": "gemini", "error": "Gemini API key not configured"}
        return {"ok": True, "provider": "gemini", "model": self.model}


class MockASRProvider(ASRProvider):
    """Deterministic fallback ASR provider with helpful onboarding message."""

    def __init__(self, fixed_text: Optional[str] = None):
        self.fixed_text = fixed_text

    async def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if self.fixed_text is not None:
            return self.fixed_text
        if len(audio_bytes) < 1600:
            return ""
        return "Configure your API key in the Falcon Console settings to enable real AI voice conversation."

    async def health_check(self) -> Dict[str, Any]:
        return {"ok": True, "provider": "mock", "status": "active"}
