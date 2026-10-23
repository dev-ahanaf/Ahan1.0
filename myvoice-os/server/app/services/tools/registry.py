"""Tool Registry for discovering, verifying permissions, and executing tools."""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from app.services.tools.base import BaseTool, ToolContext, ToolResult
from app.services.tools.clock import ClockTool
from app.services.tools.weather import WeatherTool
from app.services.tools.search import SearchTool
from app.services.tools.timer import TimerTool
from app.services.tools.alarm import AlarmTool
from app.services.tools.device_settings import DeviceSettingsTool
from app.models import Device

logger = logging.getLogger("myvoice.tools")

TOOL_PERMISSION_MAP = {
    "get_current_time": "clock",
    "get_weather": "weather",
    "web_search": "search",
    "manage_timer": "timer",
    "manage_alarm": "alarm",
    "device_settings": "device_settings",
}

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        tools = [
            ClockTool(),
            WeatherTool(),
            SearchTool(),
            TimerTool(),
            AlarmTool(),
            DeviceSettingsTool(),
        ]
        for t in tools:
            self._tools[t.name] = t

    def get_all_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_tools_for_device(self, device: Optional[Device]) -> List[BaseTool]:
        """Return allowed tools based on per-device permission settings."""
        if not device:
            return self.get_all_tools()

        enabled_str = getattr(device, "tools_enabled", "") or "clock,weather,search,timer,alarm,device_settings"
        enabled_permissions = set(p.strip().lower() for p in enabled_str.split(",") if p.strip())

        allowed = []
        for name, tool in self._tools.items():
            perm_key = TOOL_PERMISSION_MAP.get(name, name)
            if perm_key in enabled_permissions:
                allowed.append(tool)

        return allowed

    def get_openai_schemas_for_device(self, device: Optional[Device]) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible function calling schemas for allowed tools."""
        tools = self.get_tools_for_device(device)
        return [t.to_openai_schema() for t in tools]

    async def execute_tool(
        self,
        name: str,
        args: Dict[str, Any],
        context: ToolContext,
        db=None
    ) -> ToolResult:
        """Execute a tool with timeout shielding and error isolation."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' is not recognized",
                voice_summary=f"I do not know how to run the {name} tool."
            )

        # Check device permission
        if db:
            device = db.query(Device).filter(Device.id == context.device_id).first()
            if device:
                perm_key = TOOL_PERMISSION_MAP.get(name, name)
                enabled_str = getattr(device, "tools_enabled", "") or "clock,weather,search,timer,alarm,device_settings"
                enabled_permissions = set(p.strip().lower() for p in enabled_str.split(",") if p.strip())
                if perm_key not in enabled_permissions:
                    return ToolResult(
                        success=False,
                        error=f"Tool '{name}' is disabled in device permissions",
                        voice_summary=f"The {perm_key} tool is currently disabled for this device in the dashboard."
                    )

        try:
            res = await asyncio.wait_for(
                tool.execute(args, context, db=db),
                timeout=tool.timeout_seconds
            )
            return res
        except asyncio.TimeoutError:
            logger.warning(f"Tool {name} timed out after {tool.timeout_seconds}s")
            return ToolResult(
                success=False,
                error=f"Tool {name} timed out",
                voice_summary=f"The request to {name} took too long to complete."
            )
        except Exception as e:
            logger.exception(f"Tool {name} execution failed with error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                voice_summary=f"An error occurred while running the {name} tool."
            )

# Global singleton
tool_registry = ToolRegistry()
