"""Alarm management tool for MyVoice OS."""
import uuid
import zoneinfo
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from app.services.tools.base import BaseTool, ToolContext, ToolResult
from app.models import Alarm

class AlarmTool(BaseTool):
    name = "manage_alarm"
    description = "Create, list, or cancel alarms on the device."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "cancel"],
                "description": "Alarm action to perform: 'create', 'list', or 'cancel'."
            },
            "time_str": {
                "type": "string",
                "description": "Alarm time in 24-hour format HH:MM (e.g. '07:30', '20:00'). Required for 'create'."
            },
            "label": {
                "type": "string",
                "description": "Optional alarm label (e.g. 'Wake up', 'Medicine')."
            },
            "repeat_days": {
                "type": "string",
                "description": "Optional comma-separated days for repeating alarms (e.g. 'mon,tue,wed,thu,fri'). Leave empty for one-off alarm."
            },
            "alarm_id": {
                "type": "string",
                "description": "Optional alarm UUID to cancel when action is 'cancel'."
            }
        },
        "required": ["action"]
    }

    async def execute(self, args: Dict[str, Any], context: ToolContext, db=None) -> ToolResult:
        if db is None:
            return ToolResult(
                success=False,
                error="Database session unavailable",
                voice_summary="I cannot manage alarms without database access."
            )

        action = (args.get("action") or "list").lower()

        if action == "create":
            time_raw = (args.get("time_str") or "").strip()
            if not time_raw or ":" not in time_raw:
                return ToolResult(
                    success=False,
                    error="Invalid time format. Please provide HH:MM.",
                    voice_summary="Please specify a valid alarm time such as 7:30 or 20:00."
                )

            parts = time_raw.split(":")
            try:
                hour = int(parts[0])
                minute = int(parts[1])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError()
            except ValueError:
                return ToolResult(
                    success=False,
                    error="Hour must be 0-23 and minute 0-59.",
                    voice_summary="Invalid alarm time provided. Hours must be between 0 and 23."
                )

            tz_name = context.timezone or "Asia/Dhaka"
            try:
                tz = zoneinfo.ZoneInfo(tz_name)
            except Exception:
                tz = zoneinfo.ZoneInfo("UTC")

            now_local = datetime.now(tz)
            alarm_local = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if alarm_local <= now_local:
                alarm_local += timedelta(days=1)

            next_trigger_utc = alarm_local.astimezone(timezone.utc)
            label = args.get("label") or "Alarm"
            repeat_days = (args.get("repeat_days") or "").strip()
            alarm_id = str(uuid.uuid4())

            new_alarm = Alarm(
                id=alarm_id,
                device_id=context.device_id,
                time_str=f"{hour:02d}:{minute:02d}",
                label=label,
                timezone=tz_name,
                repeat_days=repeat_days,
                created_at=datetime.now(timezone.utc).isoformat(),
                next_trigger_at=next_trigger_utc.isoformat(),
                status="active"
            )
            db.add(new_alarm)
            db.commit()

            formatted_time = alarm_local.strftime("%I:%M %p").lstrip("0")
            summary = f"I have set an alarm for {formatted_time} labeled {label}."
            display = {
                "screen": "alarm",
                "id": alarm_id,
                "time": f"{hour:02d}:{minute:02d}",
                "label": label[:12]
            }

            return ToolResult(
                success=True,
                data={
                    "alarm_id": alarm_id,
                    "time": f"{hour:02d}:{minute:02d}",
                    "label": label,
                    "next_trigger_at": next_trigger_utc.isoformat()
                },
                voice_summary=summary,
                display_data=display
            )

        elif action == "list":
            active_alarms = db.query(Alarm).filter(
                Alarm.device_id == context.device_id,
                Alarm.status == "active"
            ).all()

            if not active_alarms:
                return ToolResult(
                    success=True,
                    data={"alarms": []},
                    voice_summary="You do not have any active alarms."
                )

            alarm_list_str = ", ".join([f"{a.time_str} ({a.label})" for a in active_alarms])
            summary = f"You have active alarms at: {alarm_list_str}."
            return ToolResult(
                success=True,
                data={"alarms": [a.to_dict() for a in active_alarms]},
                voice_summary=summary
            )

        elif action == "cancel":
            alarm_id = args.get("alarm_id")
            query = db.query(Alarm).filter(
                Alarm.device_id == context.device_id,
                Alarm.status == "active"
            )
            if alarm_id:
                query = query.filter(Alarm.id == alarm_id)

            alarm_to_cancel = query.first()
            if not alarm_to_cancel:
                return ToolResult(
                    success=False,
                    error="No active alarm found to cancel",
                    voice_summary="I did not find any active alarm to cancel."
                )

            alarm_to_cancel.status = "cancelled"
            db.commit()

            return ToolResult(
                success=True,
                data={"cancelled_alarm_id": alarm_to_cancel.id},
                voice_summary=f"Cancelled your {alarm_to_cancel.time_str} alarm for {alarm_to_cancel.label}."
            )

        else:
            return ToolResult(
                success=False,
                error=f"Unknown alarm action '{action}'",
                voice_summary=f"I do not know how to perform alarm action '{action}'."
            )
