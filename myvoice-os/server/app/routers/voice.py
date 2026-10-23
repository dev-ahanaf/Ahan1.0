"""Push-to-talk HTTP voice processing router."""
import sys
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app import config
from app.db import get_db
from app.models import Device
from app.auth import device_auth, must_be_paired
from app.services.asr import transcribe_wav
from app.services.tts import synthesize_wav
from app.services.llm import answer_question

router = APIRouter(prefix="/api/device", tags=["Voice"])
MAX_WAV_BYTES = 192_000

def get_current_openai_key() -> str:
    backend = sys.modules.get("app")
    if backend and hasattr(backend, "OPENAI_API_KEY"):
        return backend.OPENAI_API_KEY
    return config.OPENAI_API_KEY

@router.post("/voice")
async def voice_device(
    request: Request,
    device: Device = Depends(device_auth),
    db: Session = Depends(get_db)
):
    """Process incoming audio recording and return synthesized spoken answer."""
    must_be_paired(device)
    api_key = get_current_openai_key()
    if not api_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Set OPENAI_API_KEY for voice transcription and spoken playback"
        )
    
    content_type = request.headers.get("content-type", "").split(";")[0].lower()
    if content_type != "audio/wav":
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Expected audio/wav")
    
    content_length = int(request.headers.get("content-length", "0") or "0")
    if content_length > MAX_WAV_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Recording too large")
        
    audio = await request.body()
    if not (44 <= len(audio) <= MAX_WAV_BYTES) or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or oversized WAV")
        
    try:
        question = await transcribe_wav(audio)
        if not question or not question.strip():
            question = "I couldn't hear anything clearly."
            answer = "I couldn't hear you clearly. Please try again."
        else:
            answer = await answer_question(question, device.to_dict())
        speech = await synthesize_wav(answer)
    except httpx.HTTPError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Cloud audio service failed; check API key, quota and connectivity"
        )
        
    device.last_seen = datetime.now(timezone.utc).isoformat()
    db.commit()
    
    return Response(
        content=speech,
        media_type="audio/wav",
        headers={
            "X-Transcript-Available": "true",
            "Cache-Control": "no-store"
        }
    )
