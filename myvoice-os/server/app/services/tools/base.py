"""Base definitions for the MyVoice OS Tool and Skill System."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel

class ToolContext(BaseModel):
    device_id: str
    city: str = "Dhaka"
    latitude: float = 23.8103
    longitude: float = 90.4125
    timezone: str = "Asia/Dhaka"
    speaker_volume: int = 80
    oled_brightness: int = 128
    idle_display_mode: str = "clock"
    language: str = "en"

    class Config:
        arbitrary_types_allowed = True


class ToolResult(BaseModel):
    success: bool
    data: Dict[str, Any] = {}
    voice_summary: str
    display_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseTool(ABC):
    """Abstract base class for all MyVoice OS tools."""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    enabled_by_default: bool = True
    timeout_seconds: float = 5.0

    @abstractmethod
    async def execute(self, args: Dict[str, Any], context: ToolContext, db=None) -> ToolResult:
        """Execute the tool action."""
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            }
        }
