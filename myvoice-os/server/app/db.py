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
        Timer, Alarm, FirmwareRelease, DeviceTelemetry, AuditLog,
        AIAgent, User
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
            ("agent_id", "TEXT"),
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE devices ADD COLUMN {col_name} {col_type}"))
                conn.commit()

    # Seed default agents and admin user if not present
    seed_session = sessionmaker(autocommit=False, autoflush=False, bind=curr_engine)()
    try:
        if seed_session.query(AIAgent).count() == 0:
            agent_en = AIAgent(
                id="agent-falcon-primary",
                name="Falcon AI Assistant",
                avatar="🦅",
                description="Primary bilingual Falcon AI Voice Agent with real-time reasoning and tool calling",
                personality="helpful, concise, and intelligent voice companion",
                system_prompt="You are Falcon AI, an intelligent, helpful voice assistant. Keep answers natural, accurate, and under 50 words. Support both English and Bengali depending on what the user speaks.",
                language="en",
                model_provider="gemini",
                model_name="gemini-1.5-flash",
                tts_provider="edge-tts",
                tts_voice="en-US-AriaNeural",
                response_style="concise",
                temperature=0.7,
                tools_enabled="clock,weather,search,timer,alarm,device_settings"
            )
            agent_bn = AIAgent(
                id="agent-falcon-bangla",
                name="Falcon AI বাংলা",
                avatar="🇧🇩",
                description="সম্পূর্ণ বাংলা ভয়েস সহকারী - আবহাওয়া, সময়, এলার্ম ও সাধারণ জ্ঞান",
                personality="বন্ধুভাবাপন্ন, নির্ভুল এবং সংক্ষিপ্ত কণ্ঠ সহকারী",
                system_prompt="আপনি ফ্যালকন এআই, একটি আধুনিক এবং সাহায্যকারী কণ্ঠ সহকারী। স্পষ্ট এবং সংক্ষিপ্ত বাংলায় উত্তর দিন। ৫০ শব্দের মধ্যে উত্তর সীমাবদ্ধ রাখুন।",
                language="bn",
                model_provider="gemini",
                model_name="gemini-1.5-flash",
                tts_provider="edge-tts",
                tts_voice="bn-BD-NabanitaNeural",
                response_style="concise",
                temperature=0.7,
                tools_enabled="clock,weather,search,timer,alarm,device_settings"
            )
            seed_session.add(agent_en)
            seed_session.add(agent_bn)
            seed_session.commit()

        if seed_session.query(User).count() == 0:
            import hashlib
            from app.config import ADMIN_PASSWORD
            admin_user = User(
                id="user-admin-default",
                username="admin",
                email="admin@falcon-ai.local",
                password_hash=hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
                role="admin",
                full_name="Falcon Administrator",
                is_active=1
            )
            seed_session.add(admin_user)
            seed_session.commit()
    except Exception:
        seed_session.rollback()
    finally:
        seed_session.close()


# Call init_db() on import so tables exist for TestClient and worker processes
init_db()

