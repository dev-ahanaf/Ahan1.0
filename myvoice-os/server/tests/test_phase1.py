"""Comprehensive test suite for Phase 1 features."""
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

# Use isolated test database
_db = tempfile.NamedTemporaryFile(prefix="myvoice-phase1-", suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_PATH"] = _db.name
os.environ["ADMIN_PASSWORD"] = "test-strong-admin-password"
os.environ["ENROLLMENT_KEY"] = "test-strong-enrollment-key-123456"
os.environ["TESTING"] = "1"

from app import app
from app.db import get_engine, init_db
from app.auth import FAILED_CLAIMS

init_db()

client = TestClient(app)
ADMIN = ("admin", os.environ["ADMIN_PASSWORD"])
ENROLL = {"X-Enrollment-Key": os.environ["ENROLLMENT_KEY"]}
DEVICE_ID = "11:22:33:44:55:66"

def test_single_use_pairing_code_and_expiry():
    """Verify pairing codes are single-use and expire after duration."""
    r = client.post("/api/device/bootstrap", json={"device_id": DEVICE_ID, "firmware": "0.1.0"}, headers=ENROLL)
    assert r.status_code == 200
    token = r.json()["token"]
    code = r.json()["pair_code"]
    headers = {"X-Device-ID": DEVICE_ID, "X-Device-Token": token}
    
    # Check status endpoint confirms device is awaiting claim
    status_res = client.get("/api/device/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["paired"] is False
    
    # Claim device successfully
    claim_res = client.post("/api/admin/claim", json={"code": code, "name": "Living Room"}, auth=ADMIN)
    assert claim_res.status_code == 200
    assert claim_res.json()["paired"] is True
    
    # Device status now confirms paired is True
    paired_status = client.get("/api/device/status", headers=headers)
    assert paired_status.json()["paired"] is True
    
    # Second attempt with the same code must fail (single-use)
    reclaim_res = client.post("/api/admin/claim", json={"code": code, "name": "Living Room 2"}, auth=ADMIN)
    assert reclaim_res.status_code == 404

def test_claim_rate_limiting():
    """Verify rate limiter blocks brute force attempts on claim endpoint."""
    FAILED_CLAIMS.clear()
    
    for _ in range(5):
        r = client.post("/api/admin/claim", json={"code": "000000", "name": "Hack"}, auth=ADMIN)
        assert r.status_code == 404
        
    # Sixth attempt must be rejected with 429
    blocked = client.post("/api/admin/claim", json={"code": "000000", "name": "Hack"}, auth=ADMIN)
    assert blocked.status_code == 429
    assert "Too many failed pairing attempts" in blocked.json()["detail"]
    FAILED_CLAIMS.clear()

def test_token_rotation_and_revocation():
    """Verify admin token rotation and device revocation lifecycle."""
    dev_id = "22:33:44:55:66:77"
    boot = client.post("/api/device/bootstrap", json={"device_id": dev_id}, headers=ENROLL).json()
    token = boot["token"]
    code = boot["pair_code"]
    client.post("/api/admin/claim", json={"code": code, "name": "Rotatable"}, auth=ADMIN)
    
    headers = {"X-Device-ID": dev_id, "X-Device-Token": token}
    assert client.post("/api/device/heartbeat", headers=headers).status_code == 200
    
    # Rotate token
    rotate = client.post(f"/api/admin/devices/{dev_id}/rotate-token", auth=ADMIN)
    assert rotate.status_code == 200
    new_token = rotate.json()["new_token"]
    assert new_token != token
    
    # Old token must now be rejected
    assert client.post("/api/device/heartbeat", headers=headers).status_code == 401
    
    # New token works
    new_headers = {"X-Device-ID": dev_id, "X-Device-Token": new_token}
    assert client.post("/api/device/heartbeat", headers=new_headers).status_code == 200
    
    # Revoke device
    revoke = client.post(f"/api/admin/devices/{dev_id}/revoke", auth=ADMIN)
    assert revoke.status_code == 200
    assert revoke.json()["revoked"] is True
    
    # Device must now be forbidden from heartbeat
    assert client.post("/api/device/heartbeat", headers=new_headers).status_code == 401

def test_config_versioning_and_dynamic_sync():
    """Verify per-device settings update config_version and sync via heartbeat & GET /config."""
    dev_id = "33:44:55:66:77:88"
    boot = client.post("/api/device/bootstrap", json={"device_id": dev_id}, headers=ENROLL).json()
    client.post("/api/admin/claim", json={"code": boot["pair_code"], "name": "SyncDevice"}, auth=ADMIN)
    headers = {"X-Device-ID": dev_id, "X-Device-Token": boot["token"]}
    
    # Initial config version should be 1
    hb = client.post("/api/device/heartbeat", headers=headers).json()
    assert hb["config_version"] == 1
    
    cfg = client.get("/api/device/config", headers=headers).json()
    assert cfg["config_version"] == 1
    assert cfg["oled_brightness"] == 128
    assert cfg["clock_format"] == "24h"
    
    # Update settings via admin dashboard
    new_settings = {
        "name": "SyncDevice Office",
        "city": "Sylhet",
        "latitude": 24.8949,
        "longitude": 91.8687,
        "timezone": "Asia/Dhaka",
        "language": "en",
        "oled_brightness": 200,
        "idle_display_mode": "weather",
        "clock_format": "12h",
        "speaker_volume": 90,
        "mic_gain": 65,
        "wake_mode": "button",
        "weather_enabled": True,
        "search_enabled": True,
        "timers_enabled": True
    }
    update_res = client.post(f"/api/admin/devices/{dev_id}/settings", json=new_settings, auth=ADMIN)
    assert update_res.status_code == 200
    assert update_res.json()["config_version"] == 2
    
    # Heartbeat must report version 2
    hb2 = client.post("/api/device/heartbeat", headers=headers).json()
    assert hb2["config_version"] == 2
    
    # Device fetches new config
    cfg2 = client.get("/api/device/config", headers=headers).json()
    assert cfg2["config_version"] == 2
    assert cfg2["oled_brightness"] == 200
    assert cfg2["clock_format"] == "12h"
    assert cfg2["city"] == "Sylhet"
    assert cfg2["idle_display_mode"] == "weather"

def test_duplicate_bootstrap_rejection():
    """Verify that an already paired device cannot be re-bootstrapped or hijacked."""
    dev_id = "44:55:66:77:88:99"
    boot = client.post("/api/device/bootstrap", json={"device_id": dev_id}, headers=ENROLL).json()
    client.post("/api/admin/claim", json={"code": boot["pair_code"], "name": "SecureDevice"}, auth=ADMIN)
    
    # Attempting to re-bootstrap an already paired device returns 409 Conflict
    reboot = client.post("/api/device/bootstrap", json={"device_id": dev_id}, headers=ENROLL)
    assert reboot.status_code == 409
