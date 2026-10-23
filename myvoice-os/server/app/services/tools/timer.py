"""Timer management tool for MyVoice OS."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from app.services.tools.base import BaseTool, ToolContext, ToolResult
from app.models import Timer

class TimerTool(BaseTool):
    name = "manage_timer"
    description = "Set, list, or cancel countdown timers on the device."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["set", "list", "cancel"],
                "description": "The timer action to perform: 'set', 'list', or 'cancel'."
            },
            "duration_seconds": {
                "type": "integer",
                "description": "Duration in seconds when setting a timer (e.g. 120 for 2 minutes). Required for 'set'."
            },
            "label": {
                "type": "string",
                "description": "Optional label or description for the timer (e.g. 'Tea', 'Pasta', 'Study')."
            },
            "timer_id": {
                "type": "string",
                "description": "Optional timer UUID to cancel when action is 'cancel'."
            }
        },
        "required": ["action"]
    }

    async def execute(self, args: Dict[str, Any], context: ToolContext, db=None) -> ToolResult:
        if db is None:
            return ToolResult(
                success=False,
                error="Database session unavailable",
                voice_summary="I cannot manage timers without database access."
            )

        action = (args.get("action") or "list").lower()

        if action == "set":
            duration = int(args.get("duration_seconds") or 0)
            if duration <= 0:
                return ToolResult(
                    success=False,
                    error="Duration must be greater than zero",
                    voice_summary="Please specify a timer duration greater than zero seconds."
                )

            label = args.get("label") or "Timer"
            now = datetime.now(timezone.utc)
            expires = now + timedelta(seconds=duration)
            timer_id = str(uuid.uuid4())

            new_timer = Timer(
                id=timer_id,
                device_id=context.device_id,
                label=label,
                duration_seconds=duration,
                created_at=now.isoformat(),
                expires_at=expires.isoformat(),
                status="active",
                alert_acknowledged=0
            )
            db.add(new_timer)
            db.commit()

            mins = duration // 60
            secs = duration % 60
            dur_text = ""
            if mins > 0 and secs > 0:
                dur_text = f"{mins} minute{'s' if mins != 1 else ''} and {secs} second{'s' if secs != 1 else ''}"
            elif mins > 0:
                dur_text = f"{mins} minute{'s' if mins != 1 else ''}"
            else:
                dur_text = f"{secs} second{'s' if secs != 1 else ''}"

            summary = f"I have set a timer for {dur_text} labeled {label}."
            display = {
                "screen": "timer",
                "id": timer_id,
                "label": label[:12],
                "duration_seconds": duration,
                "expires_at": expires.isoformat()
            }

            return ToolResult(
                success=True,
                data={
                    "timer_id": timer_id,
                    "label": label,
                    "duration_seconds": duration,
                    "expires_at": expires.isoformat()
                },
                voice_summary=summary,
                display_data=display
            )

        elif action == "list":
            active_timers = db.query(Timer).filter(
                Timer.device_id == context.device_id,
                Timer.status == "active"
            ).all()

            if not active_timers:
                return ToolResult(
                    success=True,
                    data={"timers": []},
                    voice_summary="You do not have any active timers."
                )

            summaries = []
            now = datetime.now(timezone.utc)
            for t in active_timers:
                exp = datetime.fromisoformat(t.expires_at)
                rem = max(0, int((exp - now).total_seconds()))
                rem_m = rem // 60
                rem_s = rem % 60
                summaries.append(f"{t.label} with {rem_m}m {rem_s}s remaining")

            summary = "You have active timers: " + ", ".join(summaries) + "."
            return ToolResult(
                success=True,
                data={"timers": [t.to_dict() for t in active_timers]},
                voice_summary=summary
            )

        elif action == "cancel":
            timer_id = args.get("timer_id")
            query = db.query(Timer).filter(
                Timer.device_id == context.device_id,
                Timer.status == "active"
            )
            if timer_id:
                query = query.filter(Timer.id == timer_id)

            timer_to_cancel = query.first()
            if not timer_to_cancel:
                return ToolResult(
                    success=False,
                    error="No active timer found to cancel",
                    voice_summary="I did not find any active timer to cancel."
                )

            timer_to_cancel.status = "cancelled"
            db.commit()

            return ToolResult(
                success=True,
                data={"cancelled_timer_id": timer_to_cancel.id},
                voice_summary=f"Cancelled your timer for {timer_to_cancel.label}."
            )

        else:
            return ToolResult(
                success=False,
                error=f"Unknown timer action '{action}'",
                voice_summary=f"I do not know how to perform timer action '{action}'."
            )
