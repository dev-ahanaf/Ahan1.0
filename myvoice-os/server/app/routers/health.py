"""Health check router."""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "MyVoice OS", "version": "1.0.0-rc1"}

