"""Authentication, cryptographic helpers, and claim rate limiting."""
import hashlib
import secrets
import time
from collections import defaultdict
from typing import Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from app.config import ADMIN_PASSWORD, ENROLLMENT_KEY
from app.db import get_db
from app.models import Device

security = HTTPBasic()

# In-memory rate limiting for pairing code attempts (IP -> list of failed attempt timestamps)
FAILED_CLAIMS = defaultdict(list)
RATE_LIMIT_WINDOW = 60.0 # seconds
MAX_FAILED_ATTEMPTS = 5

def check_claim_rate_limit(request: Request):
    """Enforce rate limits on pairing code claim attempts to prevent brute-forcing."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    # Filter out attempts older than window
    FAILED_CLAIMS[client_ip] = [t for t in FAILED_CLAIMS[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(FAILED_CLAIMS[client_ip]) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed pairing attempts. Please wait 60 seconds."
        )

def record_failed_claim(request: Request):
    """Record a failed claim attempt against client IP."""
    client_ip = request.client.host if request.client else "unknown"
    FAILED_CLAIMS[client_ip].append(time.time())

def digest(v: str) -> str:
    """Generate SHA-256 hex digest."""
    return hashlib.sha256(v.encode()).hexdigest()

def code_digest(code: str) -> str:
    """Generate keyed SHA-256 digest of pairing code."""
    return digest(ENROLLMENT_KEY + ":" + code)

def admin(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """HTTP Basic Auth dependency for administrator operations."""
    user_ok = secrets.compare_digest(credentials.username.encode(), b"admin")
    pass_ok = secrets.compare_digest(credentials.password.encode(), ADMIN_PASSWORD.encode())
    if not (user_ok and pass_ok):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid dashboard credentials",
            headers={"WWW-Authenticate": "Basic"}
        )
    return True

def get_device(device_id: str, db: Session) -> Optional[Device]:
    """Retrieve device by primary ID."""
    return db.query(Device).filter(Device.id == device_id).first()

def device_auth(
    x_device_id: Optional[str] = Header(None),
    x_device_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Device:
    """Validate device credentials from headers."""
    if not x_device_id or not x_device_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing device credentials")
    
    device = get_device(x_device_id.upper(), db)
    if device is None or device.revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device credentials")
    
    if not secrets.compare_digest(device.token_hash, digest(x_device_token)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid device credentials")
        
    return device

def must_be_paired(device: Device):
    """Ensure device is claimed and active."""
    if not device.paired or device.revoked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Pair device in dashboard first")
