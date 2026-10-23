"""Language model completions and multi-domain intent routing."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from app.config import OPENAI_API_KEY, AI_MODEL
from app.services.weather import fetch_weather
from app.services.search import search_brave

WEATHER_WORDS = ("weather", "temperature", "forecast", "আবহাও", "তাপমাত্রা")
TIME_WORDS = ("time", "clock", "what's the date", "date today", "কয়টা", "কটা", "সময়", "সময়", "তারিখ")
SEARCH_PREFIX = re.compile(
    r"^(?:please\s+)?(?:search(?:\s+(?:for|the web for))?|look up|find online|সার্চ(?:\s+করো)?|খুঁজে দেখো)\s*[:：]?\s*",
    re.I
)

def fallback_profile() -> dict:
    """Default fallback device profile for test queries."""
    return {
        "city": "Dhaka",
        "latitude": 23.8103,
        "longitude": 90.4125,
        "timezone": "Asia/Dhaka"
    }

async def ask_llm(prompt: str) -> str:
    """Send prompt to OpenAI Chat Completion model."""
    if not OPENAI_API_KEY:
        return "General AI questions require OPENAI_API_KEY. Clock and weather commands work without it."
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": AI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concise, friendly voice assistant. Respond in the user's language. Keep responses under 70 words. Do not claim to have live web access."
                    },
                    {"role": "user", "content": prompt}
                ],
                "max_completion_tokens": 180
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"] or "I don't have an answer yet."

async def answer_question(question: str, profile: dict) -> str:
    """Route question across weather, clock, web search, or general LLM."""
    q = question.lower().strip()
    try:
        if any(k in q for k in WEATHER_WORDS):
            w = await fetch_weather(profile)
            return f"In {w['city']}, it's {w['temperature_c']} degrees Celsius with {w['conditions']}. Wind is {w['wind_kmh']} kilometers per hour."
        if any(k in q for k in TIME_WORDS):
            now = datetime.now(ZoneInfo(profile["timezone"]))
            return f"In {profile['city']}, it is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."
        m = SEARCH_PREFIX.match(question.strip())
        if m:
            search_query = question.strip()[m.end():].strip()
            return await search_brave(search_query) if search_query else "Please say what you want me to search for."
        return await ask_llm(question)
    except (httpx.HTTPError, KeyError, ValueError) as e:
        return f"The online service is temporarily unavailable ({type(e).__name__}). Please try again."
