"""Clock and Date tool for MyVoice OS."""
from datetime import datetime
import zoneinfo
from typing import Dict, Any
from app.services.tools.base import BaseTool, ToolContext, ToolResult

class ClockTool(BaseTool):
    name = "get_current_time"
    description = "Get the current time, date, day of the week, and timezone for the device."
    parameters_schema = {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Optional IANA timezone name (e.g. 'Asia/Dhaka', 'UTC', 'America/New_York'). Defaults to device timezone."
            }
        },
        "required": []
    }

    async def execute(self, args: Dict[str, Any], context: ToolContext, db=None) -> ToolResult:
        tz_name = args.get("timezone") or context.timezone or "Asia/Dhaka"
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")
            tz_name = "UTC"

        now = datetime.now(tz)
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d, %Y")
        day_of_week = now.strftime("%A")

        summary = f"It is {time_str} on {date_str} in {tz_name}."
        display = {
            "screen": "clock",
            "time": now.strftime("%H:%M"),
            "date": now.strftime("%a, %b %d"),
            "timezone": tz_name
        }

        return ToolResult(
            success=True,
            data={
                "time": time_str,
                "time_24h": now.strftime("%H:%M:%S"),
                "date": date_str,
                "day_of_week": day_of_week,
                "timezone": tz_name,
                "iso": now.isoformat(),
            },
            voice_summary=summary,
            display_data=display
        )
