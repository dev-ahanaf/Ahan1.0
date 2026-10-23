"""MyVoice OS application package."""
from app.main import app
from app.config import (
    ADMIN_PASSWORD,
    ENROLLMENT_KEY,
    OPENAI_API_KEY,
    BRAVE_SEARCH_API_KEY,
    AI_MODEL,
    DATABASE_PATH,
)
from app.services.weather import fetch_weather
from app.services.asr import transcribe_wav
from app.services.tts import synthesize_wav
from app.services.llm import answer_question, ask_llm

__all__ = [
    "app",
    "ADMIN_PASSWORD",
    "ENROLLMENT_KEY",
    "OPENAI_API_KEY",
    "BRAVE_SEARCH_API_KEY",
    "AI_MODEL",
    "DATABASE_PATH",
    "fetch_weather",
    "transcribe_wav",
    "synthesize_wav",
    "answer_question",
    "ask_llm",
]
