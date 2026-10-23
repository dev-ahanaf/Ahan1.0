"""Configuration settings for MyVoice OS backend."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ENROLLMENT_KEY = os.getenv("ENROLLMENT_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4.1-mini")
DATABASE_PATH = os.getenv("DATABASE_PATH", str(ROOT_DIR / "myvoice.db"))

if not Path(DATABASE_PATH).is_absolute():
    DATABASE_PATH = str((ROOT_DIR / DATABASE_PATH).resolve())

def validate_credentials():
    """Ensure sensitive credentials meet security minimums outside testing."""
    if os.getenv("TESTING") == "1":
        return
    if (len(ADMIN_PASSWORD) < 8 or ADMIN_PASSWORD.startswith("replace-") or
            len(ENROLLMENT_KEY) < 16 or ENROLLMENT_KEY.startswith("replace-")):
        raise RuntimeError("Configure unique ADMIN_PASSWORD (>=8 chars) and ENROLLMENT_KEY in server/.env")

validate_credentials()
