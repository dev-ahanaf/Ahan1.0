"""SQLAlchemy 2.0 database engine and session management."""
import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()

def get_db_path() -> str:
    db_path = os.getenv("DATABASE_PATH", "myvoice.db")
    if not Path(db_path).is_absolute():
        from app.config import ROOT_DIR
        db_path = str((ROOT_DIR / db_path).resolve())
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return db_path

def get_engine():
    return create_engine(
        f"sqlite:///{get_db_path()}",
        connect_args={"check_same_thread": False},
        echo=False
    )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session bound to current DATABASE_PATH."""
    db = get_db_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db_session() -> Session:
    """Return a standalone Session bound to current DATABASE_PATH."""
    curr_engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=curr_engine)()

get_session = get_db_session

def init_db():
    """Initialize tables and run non-destructive schema migrations on SQLite."""
    curr_engine = get_engine()
    from app.models import (
        Device, Conversation, Message, SystemSetting,
        Timer, Alarm, FirmwareRelease, DeviceTelemetry, AuditLog
    )
    Base.metadata.create_all(bind=curr_engine)
    
    with curr_engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(devices)"))
        existing_cols = {row[1] for row in result.fetchall()}
        
        columns_to_add = [
            ("config_version", "INTEGER NOT NULL DEFAULT 1"),
            ("language", "TEXT NOT NULL DEFAULT 'en'"),
            ("oled_brightness", "INTEGER NOT NULL DEFAULT 128"),
            ("idle_display_mode", "TEXT NOT NULL DEFAULT 'clock'"),
            ("clock_format", "TEXT NOT NULL DEFAULT '24h'"),
            ("speaker_volume", "INTEGER NOT NULL DEFAULT 80"),
            ("mic_gain", "INTEGER NOT NULL DEFAULT 50"),
            ("wake_mode", "TEXT NOT NULL DEFAULT 'button'"),
            ("weather_enabled", "INTEGER NOT NULL DEFAULT 1"),
            ("search_enabled", "INTEGER NOT NULL DEFAULT 1"),
            ("timers_enabled", "INTEGER NOT NULL DEFAULT 1"),
            ("tools_enabled", "TEXT"),
            ("revoked", "INTEGER NOT NULL DEFAULT 0"),
            ("system_prompt", "TEXT"),
            ("assistant_name", "TEXT NOT NULL DEFAULT 'MyVoice'"),
            ("personality", "TEXT NOT NULL DEFAULT 'helpful, concise voice assistant'"),
            ("history_length", "INTEGER NOT NULL DEFAULT 6"),
            ("asr_provider", "TEXT"),
            ("llm_provider", "TEXT"),
            ("llm_model", "TEXT"),
            ("tts_provider", "TEXT"),
            ("tts_voice", "TEXT"),
            ("vad_mode", "TEXT NOT NULL DEFAULT 'manual'"),
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE devices ADD COLUMN {col_name} {col_type}"))
                conn.commit()


# Call init_db() on import so tables exist for TestClient and worker processes
init_db()
