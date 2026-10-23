"""Run: cd server && python -m pytest -q"""
import os
import tempfile
from pathlib import Path

# Set environment BEFORE importing the app; use isolated test database.
_db = tempfile.NamedTemporaryFile(prefix="myvoice-test-", suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_PATH"] = _db.name
os.environ["ADMIN_PASSWORD"] = "test-strong-admin-password"
os.environ["ENROLLMENT_KEY"] = "test-strong-enrollment-key-123456"

import pytest
from fastapi.testclient import TestClient
from app import app

client=TestClient(app)
ADMIN=("admin",os.environ["ADMIN_PASSWORD"])
ENROLL={"X-Enrollment-Key":os.environ["ENROLLMENT_KEY"]}
DEVICE_ID="AA:BB:CC:DD:EE:11"


def test_health_and_protected_dashboard():
    assert client.get("/api/health").status_code==200
    assert client.get("/api/admin/devices").status_code==401
    assert client.get("/",auth=ADMIN).status_code==200


def test_bootstrap_pair_and_admin_settings():
    r=client.post("/api/device/bootstrap",json={"device_id":DEVICE_ID,"firmware":"0.1.0"})
    assert r.status_code==401
    r=client.post("/api/device/bootstrap",json={"device_id":DEVICE_ID},headers=ENROLL)
    assert r.status_code==200,r.text
    token=r.json()["token"]; code=r.json()["pair_code"]
    h={"X-Device-ID":DEVICE_ID,"X-Device-Token":token}
    assert client.get("/api/device/status",headers=h).json()["paired"] is False
    assert client.post("/api/device/heartbeat",headers=h).status_code==403
    bad=client.post("/api/admin/claim",json={"code":"000000","name":"Desk"},auth=ADMIN)
    assert bad.status_code==404
    claim=client.post("/api/admin/claim",json={"code":code,"name":"Desk Buddy"},auth=ADMIN)
    assert claim.status_code==200
    assert client.get("/api/device/status",headers=h).json()["paired"] is True
    assert client.post("/api/device/heartbeat",headers=h).status_code==200
    assert client.post("/api/device/bootstrap",json={"device_id":DEVICE_ID},headers=ENROLL).status_code==409
    d=client.get("/api/admin/devices",auth=ADMIN).json()["devices"]
    assert len(d)==1 and d[0]["name"]=="Desk Buddy"
    settings={"name":"Kitchen","city":"Chattogram","latitude":22.36,"longitude":91.80,"timezone":"Asia/Dhaka"}
    assert client.post(f"/api/admin/devices/{DEVICE_ID}/settings",json=settings,auth=ADMIN).status_code==200
    t=client.get("/api/device/time",headers=h)
    assert t.status_code==200 and t.json()["timezone"]=="Asia/Dhaka"
    assert client.post("/api/admin/ask",json={"text":"What time is it?","device_id":DEVICE_ID},auth=ADMIN).status_code==200
    assert client.post("/api/device/voice",headers={**h,"Content-Type":"audio/wav"},content=b"RIFF00WAVE").status_code==503


def test_reject_bad_timezone():
    bad={"name":"Kitchen","city":"Anywhere","latitude":0,"longitude":0,"timezone":"Wrong/Zone"}
    assert client.post(f"/api/admin/devices/{DEVICE_ID}/settings",json=bad,auth=ADMIN).status_code==422


def test_weather_and_audio_pipeline_with_mock_provider(monkeypatch):
    import io
    import wave
    import app as backend

    async def pretend_weather(row):
        return {"city": row["city"], "temperature_c": 28, "conditions": "clear skies", "wind_kmh": 4}

    async def pretend_transcription(data):
        return "What time is it?"

    audio_io = io.BytesIO()
    with wave.open(audio_io, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x00" * 400)
    sample_wav = audio_io.getvalue()

    async def pretend_synthesis(text):
        assert "it is" in text.lower()
        return sample_wav

    monkeypatch.setattr(backend, "fetch_weather", pretend_weather)
    monkeypatch.setattr(backend, "transcribe_wav", pretend_transcription)
    monkeypatch.setattr(backend, "synthesize_wav", pretend_synthesis)
    monkeypatch.setattr(backend, "OPENAI_API_KEY", "fake-testing-key")
    d = client.get("/api/admin/devices", auth=ADMIN).json()["devices"][0]
    device_id = d["id"]
    # Re-bootstrap isn't permitted for already paired devices; retrieve token for this
    # fixture through an isolated second device and pair it.
    second_id="AA:BB:CC:DD:EE:22"
    b=client.post("/api/device/bootstrap",json={"device_id": second_id},headers=ENROLL).json()
    client.post("/api/admin/claim",json={"code": b["pair_code"], "name":"Test"},auth=ADMIN)
    headers={"X-Device-ID":second_id,"X-Device-Token":b["token"]}
    r = client.get("/api/device/weather",headers=headers)
    assert r.status_code==200 and r.json()["temperature_c"]==28
    typed=client.post("/api/admin/ask",json={"text":"weather"},auth=ADMIN).json()
    assert "degrees Celsius" in typed["answer"]
    voice=client.post("/api/device/voice",headers={**headers,"Content-Type":"audio/wav"},content=sample_wav)
    assert voice.status_code==200
    assert voice.headers["content-type"].startswith("audio/wav")
    assert voice.content==sample_wav
