"""Automated Speech Recognition (ASR) service via OpenAI Whisper."""
import sys
import httpx
from app import config

async def transcribe_wav(data: bytes) -> str:
    """Send audio bytes to OpenAI speech transcription endpoint."""
    backend = sys.modules.get("app")
    if backend and hasattr(backend, "transcribe_wav") and backend.transcribe_wav is not transcribe_wav:
        return await backend.transcribe_wav(data)
        
    api_key = backend.OPENAI_API_KEY if (backend and hasattr(backend, "OPENAI_API_KEY")) else config.OPENAI_API_KEY
    async with httpx.AsyncClient(timeout=60) as client:
        result = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("recording.wav", data, "audio/wav")},
            data={"model": "gpt-4o-mini-transcribe"}
        )
        result.raise_for_status()
        return result.json().get("text", "")
