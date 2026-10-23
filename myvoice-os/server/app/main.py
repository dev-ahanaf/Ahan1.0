"""FastAPI main application module for MyVoice OS."""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.auth import admin
from app.routers.health import router as health_router
from app.routers.pairing import router as pairing_router
from app.routers.devices import router as devices_router
from app.routers.voice import router as voice_router
from app.routers.dashboard import router as dashboard_router
from app.routers.ws_device import router as ws_router
from app.routers.ota import router as ota_router
from app.routers.agents import router as agents_router
from fastapi import Request

from app.services.scheduler import scheduler_service

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan for database initialization and scheduler service."""
    init_db()
    scheduler_service.start()
    yield
    scheduler_service.stop()

app = FastAPI(title="Falcon AI Platform", version="1.2.0", lifespan=lifespan)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Register API routers
app.include_router(health_router)
app.include_router(pairing_router)
app.include_router(devices_router)
app.include_router(voice_router)
app.include_router(dashboard_router)
app.include_router(agents_router)
app.include_router(ws_router)
app.include_router(ota_router)


# Web Flasher static routes
FLASH_DIR = STATIC_DIR / "flash"
if not FLASH_DIR.exists():
    FLASH_DIR = ROOT_DIR.parent / "FalconAI_WebFlasher" / "site"

if FLASH_DIR.exists():
    app.mount("/flash", StaticFiles(directory=str(FLASH_DIR), html=True), name="flash")

FIRMWARE_DIR = STATIC_DIR / "firmware"
if FIRMWARE_DIR.exists():
    app.mount("/firmware", StaticFiles(directory=str(FIRMWARE_DIR)), name="firmware")

# Dashboard web routes
@app.get("/")
def dashboard_view(_: bool = Depends(admin)):
    """Serve main web dashboard."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/dashboard.css")
def css_view():
    """Serve dashboard CSS stylesheet."""
    return FileResponse(STATIC_DIR / "dashboard.css", media_type="text/css")

@app.get("/dashboard.js")
def js_view():
    """Serve dashboard client script."""
    return FileResponse(STATIC_DIR / "dashboard.js", media_type="application/javascript")

@app.get("/manifest.json")
def manifest_view():
    """Serve PWA manifest."""
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")

@app.get("/icon.svg")
def icon_view():
    """Serve PWA app icon."""
    return FileResponse(STATIC_DIR / "icon.svg", media_type="image/svg+xml")

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

