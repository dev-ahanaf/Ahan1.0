"""Scheduler service for background timer and alarm monitoring and alert dispatch."""
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from app.db import get_db_session
from app.models import Timer, Alarm, Device
from app.services.providers.manager import ProviderManager

logger = logging.getLogger("myvoice.scheduler")

class SchedulerService:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Background timer and alarm scheduler started.")

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Background timer and alarm scheduler stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.check_due_items()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            await asyncio.sleep(1.0)

    async def check_due_items(self):
        """Check for expired timers and triggered alarms in database."""
        db = get_db_session()
        try:
            now_utc = datetime.now(timezone.utc)
            now_iso = now_utc.isoformat()

            # 1. Check expired timers
            expired_timers = db.query(Timer).filter(
                Timer.status == "active",
                Timer.expires_at <= now_iso
            ).all()

            for t in expired_timers:
                t.status = "completed"
                db.commit()
                await self._dispatch_timer_alert(t)

            # 2. Check triggered alarms
            triggered_alarms = db.query(Alarm).filter(
                Alarm.status == "active",
                Alarm.next_trigger_at <= now_iso
            ).all()

            for a in triggered_alarms:
                # If repeating, calculate next trigger
                if a.repeat_days:
                    # Advance to next day at same time
                    try:
                        curr_next = datetime.fromisoformat(a.next_trigger_at)
                        a.next_trigger_at = (curr_next + timedelta(days=1)).isoformat()
                    except Exception:
                        a.status = "dismissed"
                else:
                    a.status = "dismissed"
                db.commit()
                await self._dispatch_alarm_alert(a)

        finally:
            db.close()

    check_timers_and_alarms = check_due_items

    async def _dispatch_timer_alert(self, timer: Timer):
        from app.routers.ws_device import ACTIVE_SESSIONS
        session = ACTIVE_SESSIONS.get(timer.device_id)
        if not session or not session.websocket:
            logger.info(f"Timer {timer.id} expired for offline device {timer.device_id}")
            return

        alert_text = f"Your timer for {timer.label} has finished."
        try:
            # Send alert JSON frame
            await session.websocket.send_text(json.dumps({
                "type": "alert",
                "kind": "timer",
                "id": timer.id,
                "label": timer.label,
                "text": alert_text
            }))

            # Send display event
            await session.websocket.send_text(json.dumps({
                "type": "display",
                "screen": "alert",
                "data": {
                    "kind": "timer",
                    "label": timer.label[:12],
                    "text": "TIME'S UP"
                }
            }))

            # Synthesize and stream spoken alert audio
            db = get_db_session()
            device = db.query(Device).filter(Device.id == timer.device_id).first()
            if device:
                tts_provider, tts_voice = ProviderManager.resolve_tts(db, device)
                await session.websocket.send_text(json.dumps({
                    "type": "tts_start",
                    "codec": "pcm16",
                    "sample_rate": 16000,
                    "channels": 1
                }))
                session.state = "SPEAKING"
                async for chunk in tts_provider.synthesize_stream(
                    alert_text,
                    voice=tts_voice,
                    language=device.language
                ):
                    await session.websocket.send_bytes(chunk)
                await session.websocket.send_text(json.dumps({"type": "tts_stop"}))
                session.state = "IDLE"
            db.close()
        except Exception as e:
            logger.warning(f"Failed to dispatch timer alert to {timer.device_id}: {e}")

    async def _dispatch_alarm_alert(self, alarm: Alarm):
        from app.routers.ws_device import ACTIVE_SESSIONS
        session = ACTIVE_SESSIONS.get(alarm.device_id)
        if not session or not session.websocket:
            logger.info(f"Alarm {alarm.id} triggered for offline device {alarm.device_id}")
            return

        alert_text = f"Your alarm for {alarm.label} at {alarm.time_str} is ringing."
        try:
            await session.websocket.send_text(json.dumps({
                "type": "alert",
                "kind": "alarm",
                "id": alarm.id,
                "label": alarm.label,
                "text": alert_text
            }))

            await session.websocket.send_text(json.dumps({
                "type": "display",
                "screen": "alert",
                "data": {
                    "kind": "alarm",
                    "label": alarm.label[:12],
                    "text": alarm.time_str
                }
            }))

            db = get_db_session()
            device = db.query(Device).filter(Device.id == alarm.device_id).first()
            if device:
                tts_provider, tts_voice = ProviderManager.resolve_tts(db, device)
                await session.websocket.send_text(json.dumps({
                    "type": "tts_start",
                    "codec": "pcm16",
                    "sample_rate": 16000,
                    "channels": 1
                }))
                session.state = "SPEAKING"
                async for chunk in tts_provider.synthesize_stream(
                    alert_text,
                    voice=tts_voice,
                    language=device.language
                ):
                    await session.websocket.send_bytes(chunk)
                await session.websocket.send_text(json.dumps({"type": "tts_stop"}))
                session.state = "IDLE"
            db.close()
        except Exception as e:
            logger.warning(f"Failed to dispatch alarm alert to {alarm.device_id}: {e}")

# Global scheduler singleton
scheduler_service = SchedulerService()
