"""TTS Provider implementations: Edge-TTS, OpenAI Speech, Piper, and Mock."""
import os
import shutil
from typing import AsyncGenerator, Dict, Any, Optional
import httpx
from app.services.providers.base import TTSProvider
from app.services.audio_utils import generate_pcm16_tone, resample_pcm16, wav_to_pcm16

class EdgeTTSProvider(TTSProvider):
    """Free, high-fidelity Microsoft Edge neural TTS supporting English and Bangla."""

    def __init__(self, voice: str = "en-US-AriaNeural"):
        self.voice = voice

    def _resolve_voice(self, voice: Optional[str], language: str) -> str:
        if voice:
            return voice
        if language in ("bn", "bengali", "bn-BD"):
            return "bn-BD-NabanitaNeural"
        return self.voice

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "en"
    ) -> AsyncGenerator[bytes, None]:
        import edge_tts
        import miniaudio

        selected_voice = self._resolve_voice(voice, language)
        communicate = edge_tts.Communicate(text, voice=selected_voice)

        mp3_buffer = bytearray()
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                mp3_buffer.extend(chunk.get("data", b""))
                # When buffer exceeds ~4 KB, attempt decode to avoid long buffering delay
                if len(mp3_buffer) >= 4096:
                    try:
                        decoded = miniaudio.decode(bytes(mp3_buffer), nchannels=1, sample_rate=16000)
                        pcm_bytes = decoded.samples.tobytes()
                        if pcm_bytes:
                            yield pcm_bytes
                            mp3_buffer.clear()
                    except Exception:
                        # Wait for more MP3 frames to complete frame boundaries
                        continue

        # Flush remaining audio
        if mp3_buffer:
            try:
                decoded = miniaudio.decode(bytes(mp3_buffer), nchannels=1, sample_rate=16000)
                pcm_bytes = decoded.samples.tobytes()
                if pcm_bytes:
                    yield pcm_bytes
            except Exception:
                pass

    async def health_check(self) -> Dict[str, Any]:
        try:
            import edge_tts  # noqa: F401
            return {"ok": True, "provider": "edge-tts", "default_voice": self.voice}
        except ImportError:
            return {"ok": False, "provider": "edge-tts", "error": "edge-tts package not installed"}


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS-1 neural speech synthesis."""

    def __init__(self, api_key: Optional[str] = None, voice: str = "alloy", model: str = "tts-1"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.voice = voice
        self.model = model

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "en"
    ) -> AsyncGenerator[bytes, None]:
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Configure OPENAI_API_KEY in server settings.")

        target_voice = voice or self.voice
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # OpenAI returns 24kHz raw PCM when response_format='pcm'
        payload = {
            "model": self.model,
            "voice": target_voice,
            "input": text[:1400],
            "response_format": "pcm"
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                buffer = bytearray()
                async for chunk in resp.aiter_bytes(chunk_size=2880):
                    buffer.extend(chunk)
                    # Resample 24kHz PCM to 16kHz PCM (3:2 ratio)
                    if len(buffer) >= 2880:
                        resampled = resample_pcm16(bytes(buffer), from_rate=24000, to_rate=16000)
                        if resampled:
                            yield resampled
                        buffer.clear()
                if buffer:
                    resampled = resample_pcm16(bytes(buffer), from_rate=24000, to_rate=16000)
                    if resampled:
                        yield resampled

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
                    return {"ok": True, "provider": "openai", "voice": self.voice}
                return {"ok": False, "provider": "openai", "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"ok": False, "provider": "openai", "error": str(exc)}


class PiperTTSProvider(TTSProvider):
    """Fast, local neural TTS using Piper executable."""

    def __init__(self, piper_path: str = "piper", model_path: Optional[str] = None):
        self.piper_path = piper_path
        self.model_path = model_path or os.getenv("PIPER_MODEL_PATH", "")

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "en"
    ) -> AsyncGenerator[bytes, None]:
        if not shutil.which(self.piper_path):
            raise RuntimeError(
                "Piper binary not found on server system path. Install piper or select Edge-TTS."
            )
        if not self.model_path or not os.path.exists(self.model_path):
            raise RuntimeError(
                f"Piper model path '{self.model_path}' does not exist. Download an onnx voice model."
            )

        import asyncio
        cmd = [self.piper_path, "--model", self.model_path, "--output-raw"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate(input=text.encode("utf-8"))
        if proc.returncode != 0:
            raise RuntimeError(f"Piper execution failed: {stderr.decode('utf-8')}")

        # Yield raw PCM16 output in 1920-byte chunks
        chunk_size = 1920
        for i in range(0, len(stdout), chunk_size):
            yield stdout[i:i + chunk_size]

    async def health_check(self) -> Dict[str, Any]:
        has_binary = bool(shutil.which(self.piper_path))
        has_model = bool(self.model_path and os.path.exists(self.model_path))
        if has_binary and has_model:
            return {"ok": True, "provider": "piper", "model": self.model_path}
        return {
            "ok": False,
            "provider": "piper",
            "error": "Piper binary or voice model missing. Server hardware requirement: Piper executable and ONNX model file."
        }


class MockTTSProvider(TTSProvider):
    """Deterministic synthetic PCM16 audio generator for offline unit testing."""

    def __init__(self, freq_hz: float = 440.0, chunk_count: int = 3):
        self.freq_hz = freq_hz
        self.chunk_count = chunk_count

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        language: str = "en"
    ) -> AsyncGenerator[bytes, None]:
        import asyncio
        for _ in range(self.chunk_count):
            yield generate_pcm16_tone(freq_hz=self.freq_hz, duration_ms=60, sample_rate=16000)
            await asyncio.sleep(0.01)

    async def health_check(self) -> Dict[str, Any]:
        return {"ok": True, "provider": "mock", "status": "active"}
