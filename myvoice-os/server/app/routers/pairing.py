"""Device bootstrapping and admin pairing router."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.config import ENROLLMENT_KEY
from app.db import get_db
from app.models import Device
from app.schemas import BootstrapBody, PairBody
from app.auth import (
    admin,
    digest,
    code_digest,
    check_claim_rate_limit,
    record_failed_claim
)

router = APIRouter(prefix="/api", tags=["Pairing"])
PAIR_DURATION = timedelta(minutes=10)

# In-memory lookup for active unhashed pairing codes for unpaired devices
ACTIVE_PAIR_CODES: dict[str, str] = {}

def utc_now() -> datetime:
    """Current UTC datetime."""
    return datetime.now(timezone.utc)

def new_code() -> str:
    """Generate 6-digit pairing code."""
    return str(secrets.randbelow(900000) + 100000)

@router.post("/device/bootstrap")
def bootstrap(
    body: BootstrapBody,
    x_enrollment_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Register unprovisioned hardware and issue a 10-minute pairing code."""
    if not x_enrollment_key or not secrets.compare_digest(x_enrollment_key, ENROLLMENT_KEY):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid enrollment key")
    
    device_id = body.device_id.upper()
    existing = db.query(Device).filter(Device.id == device_id).first()
    if existing and existing.paired:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Device is already paired. Use existing token or admin reset procedure."
        )
    
    code = new_code()
    ACTIVE_PAIR_CODES[device_id] = code
    token = secrets.token_urlsafe(32)
    expires_at = (utc_now() + PAIR_DURATION).isoformat()
    now_iso = utc_now().isoformat()
    
    if existing:
        existing.token_hash = digest(token)
        existing.pair_hash = code_digest(code)
        existing.pair_expires = expires_at
        existing.last_seen = now_iso
        existing.firmware = body.firmware
        existing.revoked = 0
    else:
        new_device = Device(
            id=device_id,
            name="My ESP32",
            token_hash=digest(token),
            pair_hash=code_digest(code),
            pair_expires=expires_at,
            created_at=now_iso,
            last_seen=now_iso,
            firmware=body.firmware,
            paired=0,
            config_version=1
        )
        db.add(new_device)
        
    db.commit()
    return {
        "token": token,
        "pair_code": code,
        "expires_in_seconds": 600,
        "paired": False
    }

@router.post("/admin/claim")
def claim(
    request: Request,
    body: PairBody,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Claim a pending device using its 6-digit pairing code (rate-limited)."""
    check_claim_rate_limit(request)
    
    hashed_code = code_digest(body.code)
    device = db.query(Device).filter(
        Device.paired == 0,
        Device.pair_hash == hashed_code
    ).first()
    
    if (device is None or not device.pair_expires or
            datetime.fromisoformat(device.pair_expires) < utc_now()):
        record_failed_claim(request)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid or expired pairing code")
    
    device.paired = 1
    device.name = body.name
    device.pair_hash = None
    device.pair_expires = None
    ACTIVE_PAIR_CODES.pop(device.id, None)
    db.commit()
    
    return {
        "paired": True,
        "device_id": device.id,
        "name": body.name
    }
