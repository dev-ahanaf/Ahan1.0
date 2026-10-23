import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import ADMIN_PASSWORD, ENROLLMENT_KEY

client = TestClient(app)
AUTH = ("admin", os.getenv("ADMIN_PASSWORD", ADMIN_PASSWORD))
ENROLL = {"X-Enrollment-Key": os.getenv("ENROLLMENT_KEY", ENROLLMENT_KEY)}


def test_list_seeded_agents():
    """Verify seeded Falcon AI primary and Bangla agents exist."""
    res = client.get("/api/admin/agents", auth=AUTH)
    assert res.status_code == 200
    data = res.json()
    assert "agents" in data
    assert len(data["agents"]) >= 2
    agent_ids = [a["id"] for a in data["agents"]]
    assert "agent-falcon-primary" in agent_ids
    assert "agent-falcon-bangla" in agent_ids


def test_create_and_delete_agent():
    """Test full lifecycle of a custom Falcon agent."""
    payload = {
        "name": "Falcon Coding Tutor",
        "avatar": "💻",
        "description": "Programming assistant for embedded and web systems",
        "personality": "expert software architect and patient teacher",
        "system_prompt": "You are a coding expert assistant. Answer clearly in concise points.",
        "language": "en",
        "model_provider": "gemini",
        "model_name": "gemini-1.5-pro",
        "tts_provider": "edge-tts",
        "tts_voice": "en-US-GuyNeural",
        "response_style": "detailed",
        "temperature": 0.5,
        "tools_enabled": "clock,search,device_settings"
    }
    create_res = client.post("/api/admin/agents", auth=AUTH, json=payload)
    assert create_res.status_code == 200
    created = create_res.json()["agent"]
    agent_id = created["id"]
    assert created["name"] == "Falcon Coding Tutor"
    assert created["model_name"] == "gemini-1.5-pro"

    # Fetch agent details
    get_res = client.get(f"/api/admin/agents/{agent_id}", auth=AUTH)
    assert get_res.status_code == 200
    assert get_res.json()["agent"]["avatar"] == "💻"

    # Update agent
    update_res = client.put(f"/api/admin/agents/{agent_id}", auth=AUTH, json={
        "name": "Falcon Senior Architect",
        "temperature": 0.8
    })
    assert update_res.status_code == 200
    assert update_res.json()["agent"]["name"] == "Falcon Senior Architect"
    assert update_res.json()["agent"]["temperature"] == 0.8

    # Delete agent
    del_res = client.delete(f"/api/admin/agents/{agent_id}", auth=AUTH)
    assert del_res.status_code == 200
    assert del_res.json()["deleted_id"] == agent_id

    # Verify 404 after deletion
    assert client.get(f"/api/admin/agents/{agent_id}", auth=AUTH).status_code == 404


def test_assign_agent_to_device():
    """Test assigning and unassigning an agent to a registered device."""
    # Register/bootstrap a device first
    dev_id = "AA:BB:CC:11:22:33"
    b_res = client.post("/api/device/bootstrap", json={"device_id": dev_id, "firmware": "1.2.0"}, headers=ENROLL)

    assert b_res.status_code == 200
    code = b_res.json()["pair_code"]


    # Claim device
    claim_res = client.post("/api/admin/claim", auth=AUTH, json={"code": code, "name": "Living Room Falcon"})
    assert claim_res.status_code == 200

    # Assign Bangla agent
    assign_res = client.post(
        f"/api/admin/devices/{dev_id}/assign_agent",
        auth=AUTH,
        json={"agent_id": "agent-falcon-bangla"}
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["agent_id"] == "agent-falcon-bangla"

    # Verify device config reflects agent
    dev_res = client.get("/api/admin/devices", auth=AUTH)
    assert dev_res.status_code == 200
    target_dev = next(d for d in dev_res.json()["devices"] if d["id"] == dev_id)
    assert target_dev["agent_id"] == "agent-falcon-bangla"
    assert target_dev["assistant_name"] == "Falcon AI বাংলা"
    assert target_dev["language"] == "bn"

    # Unassign agent
    unassign_res = client.post(
        f"/api/admin/devices/{dev_id}/assign_agent",
        auth=AUTH,
        json={"agent_id": None}
    )
    assert unassign_res.status_code == 200
    assert unassign_res.json()["agent_id"] is None

    # Cleanup test device so subsequent tests have isolated device count
    from app.db import get_db_session
    from app.models import Device
    s = get_db_session()
    s.query(Device).filter(Device.id == dev_id).delete()
    s.commit()
    s.close()

