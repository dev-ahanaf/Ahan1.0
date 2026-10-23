"""Unit and integration tests for Phase 3: AI tools, scheduler, OTA, telemetry, and device management."""
import asyncio
import json
import os
import tempfile
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Use isolated test database
_db = tempfile.NamedTemporaryFile(prefix="myvoice-phase3-", suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_PATH"] = _db.name
os.environ["ADMIN_PASSWORD"] = "test-phase3-admin-password"
os.environ["ENROLLMENT_KEY"] = "test-phase3-enrollment-key"
os.environ["TESTING"] = "1"

from app import app
from app.db import init_db, get_session
from app.models import Device, Timer, Alarm, FirmwareRelease, DeviceTelemetry, AuditLog
from app.services.tools import tool_registry
from app.services.tools.base import ToolContext
from app.services.tools.clock import ClockTool
from app.services.tools.weather import WeatherTool
from app.services.tools.timer import TimerTool
from app.services.tools.alarm import AlarmTool
from app.services.tools.device_settings import DeviceSettingsTool
from app.services.scheduler import scheduler_service

from app.config import ADMIN_PASSWORD, ENROLLMENT_KEY

init_db()
client = TestClient(app)
ADMIN = ("admin", ADMIN_PASSWORD)
ENROLL = {"X-Enrollment-Key": ENROLLMENT_KEY}
DEVICE_1 = "33:44:55:66:77:88"
DEVICE_2 = "33:44:55:66:77:99"


@pytest.fixture(scope="module", autouse=True)
def setup_test_devices():
    """Bootstrap and pair test devices."""
    for dev_id, name in [(DEVICE_1, "Living Room Device"), (DEVICE_2, "Kitchen Device")]:
        res = client.post("/api/device/bootstrap", json={"device_id": dev_id, "firmware": "1.0.0"}, headers=ENROLL)
        if res.status_code == 200:
            code = res.json()["pair_code"]
            claim = client.post("/api/admin/claim", json={"code": code, "name": name}, auth=ADMIN)
            assert claim.status_code == 200
        else:
            with get_session() as session:
                dev = session.query(Device).filter(Device.id == dev_id).first()
                if dev:
                    dev.paired = 1
                    dev.revoked = 0
                    session.commit()


def test_tool_registry_discovery():
    """Verify all built-in tools are discovered by the registry."""
    tools = tool_registry.get_all_tools()
    tool_names = [t.name for t in tools]
    assert "get_current_time" in tool_names
    assert "get_weather" in tool_names
    assert "web_search" in tool_names
    assert "manage_timer" in tool_names
    assert "manage_alarm" in tool_names
    assert "device_settings" in tool_names


def test_clock_tool_execution():
    """Test ClockTool returns timezone-aware time and date."""
    tool = ClockTool()
    ctx = ToolContext(device_id=DEVICE_1, timezone="Asia/Dhaka")
    result = asyncio.run(tool.execute({}, ctx))
    assert result.success is True
    assert "time" in result.data
    assert "date" in result.data
    assert "day_of_week" in result.data
    assert result.display_data is not None
    assert result.display_data.get("screen") == "clock"


def test_weather_tool_execution():
    """Test WeatherTool execution with fallback or live API."""
    tool = WeatherTool()
    ctx = ToolContext(device_id=DEVICE_1, city="Dhaka", latitude=23.8103, longitude=90.4125)
    result = asyncio.run(tool.execute({"location": "Dhaka"}, ctx))
    assert result.success is True
    assert "temperature_c" in result.data
    assert "condition" in result.data
    assert result.display_data is not None
    assert result.display_data.get("screen") == "weather"


def test_timer_tool_set_and_cancel():
    """Test TimerTool setting and cancelling a timer."""
    tool = TimerTool()
    ctx = ToolContext(device_id=DEVICE_1)
    
    with get_session() as session:
        # Set timer
        res = asyncio.run(tool.execute({"action": "set", "duration_seconds": 120, "label": "Pasta"}, ctx, db=session))
        assert res.success is True
        assert "Pasta" in res.voice_summary
        timer_id = res.data["timer_id"]
        
        # List timers
        list_res = asyncio.run(tool.execute({"action": "list"}, ctx, db=session))
        assert list_res.success is True
        assert any(t["id"] == timer_id for t in list_res.data["timers"])
        
        # Cancel timer
        cancel_res = asyncio.run(tool.execute({"action": "cancel", "timer_id": timer_id}, ctx, db=session))
        assert cancel_res.success is True
        assert "cancelled" in cancel_res.voice_summary.lower()


def test_alarm_tool_create_and_cancel():
    """Test AlarmTool creating and cancelling an alarm."""
    tool = AlarmTool()
    ctx = ToolContext(device_id=DEVICE_1, timezone="Asia/Dhaka")
    
    with get_session() as session:
        # Create alarm
        res = asyncio.run(tool.execute({"action": "create", "time_str": "07:30", "label": "Wake Up"}, ctx, db=session))
        assert res.success is True
        alarm_id = res.data["alarm_id"]
        
        # List alarms
        list_res = asyncio.run(tool.execute({"action": "list"}, ctx, db=session))
        assert list_res.success is True
        assert any(a["id"] == alarm_id for a in list_res.data["alarms"])
        
        # Cancel alarm
        cancel_res = asyncio.run(tool.execute({"action": "cancel", "alarm_id": alarm_id}, ctx, db=session))
        assert cancel_res.success is True
        assert "cancelled" in cancel_res.voice_summary.lower()


def test_device_settings_tool():
    """Test DeviceSettingsTool updating volume, brightness, and display mode."""
    tool = DeviceSettingsTool()
    ctx = ToolContext(device_id=DEVICE_1)
    
    with get_session() as session:
        res = asyncio.run(tool.execute({"action": "set_volume", "volume": 95}, ctx, db=session))
        assert res.success is True
        assert "95" in res.voice_summary
        
        dev = session.query(Device).filter(Device.id == DEVICE_1).first()
        assert dev.speaker_volume == 95


def test_device_tool_permission_enforcement():
    """Test that disabling a tool on a device prevents its execution."""
    with get_session() as session:
        dev = session.query(Device).filter(Device.id == DEVICE_1).first()
        dev.tools_enabled = "clock,timer,alarm"
        session.commit()
        
        ctx = ToolContext(device_id=DEVICE_1)
        # Attempt to execute weather via registry
        res = asyncio.run(tool_registry.execute_tool("get_weather", {"location": "Tokyo"}, ctx, db=session))
        assert res.success is False
        assert "disabled" in res.error.lower()
        
        # Clock should still work
        clock_res = asyncio.run(tool_registry.execute_tool("get_current_time", {}, ctx, db=session))
        assert clock_res.success is True


def test_scheduler_service_timer_expiry():
    """Test that SchedulerService finds expired timers and marks them completed."""
    now = datetime.now(timezone.utc)
    expired_time = (now - timedelta(seconds=5)).isoformat()
    
    with get_session() as session:
        timer = Timer(
            device_id=DEVICE_1,
            label="Egg Timer",
            duration_seconds=10,
            expires_at=expired_time,
            status="active",
            alert_acknowledged=0
        )
        session.add(timer)
        session.commit()
        t_id = timer.id
    
    # Run scheduler tick
    asyncio.run(scheduler_service.check_timers_and_alarms())
    
    # Check status updated to completed
    with get_session() as session:
        t = session.query(Timer).filter(Timer.id == t_id).first()
        assert t.status == "completed"


def test_ota_firmware_upload_magic_byte_validation():
    """Test that OTA upload rejects files without ESP32 0xE9 magic byte."""
    bad_bytes = b"\x00" * 16384
    files = {"file": ("bad_firmware.bin", bad_bytes, "application/octet-stream")}
    data = {"version": "1.0.9-bad", "target_hardware": "esp32dev"}
    
    res = client.post("/api/admin/ota/upload", data=data, files=files, auth=ADMIN)
    assert res.status_code == 400
    assert "magic byte" in res.json()["detail"].lower()


def test_ota_firmware_upload_valid_flow():
    """Test valid OTA firmware upload, listing, and download."""
    valid_payload = b"\xe9\x04\x00\x00" + b"\xaa" * 16380
    files = {"file": ("firmware_v1.0.1.bin", valid_payload, "application/octet-stream")}
    data = {"version": "1.0.1", "target_hardware": "esp32dev", "release_notes": "Phase 3 Release Candidate"}
    
    upload_res = client.post("/api/admin/ota/upload", data=data, files=files, auth=ADMIN)
    assert upload_res.status_code == 200
    release_info = upload_res.json()["release"]
    assert release_info["version"] == "1.0.1"
    assert "sha256" in release_info
    
    # List releases
    list_res = client.get("/api/admin/ota/releases", auth=ADMIN)
    assert list_res.status_code == 200
    assert any(r["version"] == "1.0.1" for r in list_res.json()["releases"])
    
    # Download binary
    dl_res = client.get(f"/api/ota/download/1.0.1/firmware.bin?device_id={DEVICE_1}")
    assert dl_res.status_code == 200
    assert dl_res.content == valid_payload


def test_ota_deploy_to_device():
    """Test deploying an OTA release to a device."""
    deploy_res = client.post(
        "/api/admin/ota/deploy",
        json={"version": "1.0.1", "target_device": DEVICE_1},
        auth=ADMIN
    )
    assert deploy_res.status_code == 200
    assert deploy_res.json()["version"] == "1.0.1"


def test_device_telemetry_and_audit_logs():
    """Test telemetry query and audit log recording."""
    with get_session() as session:
        telem = DeviceTelemetry(
            device_id=DEVICE_1,
            rssi=-62,
            free_heap=185000,
            uptime_s=3600
        )
        session.add(telem)
        session.commit()
    
    t_res = client.get(f"/api/admin/devices/{DEVICE_1}/telemetry", auth=ADMIN)
    assert t_res.status_code == 200
    assert len(t_res.json()["telemetry"]) >= 1
    assert t_res.json()["telemetry"][0]["rssi"] == -62
    
    a_res = client.get("/api/admin/audit-logs", auth=ADMIN)
    assert a_res.status_code == 200
    assert "logs" in a_res.json()


def test_device_reboot_and_reset_wifi_endpoints():
    """Test remote reboot and reset Wi-Fi administrative endpoints."""
    r_res = client.post(f"/api/admin/devices/{DEVICE_1}/reboot", auth=ADMIN)
    assert r_res.status_code == 200
    assert r_res.json()["action"] == "reboot"
    
    w_res = client.post(f"/api/admin/devices/{DEVICE_1}/reset-wifi", auth=ADMIN)
    assert w_res.status_code == 200
    assert w_res.json()["action"] == "reset_wifi"


def test_cross_device_timer_isolation():
    """Verify that devices have isolated timers."""
    with get_session() as session:
        t1 = Timer(
            device_id=DEVICE_1,
            label="Device 1 Timer",
            duration_seconds=300,
            expires_at=(datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
            status="active"
        )
        t2 = Timer(
            device_id=DEVICE_2,
            label="Device 2 Timer",
            duration_seconds=300,
            expires_at=(datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
            status="active"
        )
        session.add_all([t1, t2])
        session.commit()
        t1_id = t1.id
        t2_id = t2.id
    
    # Device 1 cancels its own timer
    del_res = client.delete(f"/api/admin/timers/{t1_id}", auth=ADMIN)
    assert del_res.status_code == 200
    
    # Verify Device 2 timer is still active
    with get_session() as session:
        dev2_timer = session.query(Timer).filter(Timer.id == t2_id).first()
        assert dev2_timer.status == "active"
