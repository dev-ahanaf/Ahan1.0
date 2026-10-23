"""Conversation memory engine and context construction for MyVoice OS."""
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.models import Conversation, Message, Device

def get_or_create_conversation(db: Session, device_id: str, title: str = "Voice Chat") -> Conversation:
    """Get latest active conversation for device or create a fresh session if idle for >1 hour."""
    now = datetime.now(timezone.utc)
    conv = (
        db.query(Conversation)
        .filter(Conversation.device_id == device_id)
        .order_by(desc(Conversation.updated_at))
        .first()
    )

    if conv:
        try:
            last_dt = datetime.fromisoformat(conv.updated_at)
            if now - last_dt < timedelta(hours=1):
                return conv
        except Exception:
            pass

    # Create new conversation
    conv_id = str(uuid.uuid4())
    new_conv = Conversation(
        id=conv_id,
        device_id=device_id,
        title=title,
        created_at=now.isoformat(),
        updated_at=now.isoformat()
    )
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return new_conv

def record_message(
    db: Session,
    conversation_id: str,
    device_id: str,
    role: str,
    content: str,
    latency_ms: Optional[int] = None,
    provider_info: Optional[Dict[str, Any]] = None
) -> Message:
    """Save an incoming user query or assistant reply to conversation history."""
    now = datetime.now(timezone.utc).isoformat()
    msg_id = str(uuid.uuid4())
    info_str = json.dumps(provider_info) if provider_info else None

    msg = Message(
        id=msg_id,
        conversation_id=conversation_id,
        device_id=device_id,
        role=role,
        content=content,
        latency_ms=latency_ms,
        provider_info=info_str,
        created_at=now
    )
    db.add(msg)

    # Update conversation updated_at timestamp
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        conv.updated_at = now

    db.commit()
    db.refresh(msg)
    return msg

def get_conversation_context(db: Session, conversation_id: str, history_length: int = 6) -> List[Dict[str, str]]:
    """Retrieve last N messages from the conversation for LLM prompting."""
    if history_length <= 0:
        return []

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(history_length)
        .all()
    )
    # Reverse to restore chronological order
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]

def build_system_prompt(device: Optional[Device], db: Optional[Session] = None) -> str:
    """Build dynamic system instructions with Falcon AI branding and agent localization."""
    name = "Falcon AI"
    personality = "intelligent, concise voice companion"
    system_custom = None
    city = device.city if (device and device.city) else "Dhaka"

    if device:
        if device.agent_id and db:
            from app.models import AIAgent
            agent = db.query(AIAgent).filter(AIAgent.id == device.agent_id).first()
            if agent:
                name = agent.name or name
                personality = agent.personality or personality
                system_custom = agent.system_prompt
        elif device.assistant_name:
            name = device.assistant_name
            if device.personality:
                personality = device.personality
            if device.system_prompt:
                system_custom = device.system_prompt

    base_instructions = (
        f"You are {name}, a {personality}. "
        f"You are conversing with the user over a real-time voice interface on their Falcon AI smart speaker. "
        f"The user's local city is {city}. "
        "Keep all responses direct, conversational, natural, and under 50 words. "
        "Do not output markdown headings, asterisks, bullet points, or emoji, as your text will be read aloud by a text-to-speech synthesizer. "
        "Support English and Bengali seamlessly according to the user's spoken language."
    )

    if system_custom:
        return f"{base_instructions}\nAdditional agent instructions: {system_custom}"
    return base_instructions


def search_conversations(db: Session, device_id: Optional[str] = None, query: str = "") -> List[Dict[str, Any]]:
    """Search conversation titles and message content."""
    q = db.query(Conversation)
    if device_id:
        q = q.filter(Conversation.device_id == device_id)

    if query:
        pattern = f"%{query}%"
        matching_conv_ids = (
            db.query(Message.conversation_id)
            .filter(Message.content.ilike(pattern))
            .distinct()
            .all()
        )
        matched_ids = [cid[0] for cid in matching_conv_ids]
        q = q.filter(or_(Conversation.title.ilike(pattern), Conversation.id.in_(matched_ids)))

    conversations = q.order_by(desc(Conversation.updated_at)).limit(50).all()
    results = []
    for c in conversations:
        count = db.query(Message).filter(Message.conversation_id == c.id).count()
        results.append({
            "id": c.id,
            "device_id": c.device_id,
            "title": c.title,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "message_count": count
        })
    return results

def get_conversation_messages(db: Session, conversation_id: str) -> List[Dict[str, Any]]:
    """Get all messages for a specific conversation."""
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    return [m.to_dict() for m in msgs]

def delete_conversation(db: Session, conversation_id: str) -> bool:
    """Delete a conversation and its messages."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return False
    db.query(Message).filter(Message.conversation_id == conversation_id).delete()
    db.delete(conv)
    db.commit()
    return True
