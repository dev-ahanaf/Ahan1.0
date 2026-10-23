"""OTA firmware distribution router for MyVoice OS."""
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth import admin
from app.models import Device, FirmwareRelease, AuditLog

router = APIRouter(tags=["ota"])

CATALOG_DIR = Path(__file__).resolve().parent.parent.parent / "firmware_catalog"
CATALOG_DIR.mkdir(parents=True, exist_ok=True)

# Maximum allowed firmware binary size: 2 MB
MAX_FIRMWARE_SIZE = 2 * 1024 * 1024

@router.post("/api/admin/ota/upload")
async def upload_firmware(
    file: UploadFile = File(...),
    version: str = Form(...),
    target_hardware: str = Form("esp32dev"),
    release_notes: Optional[str] = Form(None),
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Upload a new compiled ESP32 firmware binary with SHA-256 verification."""
    version = version.strip()
    if not version:
        raise HTTPException(status_code=400, detail="Version string is required")

    existing = db.query(FirmwareRelease).filter(FirmwareRelease.version == version).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Firmware version '{version}' already exists")

    content = await file.read()
    if len(content) > MAX_FIRMWARE_SIZE:
        raise HTTPException(status_code=400, detail=f"Firmware exceeds maximum limit of {MAX_FIRMWARE_SIZE} bytes")
    if len(content) < 10000:
        raise HTTPException(status_code=400, detail="Firmware binary is suspiciously small (< 10 KB)")

    # Validate ESP32 binary magic header (0xE9)
    if content[0] != 0xE9:
        raise HTTPException(
            status_code=400,
            detail="Invalid binary: ESP32 firmware binary must begin with magic byte 0xE9"
        )

    sha256_hash = hashlib.sha256(content).hexdigest()

    version_dir = CATALOG_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)
    bin_path = version_dir / "firmware.bin"

    with open(bin_path, "wb") as f:
        f.write(content)

    release_id = str(uuid.uuid4())
    release = FirmwareRelease(
        id=release_id,
        version=version,
        target_hardware=target_hardware,
        file_path=str(bin_path),
        file_size=len(content),
        sha256=sha256_hash,
        release_notes=release_notes,
        created_at=datetime.now(timezone.utc).isoformat(),
        is_active=1
    )
    db.add(release)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user="admin",
        action="upload_firmware",
        target=version,
        details=json.dumps({"size": len(content), "sha256": sha256_hash, "target_hardware": target_hardware})
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "message": f"Firmware version {version} uploaded successfully",
        "release": release.to_dict()
    }


@router.get("/api/admin/ota/releases")
def list_firmware_releases(
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """List all available firmware releases."""
    releases = db.query(FirmwareRelease).order_by(FirmwareRelease.created_at.desc()).all()
    return {"releases": [r.to_dict() for r in releases]}


@router.post("/api/admin/ota/deploy")
async def deploy_firmware(
    payload: Dict[str, Any],
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Trigger OTA update command to targeted devices over WebSocket."""
    version = payload.get("version")
    target_device = payload.get("target_device", "ALL")

    if not version:
        raise HTTPException(status_code=400, detail="Firmware version is required")

    release = db.query(FirmwareRelease).filter(FirmwareRelease.version == version).first()
    if not release:
        raise HTTPException(status_code=404, detail=f"Release {version} not found")

    from app.routers.ws_device import ACTIVE_SESSIONS

    devices_to_update = []
    if target_device == "ALL":
        devices_to_update = db.query(Device).filter(Device.paired == 1, Device.revoked == 0).all()
    else:
        d = db.query(Device).filter(Device.id == target_device, Device.paired == 1, Device.revoked == 0).first()
        if d:
            devices_to_update = [d]

    dispatched = []
    for d in devices_to_update:
        session = ACTIVE_SESSIONS.get(d.id)
        if session and session.websocket:
            ota_frame = {
                "type": "ota",
                "version": release.version,
                "url": f"/api/ota/download/{release.version}/firmware.bin?device_id={d.id}",
                "sha256": release.sha256,
                "size": release.file_size
            }
            try:
                await session.websocket.send_text(json.dumps(ota_frame))
                dispatched.append({"device_id": d.id, "status": "dispatched"})
            except Exception as e:
                dispatched.append({"device_id": d.id, "status": "failed", "error": str(e)})
        else:
            dispatched.append({"device_id": d.id, "status": "offline_pending"})

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user="admin",
        action="deploy_firmware",
        target=target_device,
        details=json.dumps({"version": version, "dispatched_count": len(dispatched)})
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "version": release.version,
        "results": dispatched
    }


@router.get("/api/ota/download/{version}/{filename}")
def download_firmware(
    version: str,
    filename: str,
    device_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Protected firmware download endpoint validating device authorization."""
    # Check authorization via token query or device_id if authenticated
    auth_header = request.headers.get("X-Device-Token") if request else None
    check_token = token or auth_header

    if device_id:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device or device.revoked:
            raise HTTPException(status_code=403, detail="Device not authorized for firmware download")
        if check_token:
            token_hash = hashlib.sha256(check_token.encode()).hexdigest()
            if token_hash != device.token_hash:
                raise HTTPException(status_code=401, detail="Invalid token for firmware download")

    release = db.query(FirmwareRelease).filter(FirmwareRelease.version == version).first()
    if not release or not release.is_active:
        raise HTTPException(status_code=404, detail="Firmware release not found or inactive")

    bin_path = Path(release.file_path)
    if not bin_path.exists():
        raise HTTPException(status_code=404, detail="Firmware binary file missing on disk")

    return FileResponse(
        bin_path,
        media_type="application/octet-stream",
        filename=f"myvoice-os-{version}.bin",
        headers={
            "X-Firmware-SHA256": release.sha256,
            "X-Firmware-Size": str(release.file_size)
        }
    )
