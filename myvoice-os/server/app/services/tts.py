"""Text-to-Speech (TTS) service via OpenAI speech synthesis."""
import sys
import httpx
from app import config

async def synthesize_wav(text: str) -> bytes:
    """Synthesize text into WAV audio using OpenAI TTS-1."""
    backend = sys.modules.get("app")
    if backend and hasattr(backend, "synthesize_wav") and backend.synthesize_wav is not synthesize_wav:
        return await backend.synthesize_wav(text)
        
    api_key = backend.OPENAI_API_KEY if (backend and hasattr(backend, "OPENAI_API_KEY")) else config.OPENAI_API_KEY
    async with httpx.AsyncClient(timeout=65) as client:
        r = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "tts-1",
                "voice": "alloy",
                "input": text[:1400],
                "response_format": "wav"
            }
        )
        r.raise_for_status()
        return r.content
