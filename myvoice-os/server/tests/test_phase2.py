"""Unit and integration tests for Phase 2: WebSocket streaming, providers, memory, and barge-in."""
import json
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Use isolated test database
_db = tempfile.NamedTemporaryFile(prefix="myvoice-phase2-", suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_PATH"] = _db.name
os.environ["ADMIN_PASSWORD"] = "test-strong-admin-password"
os.environ["ENROLLMENT_KEY"] = "test-strong-enrollment-key-123456"
os.environ["TESTING"] = "1"

from app import app
from app.db import init_db
from app.services.audio_utils import generate_pcm16_tone, detect_energy_vad, resample_pcm16

init_db()
client = TestClient(app)
ADMIN = ("admin", os.environ["ADMIN_PASSWORD"])
ENROLL = {"X-Enrollment-Key": os.environ["ENROLLMENT_KEY"]}
DEVICE_ID = "AA:BB:CC:DD:EE:99"

@pytest.fixture(scope="module")
def paired_device():
    """Bootstrap and claim a device for testing."""
    res = client.post("/api/device/bootstrap", json={"device_id": DEVICE_ID, "firmware": "1.0.0"}, headers=ENROLL)
    assert res.status_code == 200
    token = res.json()["token"]
    code = res.json()["pair_code"]
    
    claim = client.post("/api/admin/claim", json={"code": code, "name": "Lab Device"}, auth=ADMIN)
    assert claim.status_code == 200
    
    # Configure device to use mock providers for deterministic offline testing
    settings = {
        "name": "Lab Device",
        "city": "Dhaka",
        "latitude": 23.8103,
        "longitude": 90.4125,
        "timezone": "Asia/Dhaka",
        "language": "en",
        "oled_brightness": 128,
        "idle_display_mode": "clock",
        "clock_format": "24h",
        "speaker_volume": 80,
        "mic_gain": 50,
        "wake_mode": "button",
        "weather_enabled": True,
        "search_enabled": True,
        "timers_enabled": True,
        "asr_provider": "mock",
        "llm_provider": "mock",
        "tts_provider": "mock",
        "history_length": 6
    }
    set_res = client.post(f"/api/admin/devices/{DEVICE_ID}/settings", json=settings, auth=ADMIN)
    assert set_res.status_code == 200

    return {"device_id": DEVICE_ID, "token": token}


def test_ws_auth_rejection():
    """Verify WebSocket endpoint rejects unauthenticated or invalid tokens."""
    # Invalid device ID
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/device?device_id=00:00:00:00:00:00&token=bad"):
            pass

    # Invalid token for existing device
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/device?device_id={DEVICE_ID}&token=invalid-token"):
            pass


def test_ws_handshake_and_session(paired_device):
    """Verify successful WebSocket handshake and hello_ack."""
    dev_id = paired_device["device_id"]
    token = paired_device["token"]

    with client.websocket_connect(f"/ws/device?device_id={dev_id}&token={token}") as ws:
        # Send hello
        ws.send_text(json.dumps({
            "type": "hello",
            "firmware": "1.0.0",
            "audio": {"codec": "pcm16", "sample_rate": 16000, "channels": 1, "frame_ms": 60}
        }))

        ack = json.loads(ws.receive_text())
        assert ack["type"] == "hello_ack"
        assert "session_id" in ack
        assert ack["config"]["assistant_name"] == "MyVoice"


def test_ws_voice_streaming_pipeline(paired_device):
    """Test full voice cycle: audio frames -> STT -> LLM tokens -> binary TTS -> tts_stop."""
    dev_id = paired_device["device_id"]
    token = paired_device["token"]

    with client.websocket_connect(f"/ws/device?device_id={dev_id}&token={token}") as ws:
        # Handshake
        ws.send_text(json.dumps({"type": "hello", "firmware": "1.0.0"}))
        ack = json.loads(ws.receive_text())
        assert ack["type"] == "hello_ack"

        # Start listening
        ws.send_text(json.dumps({"type": "listen_start", "mode": "manual"}))

        # Stream 3 PCM16 frames (1920 bytes each)
        for _ in range(3):
            pcm_chunk = generate_pcm16_tone(freq_hz=440.0, duration_ms=60, sample_rate=16000)
            assert len(pcm_chunk) == 1920
            ws.send_bytes(pcm_chunk)

        # Stop listening
        ws.send_text(json.dumps({"type": "listen_stop"}))

        # Collect events
        received_stt = False
        received_llm = False
        received_tts_start = False
        received_audio_bytes = 0
        received_tts_stop = False

        while not received_tts_stop:
            msg = ws.receive()
            if "bytes" in msg and msg["bytes"]:
                received_audio_bytes += len(msg["bytes"])
            elif "text" in msg and msg["text"]:
                event = json.loads(msg["text"])
                etype = event.get("type")
                if etype == "stt":
                    received_stt = True
                    assert len(event.get("text", "")) > 0
                elif etype == "llm":
                    received_llm = True
                elif etype == "tts_start":
                    received_tts_start = True
                    assert event.get("codec") == "pcm16"
                elif etype == "tts_stop":
                    received_tts_stop = True

        assert received_stt is True
        assert received_llm is True
        assert received_tts_start is True
        assert received_audio_bytes > 0
        assert received_tts_stop is True


def test_ws_barge_in_abort(paired_device):
    """Verify client abort stops pipeline immediately and receives abort_ack."""
    dev_id = paired_device["device_id"]
    token = paired_device["token"]

    with client.websocket_connect(f"/ws/device?device_id={dev_id}&token={token}") as ws:
        ws.send_text(json.dumps({"type": "hello"}))
        ws.receive_text()

        ws.send_text(json.dumps({"type": "listen_start"}))
        for _ in range(2):
            ws.send_bytes(generate_pcm16_tone(duration_ms=60))
        ws.send_text(json.dumps({"type": "listen_stop"}))

        # Send abort
        ws.send_text(json.dumps({"type": "abort", "reason": "user_interrupt"}))

        got_abort_ack = False
        for _ in range(10):
            msg = ws.receive()
            if "text" in msg and msg["text"]:
                evt = json.loads(msg["text"])
                if evt.get("type") == "abort_ack":
                    got_abort_ack = True
                    break

        assert got_abort_ack is True


def test_provider_health_checks():
    """Verify admin provider test endpoint for mock and available providers."""
    # Mock ASR
    r1 = client.post("/api/admin/providers/test", json={"provider_type": "asr", "provider_name": "mock"}, auth=ADMIN)
    assert r1.status_code == 200
    assert r1.json()["ok"] is True

    # Mock LLM
    r2 = client.post("/api/admin/providers/test", json={"provider_type": "llm", "provider_name": "mock"}, auth=ADMIN)
    assert r2.status_code == 200
    assert r2.json()["ok"] is True

    # Mock TTS
    r3 = client.post("/api/admin/providers/test", json={"provider_type": "tts", "provider_name": "mock"}, auth=ADMIN)
    assert r3.status_code == 200
    assert r3.json()["ok"] is True

    # Edge TTS (local library)
    r4 = client.post("/api/admin/providers/test", json={"provider_type": "tts", "provider_name": "edge-tts"}, auth=ADMIN)
    assert r4.status_code == 200
    assert r4.json()["ok"] is True


def test_conversation_memory_and_search(paired_device):
    """Verify conversation messages are stored and searchable."""
    res = client.get("/api/admin/conversations", auth=ADMIN)
    assert res.status_code == 200
    convs = res.json()["conversations"]
    assert len(convs) >= 1

    first_conv_id = convs[0]["id"]
    msgs_res = client.get(f"/api/admin/conversations/{first_conv_id}/messages", auth=ADMIN)
    assert msgs_res.status_code == 200
    msgs = msgs_res.json()["messages"]
    assert len(msgs) >= 2  # user and assistant

    # Search conversation
    search_res = client.get("/api/admin/conversations?q=weather", auth=ADMIN)
    assert search_res.status_code == 200


def test_audio_utils_dsp():
    """Verify DSP helpers: energy VAD and resampling."""
    tone = generate_pcm16_tone(freq_hz=1000.0, duration_ms=60, sample_rate=16000)
    silence = b"\x00" * 1920

    assert detect_energy_vad(tone, threshold=200.0) is True
    assert detect_energy_vad(silence, threshold=200.0) is False

    # Resample 24kHz to 16kHz
    orig_24k = generate_pcm16_tone(freq_hz=440.0, duration_ms=100, sample_rate=24000)
    resampled_16k = resample_pcm16(orig_24k, from_rate=24000, to_rate=16000)
    expected_samples = int(len(orig_24k) // 2 * (16000 / 24000))
    actual_samples = len(resampled_16k) // 2
    assert abs(actual_samples - expected_samples) <= 2
