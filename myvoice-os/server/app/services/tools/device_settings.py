"""Device hardware settings tool for MyVoice OS."""
from typing import Dict, Any
from app.services.tools.base import BaseTool, ToolContext, ToolResult
from app.models import Device

class DeviceSettingsTool(BaseTool):
    name = "device_settings"
    description = "Adjust hardware settings on the device, such as speaker volume, OLED screen brightness, and display mode."
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["set_volume", "set_brightness", "set_display_mode", "get_status"],
                "description": "Setting action to execute."
            },
            "volume": {
                "type": "integer",
                "description": "Speaker volume percentage from 0 to 100 (for 'set_volume')."
            },
            "brightness": {
                "type": "integer",
                "description": "OLED screen brightness level from 0 to 255 (for 'set_brightness')."
            },
            "display_mode": {
                "type": "string",
                "enum": ["clock", "blank"],
                "description": "Idle screen display mode (for 'set_display_mode')."
            }
        },
        "required": ["action"]
    }

    async def execute(self, args: Dict[str, Any], context: ToolContext, db=None) -> ToolResult:
        if db is None:
            return ToolResult(
                success=False,
                error="Database session unavailable",
                voice_summary="I cannot adjust hardware settings without database access."
            )

        device = db.query(Device).filter(Device.id == context.device_id).first()
        if not device:
            return ToolResult(
                success=False,
                error=f"Device {context.device_id} not found in database",
                voice_summary="Device profile not found."
            )

        action = (args.get("action") or "get_status").lower()

        if action == "set_volume":
            vol = args.get("volume")
            if vol is None or not (0 <= int(vol) <= 100):
                return ToolResult(
                    success=False,
                    error="Volume must be an integer between 0 and 100",
                    voice_summary="Please specify a volume percentage between 0 and 100."
                )
            device.speaker_volume = int(vol)
            device.config_version += 1
            db.commit()

            return ToolResult(
                success=True,
                data={"speaker_volume": device.speaker_volume, "config_version": device.config_version},
                voice_summary=f"Speaker volume set to {device.speaker_volume} percent."
            )

        elif action == "set_brightness":
            bri = args.get("brightness")
            if bri is None or not (0 <= int(bri) <= 255):
                return ToolResult(
                    success=False,
                    error="Brightness must be an integer between 0 and 255",
                    voice_summary="Please specify a brightness level between 0 and 255."
                )
            device.oled_brightness = int(bri)
            device.config_version += 1
            db.commit()

            pct = int((device.oled_brightness / 255.0) * 100)
            return ToolResult(
                success=True,
                data={"oled_brightness": device.oled_brightness, "config_version": device.config_version},
                voice_summary=f"Screen brightness set to {pct} percent."
            )

        elif action == "set_display_mode":
            mode = (args.get("display_mode") or "").lower()
            if mode not in ["clock", "blank"]:
                return ToolResult(
                    success=False,
                    error="Display mode must be 'clock' or 'blank'",
                    voice_summary="Display mode must be either clock or blank."
                )
            device.idle_display_mode = mode
            device.config_version += 1
            db.commit()

            return ToolResult(
                success=True,
                data={"idle_display_mode": device.idle_display_mode, "config_version": device.config_version},
                voice_summary=f"Screen display mode changed to {mode}."
            )

        elif action == "get_status":
            summary = (
                f"Device {device.name} is online. Speaker volume is {device.speaker_volume} percent, "
                f"screen brightness is {device.oled_brightness}, and city is set to {device.city}."
            )
            return ToolResult(
                success=True,
                data=device.to_dict(),
                voice_summary=summary
            )

        else:
            return ToolResult(
                success=False,
                error=f"Unknown settings action '{action}'",
                voice_summary=f"I do not recognize setting action '{action}'."
            )
