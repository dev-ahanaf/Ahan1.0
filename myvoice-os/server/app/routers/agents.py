"""AI Agents Management API router for Falcon AI Platform."""
import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import AIAgent, Device, AuditLog
from app.schemas import AIAgentCreateBody, AIAgentUpdateBody, AssignAgentBody
from app.auth import admin

router = APIRouter(prefix="/api/admin", tags=["Agents"])


@router.get("/agents")
def list_agents(_: bool = Depends(admin), db: Session = Depends(get_db)):
    """List all AI agents with assigned device counts."""
    agents = db.query(AIAgent).order_by(AIAgent.created_at.asc()).all()
    results = []
    for a in agents:
        dev_rows = db.query(Device).filter(Device.agent_id == a.id).all()
        a_dict = a.to_dict()
        a_dict["assigned_devices_count"] = len(dev_rows)
        a_dict["assigned_devices"] = [{"id": d.id, "name": d.name, "online": d.last_seen is not None} for d in dev_rows]
        results.append(a_dict)
    return {"agents": results}


@router.post("/agents")
def create_agent(
    body: AIAgentCreateBody,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Create a new Falcon AI agent personality."""
    agent_id = "agent-" + uuid.uuid4().hex[:12]
    now_iso = datetime.now(timezone.utc).isoformat()
    agent = AIAgent(
        id=agent_id,
        name=body.name,
        avatar=body.avatar or "🦅",
        description=body.description,
        personality=body.personality,
        system_prompt=body.system_prompt or f"You are {body.name}, a helpful voice assistant.",
        language=body.language,
        model_provider=body.model_provider,
        model_name=body.model_name,
        tts_provider=body.tts_provider,
        tts_voice=body.tts_voice,
        response_style=body.response_style,
        temperature=body.temperature,
        tools_enabled=body.tools_enabled,
        created_at=now_iso,
        updated_at=now_iso
    )
    db.add(agent)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user="admin",
        action="create_agent",
        target=agent_id,
        details=json.dumps({"name": body.name, "model": body.model_name})
    )
    db.add(audit)
    db.commit()
    db.refresh(agent)
    return {"ok": True, "agent": agent.to_dict()}


@router.get("/agents/{agent_id}")
def get_agent(
    agent_id: str,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Get agent configuration details and assigned devices."""
    agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI Agent not found")

    dev_rows = db.query(Device).filter(Device.agent_id == agent.id).all()
    a_dict = agent.to_dict()
    a_dict["assigned_devices"] = [d.to_dict() for d in dev_rows]
    return {"agent": a_dict}


@router.put("/agents/{agent_id}")
def update_agent(
    agent_id: str,
    body: AIAgentUpdateBody,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Update AI Agent configuration."""
    agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI Agent not found")

    if body.name is not None:
        agent.name = body.name
    if body.avatar is not None:
        agent.avatar = body.avatar
    if body.description is not None:
        agent.description = body.description
    if body.personality is not None:
        agent.personality = body.personality
    if body.system_prompt is not None:
        agent.system_prompt = body.system_prompt
    if body.language is not None:
        agent.language = body.language
    if body.model_provider is not None:
        agent.model_provider = body.model_provider
    if body.model_name is not None:
        agent.model_name = body.model_name
    if body.tts_provider is not None:
        agent.tts_provider = body.tts_provider
    if body.tts_voice is not None:
        agent.tts_voice = body.tts_voice
    if body.response_style is not None:
        agent.response_style = body.response_style
    if body.temperature is not None:
        agent.temperature = body.temperature
    if body.tools_enabled is not None:
        agent.tools_enabled = body.tools_enabled

    agent.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    # If active devices have this agent, push config update
    from app.routers.ws_device import ACTIVE_SESSIONS
    dev_rows = db.query(Device).filter(Device.agent_id == agent.id).all()
    for d in dev_rows:
        if d.id.upper() in ACTIVE_SESSIONS:
            ws_sess = ACTIVE_SESSIONS[d.id.upper()]
            try:
                import asyncio
                asyncio.create_task(ws_sess.websocket.send_text(json.dumps({
                    "type": "config_update",
                    "config": {
                        "assistant_name": agent.name,
                        "language": agent.language
                    },
                    "agent_id": agent.id
                })))
            except Exception:
                pass

    return {"ok": True, "agent": agent.to_dict()}


@router.delete("/agents/{agent_id}")
def delete_agent(
    agent_id: str,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Delete an AI agent and unassign associated devices."""
    agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI Agent not found")

    # Unassign devices
    db.query(Device).filter(Device.agent_id == agent_id).update({"agent_id": None})
    db.delete(agent)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        user="admin",
        action="delete_agent",
        target=agent_id,
        details=json.dumps({"name": agent.name})
    )
    db.add(audit)
    db.commit()
    return {"ok": True, "deleted_id": agent_id}


@router.post("/devices/{device_id}/assign_agent")
def assign_agent_to_device(
    device_id: str,
    body: AssignAgentBody,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Assign an AI agent to a device or unassign (agent_id=None)."""
    device = db.query(Device).filter(Device.id == device_id.upper()).first()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")

    if body.agent_id:
        agent = db.query(AIAgent).filter(AIAgent.id == body.agent_id).first()
        if not agent:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "AI Agent not found")
        device.agent_id = agent.id
        device.assistant_name = agent.name
        device.language = agent.language
        device.system_prompt = agent.system_prompt
        device.personality = agent.personality
        device.llm_provider = agent.model_provider
        device.llm_model = agent.model_name
        device.tts_provider = agent.tts_provider
        device.tts_voice = agent.tts_voice
        device.tools_enabled = agent.tools_enabled
    else:
        device.agent_id = None

    device.config_version += 1
    db.commit()

    # Push config_update to active device if connected
    from app.routers.ws_device import ACTIVE_SESSIONS
    if device.id.upper() in ACTIVE_SESSIONS:
        ws_sess = ACTIVE_SESSIONS[device.id.upper()]
        try:
            import asyncio
            asyncio.create_task(ws_sess.websocket.send_text(json.dumps({
                "type": "config_update",
                "config": {
                    "assistant_name": device.assistant_name,
                    "language": device.language,
                    "speaker_volume": device.speaker_volume,
                    "mic_gain": device.mic_gain
                },
                "config_version": device.config_version
            })))
        except Exception:
            pass

    return {"ok": True, "device_id": device_id, "agent_id": device.agent_id}


@router.post("/agents/{agent_id}/test")
async def test_agent(
    agent_id: str,
    payload: dict,
    _: bool = Depends(admin),
    db: Session = Depends(get_db)
):
    """Interactively test an agent's prompt and voice response from console."""
    agent = db.query(AIAgent).filter(AIAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI Agent not found")

    prompt = payload.get("prompt", "Hello! Who are you?")
    from app.services.providers.manager import ProviderManager

    # Construct mock device with agent's properties
    mock_dev = Device(
        id="SIMULATOR",
        name=agent.name,
        assistant_name=agent.name,
        personality=agent.personality,
        system_prompt=agent.system_prompt,
        language=agent.language,
        llm_provider=agent.model_provider,
        llm_model=agent.model_name,
        tts_provider=agent.tts_provider,
        tts_voice=agent.tts_voice,
        agent_id=agent.id
    )

    llm_provider, model_name = ProviderManager.resolve_llm(db, mock_dev)
    messages = [
        {"role": "system", "content": agent.system_prompt or "You are Falcon AI, a concise voice assistant."},
        {"role": "user", "content": prompt}
    ]

    import time
    t0 = time.time()
    response_chunks = []
    try:
        async for chunk in llm_provider.stream_chat(messages, model=model_name, temperature=agent.temperature):
            response_chunks.append(chunk)
        t_llm = int((time.time() - t0) * 1000)

        full_text = "".join(response_chunks).strip() or "Falcon AI response ready."
        return {
            "ok": True,
            "agent_id": agent.id,
            "agent_name": agent.name,
            "response": full_text,
            "latency_ms": t_llm,
            "provider": agent.model_provider,
            "model": model_name
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "fallback_answer": f"Falcon AI ({agent.name}) is online. (Provider message: {str(e)})"
        }
