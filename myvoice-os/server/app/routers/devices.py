"""Device state, heartbeat, configuration sync, weather, and time router."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Device
from app.schemas import HeartbeatBody, DeviceConfigOut
from app.auth import device_auth, must_be_paired, code_digest
from app.services.weather import fetch_weather

router = APIRouter(prefix="/api/device", tags=["Device"])
PAIR_DURATION = timedelta(minutes=10)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

@router.get("/status")
def device_status(device: Device = Depends(device_auth), db: Session = Depends(get_db)):
    """Device status check and pairing code renewal."""
    code = None
    if not device.paired and (not device.pair_expires or datetime.fromisoformat(device.pair_expires) < utc_now()):
        import secrets
        code = str(secrets.randbelow(900000) + 100000)
        device.pair_hash = code_digest(code)
        device.pair_expires = (utc_now() + PAIR_DURATION).isoformat()
        db.commit()
    return {
        "paired": bool(device.paired),
        "name": device.name,
        "pair_code": code,
        "city": device.city,
        "timezone": device.timezone,
        "config_version": device.config_version
    }

@router.post("/heartbeat")
def device_heartbeat(
    body: Optional[HeartbeatBody] = None,
    device: Device = Depends(device_auth),
    db: Session = Depends(get_db)
):
    """Device heartbeat and configuration version synchronization."""
    must_be_paired(device)
    device.last_seen = utc_now().isoformat()
    db.commit()
    return {
        "ok": True,
        "name": device.name,
        "server_utc": utc_now().isoformat(),
        "config_version": device.config_version
    }

@router.get("/config", response_model=DeviceConfigOut)
def get_device_config(device: Device = Depends(device_auth)):
    """Fetch complete per-device configuration settings."""
    must_be_paired(device)
    return {
        "config_version": device.config_version,
        "name": device.name,
        "timezone": device.timezone,
        "language": device.language,
        "city": device.city,
        "latitude": device.latitude,
        "longitude": device.longitude,
        "oled_brightness": device.oled_brightness,
        "idle_display_mode": device.idle_display_mode,
        "clock_format": device.clock_format,
        "speaker_volume": device.speaker_volume,
        "mic_gain": device.mic_gain,
        "wake_mode": device.wake_mode,
        "weather_enabled": bool(device.weather_enabled),
        "search_enabled": bool(device.search_enabled),
        "timers_enabled": bool(device.timers_enabled)
    }

@router.get("/weather")
async def device_weather(device: Device = Depends(device_auth)):
    """Fetch localized weather forecast for device location."""
    must_be_paired(device)
    try:
        return await fetch_weather(device.to_dict())
    except (httpx.HTTPError, KeyError, ValueError):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Weather service temporarily unavailable"
        )

@router.get("/time")
def device_time(device: Device = Depends(device_auth)):
    """Fetch formatted local time and timezone offsets."""
    must_be_paired(device)
    tz = ZoneInfo(device.timezone)
    now = datetime.now(tz)
    return {
        "local_time": now.isoformat(),
        "timezone": device.timezone,
        "epoch_seconds": int(now.timestamp()),
        "utc_offset_seconds": int(now.utcoffset().total_seconds() if now.utcoffset() else 0)
    }
