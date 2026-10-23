"""Vercel / ASGI entrypoint for MyVoice OS FastAPI server."""
from app.main import app

__all__ = ["app"]
