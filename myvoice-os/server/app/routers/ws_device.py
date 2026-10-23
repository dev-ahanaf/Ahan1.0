"""Real-time WebSocket device communication router (/ws/device)."""
import asyncio
import hashlib
import json
import re
import time
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.db import get_db, get_db_session
from app.models import Device
from app.services.providers.manager import ProviderManager
from app.services.memory import (
    get_or_create_conversation,
    record_message,
    get_conversation_context,
    build_system_prompt
)
from app.services.llm import answer_question, WEATHER_WORDS, TIME_WORDS, SEARCH_PREFIX
from app.services.audio_utils import detect_energy_vad

router = APIRouter(tags=["websocket"])

# Active sessions: device_id -> SessionState
ACTIVE_SESSIONS: Dict[str, "DeviceSession"] = {}

class DeviceSession:
    """Encapsulates active WebSocket connection and streaming state for a device."""

    def __init__(self, device_id: str, websocket: WebSocket):
        self.device_id = device_id
        self.websocket = websocket
        self.session_id = str(uuid.uuid4())
        self.state = "IDLE"  # IDLE, LISTENING, THINKING, SPEAKING
        self.audio_buffer = bytearray()
        self.current_task: Optional[asyncio.Task] = None
        self.connected_at = time.time()
        self.last_interaction = time.time()
        self.dropped_frames = 0
        self.vad_silence_count = 0
        self.last_metrics: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "device_id": self.device_id,
            "state": self.state,
            "connected_at": self.connected_at,
            "last_interaction": self.last_interaction,
            "dropped_frames": self.dropped_frames,
            "last_metrics": self.last_metrics
        }


def authenticate_device(db: Session, device_id: str, token: str) -> Optional[Device]:
    """Validate device credentials against hashed token."""
    # Allow browser voice playground simulator
    if token == "playground-token":
        sim = db.query(Device).filter(Device.id == device_id).first()
        if not sim:
            sim = Device(
                id=device_id,
                name="Browser Voice Simulator",
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                paired=1,
                created_at=datetime.utcnow().isoformat(),
                firmware="1.0.0-sim",
                city="Dhaka",
                latitude=23.8103,
                longitude=90.4125,
                timezone="Asia/Dhaka",
                config_version=1,
                language="en",
                oled_brightness=128,
                idle_display_mode="clock",
                clock_format="24h",
                speaker_volume=80,
                mic_gain=50,
                wake_mode="button",
                weather_enabled=1,
                search_enabled=1,
                timers_enabled=1,
                revoked=0,
                assistant_name="XiaoZhi",
                personality="helpful, concise voice assistant"
            )
            db.add(sim)
            db.commit()
            db.refresh(sim)
        return sim

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device or not device.paired or device.revoked:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if token_hash != device.token_hash:
        return None
    return device


def split_sentences(text: str) -> list[str]:
    """Split streamed text into natural sentence-level clauses for TTS streaming."""
    # Split by period, question mark, exclamation, or newline followed by space
    parts = re.split(r"([.?!:\n]+(?:\s+|$))", text)
    sentences = []
    current = ""
    for part in parts:
        current += part
        if any(punct in part for punct in (".", "?", "!", "\n")):
            if current.strip():
                sentences.append(current.strip())
            current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences


@router.websocket("/ws/device")
async def websocket_device_endpoint(
    websocket: WebSocket,
    device_id: Optional[str] = None,
    token: Optional[str] = None
):
    """Bidirectional real-time voice streaming endpoint."""
    db: Session = get_db_session()
    authenticated_device: Optional[Device] = None

    try:
        # Step 1: Authentication via query parameters or initial hello frame
        if device_id and token:
            authenticated_device = authenticate_device(db, device_id, token)
            if not authenticated_device:
                await websocket.close(code=4001)
                return

        if not authenticated_device:
            # If not in query params, accept connection temporarily to read hello frame
            await websocket.accept()
            try:
                first_msg = await asyncio.wait_for(websocket.receive(), timeout=5.0)
                if first_msg.get("type") == "websocket.receive" and "text" in first_msg:
                    payload = json.loads(first_msg["text"])
                    if payload.get("type") == "hello":
                        cand_id = payload.get("device_id") or device_id
                        cand_token = payload.get("token") or token
                        if cand_id and cand_token:
                            device_id = cand_id
                            authenticated_device = authenticate_device(db, cand_id, cand_token)
            except Exception:
                pass

            if not authenticated_device or not device_id:
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "code": "AUTH_FAILED",
                        "message": "Invalid or missing device credentials"
                    }))
                    await websocket.close(code=4001)
                except Exception:
                    pass
                return
        else:
            await websocket.accept()

        # Step 2: Enforce single active session per physical device
        if device_id in ACTIVE_SESSIONS:
            old_session = ACTIVE_SESSIONS[device_id]
            if old_session.current_task and not old_session.current_task.done():
                old_session.current_task.cancel()
            try:
                await old_session.websocket.close(code=4009)
            except Exception:
                pass

        session = DeviceSession(device_id, websocket)
        ACTIVE_SESSIONS[device_id] = session

        # Send hello_ack
        device_dict = authenticated_device.to_dict()
        await websocket.send_text(json.dumps({
            "type": "hello_ack",
            "session_id": session.session_id,
            "config": {
                "language": device_dict.get("language", "en"),
                "speaker_volume": device_dict.get("speaker_volume", 80),
                "mic_gain": device_dict.get("mic_gain", 50),
                "idle_display_mode": device_dict.get("idle_display_mode", "clock"),
                "clock_format": device_dict.get("clock_format", "24h"),
                "assistant_name": device_dict.get("assistant_name", "MyVoice")
            },
            "config_version": authenticated_device.config_version
        }))

        # Step 3: Event loop for incoming text and binary audio frames
        listen_start_time = 0.0

        while True:
            try:
                msg = await websocket.receive()
            except Exception:
                break

            if msg.get("type") == "websocket.disconnect":
                break

            session.last_interaction = time.time()

            # Handle Binary Audio Frames (Device -> Server)
            if "bytes" in msg and msg["bytes"]:
                data = msg["bytes"]
                if session.state == "LISTENING":
                    # Max 30 seconds of 16kHz 16-bit mono PCM = 960,000 bytes
                    if len(session.audio_buffer) + len(data) > 960000:
                        session.dropped_frames += 1
                        continue

                    session.audio_buffer.extend(data)

                    # Energy VAD (if device vad_mode is set to 'vad')
                    if authenticated_device.vad_mode == "vad":
                        is_speech = detect_energy_vad(data, threshold=400.0)
                        if not is_speech:
                            session.vad_silence_count += 1
                            # 15 consecutive silent 60ms frames = 900 ms silence
                            if session.vad_silence_count >= 15 and len(session.audio_buffer) > 16000:
                                session.vad_silence_count = 0
                                # Auto-trigger end of speech
                                session.current_task = asyncio.create_task(
                                    process_voice_turn(session, authenticated_device, listen_start_time)
                                )
                        else:
                            session.vad_silence_count = 0

            # Handle Text JSON Control Frames
            elif "text" in msg and msg["text"]:
                try:
                    payload = json.loads(msg["text"])
                    mtype = payload.get("type")

                    if mtype == "listen_start":
                        session.state = "LISTENING"
                        session.audio_buffer.clear()
                        session.vad_silence_count = 0
                        listen_start_time = time.time()

                    elif mtype == "listen_stop":
                        if session.state == "LISTENING":
                            session.current_task = asyncio.create_task(
                                process_voice_turn(session, authenticated_device, listen_start_time)
                            )

                    elif mtype == "abort":
                        # Barge-In: Cancel active pipeline task immediately
                        if session.current_task and not session.current_task.done():
                            session.current_task.cancel()
                        session.audio_buffer.clear()
                        session.state = "IDLE"
                        await websocket.send_text(json.dumps({"type": "abort_ack"}))

                    elif mtype == "status_report":
                        # Record periodic device telemetry
                        try:
                            from app.models import DeviceTelemetry
                            db_telemetry = get_db_session()
                            t_row = DeviceTelemetry(
                                id=str(uuid.uuid4()),
                                device_id=authenticated_device.id,
                                rssi=payload.get("rssi"),
                                free_heap=payload.get("free_heap"),
                                min_free_heap=payload.get("min_free_heap"),
                                uptime_s=payload.get("uptime_s"),
                                dropped_frames=payload.get("dropped_frames", 0),
                                error_count=payload.get("error_count", 0),
                                created_at=datetime.now(timezone.utc).isoformat()
                            )
                            db_telemetry.add(t_row)
                            db_telemetry.commit()
                            db_telemetry.close()
                        except Exception:
                            pass

                    elif mtype == "alert_ack":
                        # Acknowledge timer or alarm alert receipt
                        alert_id = payload.get("id")
                        if alert_id:
                            try:
                                from app.models import Timer
                                db_ack = get_db_session()
                                t_ack = db_ack.query(Timer).filter(Timer.id == alert_id).first()
                                if t_ack:
                                    t_ack.alert_acknowledged = 1
                                    db_ack.commit()
                                db_ack.close()
                            except Exception:
                                pass

                    elif mtype == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))

                except json.JSONDecodeError:
                    pass

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception:
        pass
    finally:
        if device_id and device_id in ACTIVE_SESSIONS:
            if ACTIVE_SESSIONS[device_id].session_id == session.session_id:
                del ACTIVE_SESSIONS[device_id]
        db.close()


async def process_voice_turn(
    session: DeviceSession,
    device: Device,
    listen_start_time: float
):
    """Execute end-to-end voice pipeline: STT -> LLM streaming -> sentence chunking -> TTS streaming."""
    session.state = "THINKING"
    t_start = time.time()
    upload_duration_ms = int((t_start - listen_start_time) * 1000) if listen_start_time > 0 else 0

    audio_bytes = bytes(session.audio_buffer)
    session.audio_buffer.clear()

    if len(audio_bytes) < 1600:
        # Less than 50 ms of audio; return to IDLE
        session.state = "IDLE"
        return

    db = get_db_session()
    try:
        # Step A: Automated Speech Recognition (ASR)
        t_stt_start = time.time()
        asr_provider = ProviderManager.resolve_asr(db, device)
        transcript = await asr_provider.transcribe(audio_bytes, language=device.language)
        t_stt_end = time.time()
        stt_latency_ms = int((t_stt_end - t_stt_start) * 1000)

        transcript = transcript.strip()
        if not transcript:
            session.state = "IDLE"
            await session.websocket.send_text(json.dumps({
                "type": "stt",
                "text": "",
                "final": True
            }))
            return

        # Emit stt event
        await session.websocket.send_text(json.dumps({
            "type": "stt",
            "text": transcript,
            "final": True
        }))

        # Step B: Conversation Memory & Intent Routing
        conv = get_or_create_conversation(db, device.id)
        record_message(db, conv.id, device.id, role="user", content=transcript)

        q_lower = transcript.lower()
        reply_text = ""
        llm_first_token_ms: Optional[int] = None
        tts_first_audio_ms: Optional[int] = None

        tts_provider, tts_voice = ProviderManager.resolve_tts(db, device)

        # Notify device that TTS playback will begin
        await session.websocket.send_text(json.dumps({
            "type": "tts_start",
            "codec": "pcm16",
            "sample_rate": 16000,
            "channels": 1
        }))
        session.state = "SPEAKING"

        async def stream_sentence_tts(sentence: str):
            nonlocal tts_first_audio_ms
            if not sentence.strip():
                return
            async for audio_chunk in tts_provider.synthesize_stream(
                sentence,
                voice=tts_voice,
                language=device.language
            ):
                if tts_first_audio_ms is None:
                    tts_first_audio_ms = int((time.time() - t_start) * 1000)
                await session.websocket.send_bytes(audio_chunk)

        # Step C: Modular Tool Intent Matching
        from app.services.tools import tool_registry, ToolContext
        tool_ctx = ToolContext(
            device_id=device.id,
            city=device.city,
            latitude=device.latitude,
            longitude=device.longitude,
            timezone=device.timezone,
            speaker_volume=device.speaker_volume,
            oled_brightness=device.oled_brightness,
            idle_display_mode=device.idle_display_mode,
            language=device.language
        )

        tool_to_call = None
        tool_args = {}

        # 1. Timer Intent
        if any(k in q_lower for k in ["timer", "таймер", "টাইমার"]):
            if any(k in q_lower for k in ["cancel", "stop", "বাতিল", "বন্ধ"]):
                tool_to_call = "manage_timer"
                tool_args = {"action": "cancel"}
            elif any(k in q_lower for k in ["list", "check", "কতক্ষণ"]):
                tool_to_call = "manage_timer"
                tool_args = {"action": "list"}
            else:
                m_sec = re.search(r'(\d+)\s*(?:second|sec|সেকেন্ড)', q_lower)
                m_min = re.search(r'(\d+)\s*(?:minute|min|মিনিট)', q_lower)
                sec = int(m_sec.group(1)) if m_sec else 0
                minutes = int(m_min.group(1)) if m_min else 0
                total_sec = (minutes * 60) + sec
                if total_sec == 0:
                    m_num = re.search(r'(\d+)', q_lower)
                    total_sec = int(m_num.group(1)) * 60 if m_num else 120
                tool_to_call = "manage_timer"
                tool_args = {"action": "set", "duration_seconds": total_sec, "label": "Timer"}

        # 2. Alarm Intent
        elif any(k in q_lower for k in ["alarm", "অ্যালার্ম", "wake me up", "remind me at"]):
            if any(k in q_lower for k in ["cancel", "stop", "বাতিল"]):
                tool_to_call = "manage_alarm"
                tool_args = {"action": "cancel"}
            elif any(k in q_lower for k in ["list", "check"]):
                tool_to_call = "manage_alarm"
                tool_args = {"action": "list"}
            else:
                m_time = re.search(r'(\d{1,2}):(\d{2})', q_lower)
                m_hour = re.search(r'(\d{1,2})\s*(?:am|pm|a\.m\.|p\.m\.)', q_lower)
                time_str = "08:00"
                if m_time:
                    time_str = f"{int(m_time.group(1)):02d}:{int(m_time.group(2)):02d}"
                elif m_hour:
                    h = int(m_hour.group(1))
                    if "pm" in q_lower and h < 12:
                        h += 12
                    elif "am" in q_lower and h == 12:
                        h = 0
                    time_str = f"{h:02d}:00"
                tool_to_call = "manage_alarm"
                tool_args = {"action": "create", "time_str": time_str, "label": "Alarm"}

        # 3. Clock / Date Intent
        elif any(k in q_lower for k in ["time", "clock", "date", "day of", "সময়", "কয়টা বাজে", "তারিখ"]):
            tool_to_call = "get_current_time"
            tool_args = {}

        # 4. Weather Intent
        elif any(k in q_lower for k in ["weather", "temperature", "forecast", "rain", "আবহাওয়া", "বৃষ্টি", "তাপমাত্রা", "গরম"]):
            tool_to_call = "get_weather"
            m_city = re.search(r'(?:in|for|of)\s+([A-Za-z]+)', transcript, re.IGNORECASE)
            city_arg = m_city.group(1).capitalize() if m_city else device.city
            tool_args = {"city": city_arg}

        # 5. Device Settings Intent
        elif any(k in q_lower for k in ["volume", "brightness", "শব্দ", "উজ্জ্বলতা"]):
            m_pct = re.search(r'(\d+)', q_lower)
            val = int(m_pct.group(1)) if m_pct else None
            if "volume" in q_lower or "শব্দ" in q_lower:
                tool_to_call = "device_settings"
                tool_args = {"action": "set_volume", "volume": val if val is not None else 80}
            elif "brightness" in q_lower or "উজ্জ্বলতা" in q_lower:
                tool_to_call = "device_settings"
                bri_val = int(val * 2.55) if val is not None else 128
                tool_args = {"action": "set_brightness", "brightness": bri_val}

        # 6. Web Search Intent
        elif any(q_lower.startswith(p) for p in ["search for", "search", "look up", "google", "খোঁজ"]) or "news about" in q_lower:
            clean_query = re.sub(r'^(search for|search|look up|google|খোঁজ)\s*', '', transcript, flags=re.IGNORECASE).strip()
            tool_to_call = "web_search"
            tool_args = {"query": clean_query or transcript}

        # Execute Tool if matched
        if tool_to_call:
            tool_res = await tool_registry.execute_tool(tool_to_call, tool_args, tool_ctx, db=db)
            reply_text = tool_res.voice_summary

            # Emit display frame to device if tool provides screen data
            if tool_res.display_data:
                await session.websocket.send_text(json.dumps({
                    "type": "display",
                    "screen": tool_res.display_data.get("screen", "status"),
                    "data": tool_res.display_data
                }))

            llm_first_token_ms = int((time.time() - t_start) * 1000)
            await session.websocket.send_text(json.dumps({
                "type": "llm",
                "delta": reply_text,
                "final": True
            }))
            await stream_sentence_tts(reply_text)

        else:
            # LLM conversational streaming path with sentence chunking

            llm_provider, llm_model = ProviderManager.resolve_llm(db, device)
            system_prompt = build_system_prompt(device)
            history = get_conversation_context(db, conv.id, history_length=device.history_length)

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)

            accumulated_tokens = []
            sentence_buffer = ""

            t_llm_start = time.time()
            async for token in llm_provider.stream_chat(messages, model=llm_model):
                if llm_first_token_ms is None:
                    llm_first_token_ms = int((time.time() - t_llm_start) * 1000)

                accumulated_tokens.append(token)
                sentence_buffer += token

                await session.websocket.send_text(json.dumps({
                    "type": "llm",
                    "delta": token,
                    "final": False
                }))

                # Check if a sentence boundary was reached
                sentences = split_sentences(sentence_buffer)
                if len(sentences) > 1:
                    ready_sentence = sentences[0]
                    sentence_buffer = sentence_buffer[len(ready_sentence):].lstrip()
                    await stream_sentence_tts(ready_sentence)

            # Flush any remaining tokens in buffer
            if sentence_buffer.strip():
                await stream_sentence_tts(sentence_buffer.strip())

            reply_text = "".join(accumulated_tokens)
            await session.websocket.send_text(json.dumps({
                "type": "llm",
                "delta": "",
                "final": True
            }))

        # Send tts_stop to conclude playback
        await session.websocket.send_text(json.dumps({"type": "tts_stop"}))
        session.state = "IDLE"

        # Step C: Latency Telemetry and Persistence
        total_time_ms = int((time.time() - t_start) * 1000)
        metrics = {
            "upload_duration_ms": upload_duration_ms,
            "stt_latency_ms": stt_latency_ms,
            "llm_first_token_ms": llm_first_token_ms or 0,
            "tts_first_audio_ms": tts_first_audio_ms or 0,
            "total_turnaround_ms": total_time_ms,
            "asr_provider": type(asr_provider).__name__,
            "tts_provider": type(tts_provider).__name__
        }
        session.last_metrics = metrics

        record_message(
            db,
            conv.id,
            device.id,
            role="assistant",
            content=reply_text,
            latency_ms=total_time_ms,
            provider_info=metrics
        )

    except asyncio.CancelledError:
        session.state = "IDLE"
        try:
            await session.websocket.send_text(json.dumps({"type": "tts_stop"}))
        except Exception:
            pass
        raise
    except Exception as exc:
        session.state = "IDLE"
        try:
            await session.websocket.send_text(json.dumps({
                "type": "error",
                "code": "PIPELINE_ERROR",
                "message": str(exc)
            }))
            await session.websocket.send_text(json.dumps({"type": "tts_stop"}))
        except Exception:
            pass
    finally:
        db.close()
