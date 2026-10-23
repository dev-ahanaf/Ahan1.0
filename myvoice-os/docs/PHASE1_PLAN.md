# MyVoice OS - Phase 1 Implementation Plan

Title: Phase 1 - Foundation, Hardware Bring-Up, and Device Management
Target Hardware: ESP32 DevKit V1 / ESP32-WROOM-32 (Standard ESP32, No PSRAM)
Target Protocol: MyVoice OS Protocol v1.0 (specified in docs/PROTOCOL.md)
Status: Pending User Review and Approval

---

## 1. Overview and Objectives

Phase 1 establishes a rock-solid, production-ready foundation for MyVoice OS. The existing v0.1 starter demonstrated basic feasibility via a monolithic FastAPI script, rudimentary static HTML, and a single-file Arduino sketch. Phase 1 systematically upgrades each component into an enterprise-grade, modular, and maintainable architecture while maintaining 100% backward compatibility with existing endpoints and preserving the HTTP push-to-talk voice pipeline.

Core deliverables:
1. Complete codebase audit (`docs/AUDIT.md`) - Completed.
2. Authoritative device-server protocol specification (`docs/PROTOCOL.md`) - Completed.
3. Modular FastAPI backend with SQLAlchemy 2.0 ORM, Alembic migrations, and Pydantic schemas.
4. Hardened device registration, single-use pairing codes, attempt throttling, and token lifecycle management.
5. Per-device dynamic configuration engine with automatic version-based synchronization (`config_version`).
6. Modern, high-performance web dashboard built with React, TypeScript, Vite, and Tailwind CSS.
7. Modular, non-blocking ESP32 firmware with FreeRTOS task hygiene, LittleFS audio buffering, and zero heap fragmentation.
8. Crisp monochrome SSD1306 128x64 OLED display interface supporting 10 distinct UI states.
9. Interactive hardware diagnostics mode activated via boot button hold, backed by `docs/BRINGUP.md`.
10. Headless Python device simulator (`tools/simulator.py`) for automated end-to-end regression testing.
11. Comprehensive automated test coverage for backend, database migrations, frontend compilation, and firmware compilation.

---

## 2. Detailed Task Breakdown & Implementation Strategy

### Task 1: Complete Codebase Audit (Completed)
- Artifact: `docs/AUDIT.md`
- Status: Completed and documented in repository.
- Key Findings: Detailed memory constraints on ESP32 without PSRAM (520 KB SRAM limit), plaintext HTTP security boundaries, lack of configuration sync, monolithic backend debt, missing OLED driver logic, and flash wear considerations.

---

### Task 2: Modular Backend Architecture
- Objective: Transition from monolithic `server/app.py` to structured domain packages while preserving existing API endpoints, SQLite records, and passing test suites.
- File Structure:
  ```text
  server/
    alembic/                # Database migrations
      versions/
      env.py
      script.py.mako
    alembic.ini
    app/
      __init__.py
      main.py               # FastAPI app factory, lifespan, CORS, and router registration
      config.py             # Pydantic BaseSettings for environment variables
      db.py                 # SQLAlchemy 2.0 engine, SessionLocal, declarative base
      models.py             # SQLAlchemy ORM models (Device, DeviceConfig)
      schemas.py            # Pydantic v2 schemas for all payloads and query params
      auth.py               # HTTP Basic Auth, timing-safe hashing, and device token auth
      routers/
        __init__.py
        health.py           # GET /api/health
        devices.py          # GET /api/device/status, /api/device/config, /api/device/time, /api/device/weather
        pairing.py          # POST /api/device/bootstrap, POST /api/admin/claim
        voice.py            # POST /api/device/voice (preserved HTTP push-to-talk WAV pipeline)
        dashboard.py        # GET /api/admin/devices, POST /api/admin/devices/{id}/settings, token rotation/revocation
      services/
        __init__.py
        asr.py              # Speech-to-text service (Whisper API client)
        llm.py              # LLM chat completion and intent classifier
        tts.py              # Speech synthesis service (TTS-1 client)
        weather.py          # Open-Meteo client
        search.py           # Brave Search API client
    static/                 # Production-built web dashboard assets
    tests/                  # Pytest test suite
  ```
- Incremental Migration Strategy:
  1. Add `SQLAlchemy>=2.0` and `alembic>=1.13` to `server/requirements.txt`.
  2. Implement `app/config.py`, `app/db.py`, `app/models.py`, and `app/schemas.py`.
  3. Initialize Alembic with a migration script matching the upgraded database schema.
  4. Write a database bootstrap helper that transparently adds any missing columns to existing `myvoice.db` SQLite files.
  5. Implement domain routers and services, importing all route handlers into `app/main.py`.
  6. Create an entry point `server/app.py` that re-exports `app` from `app.main:app` so existing scripts, test runners, and Uvicorn commands work with zero disruption.
  7. Run `python -m pytest` to verify that all existing tests pass continuously.

---

### Task 3: Secure Device Registration and Pairing
- Objective: Harden device bootstrapping, eliminate spoofing risks, and manage token lifecycles.
- Implementation Details:
  - Identity Format: Validate MAC addresses using regex `^[0-9A-Fa-f:]{12,17}$`, standardizing to uppercase.
  - Conflict Guard: If a device ID is already registered and marked as `paired == 1`, bootstrap requests will return `409 Conflict`. A device cannot be hijacked by re-submitting its MAC address with the enrollment key.
  - Expiring Single-Use Pairing Codes:
    - 6-digit random code generated via `secrets.randbelow(900000) + 100000`.
    - Stored as `sha256(ENROLLMENT_KEY + ":" + code)` with `pair_expires = now + 10 minutes`.
    - Once claimed via `/api/admin/claim`, `pair_hash` and `pair_expires` are immediately nulled.
  - Rate Limiting on Pairing:
    - Implement an in-memory sliding window rate limiter on `/api/admin/claim` (e.g., maximum 5 failed attempts per minute per IP address).
    - Return `429 Too Many Requests` on threshold breach to prevent brute-forcing the 6-digit space.
  - Device Token Hashing:
    - Device tokens generated via `secrets.token_urlsafe(32)`.
    - Stored in database only as `sha256(token)`. Validated using `secrets.compare_digest`.
  - Token Rotation & Revocation:
    - Add `POST /api/admin/devices/{id}/rotate-token`: Generates a fresh token, returns it once in the response, and invalidates the previous token.
    - Add `POST /api/admin/devices/{id}/revoke`: Sets `revoked = 1`, causing all future device requests to return `401 Unauthorized`.
  - Online Status Tracking:
    - Update `last_seen` timestamp on every authenticated device request (heartbeat, voice, config, weather, time).
    - Devices seen within the last 120 seconds are marked as `online = true`.

---

### Task 4: Per-Device Configuration and Dynamic Sync
- Objective: Provide individual hardware and behavioral settings stored independently for every device, synchronized via versioning.
- Settings Fields:
  - `name`: string (1-50 chars)
  - `timezone`: valid IANA timezone string (validated via `ZoneInfo`)
  - `language`: string (e.g., 'en', 'bn')
  - `city`: string (1-80 chars)
  - `latitude`: float (-90 to +90)
  - `longitude`: float (-180 to +180)
  - `oled_brightness`: integer (0 to 255)
  - `idle_display_mode`: string ('clock', 'weather', 'blank')
  - `clock_format`: string ('12h', '24h')
  - `speaker_volume`: integer (0 to 100)
  - `mic_gain`: integer (0 to 100)
  - `wake_mode`: string ('button', 'wakeword') [Documented as config-only placeholder]
  - `weather_enabled`: boolean
  - `search_enabled`: boolean
  - `timers_enabled`: boolean
  - `config_version`: integer counter (monotonically increasing)
- Version-Based Sync Flow:
  1. Admin updates settings via `POST /api/admin/devices/{id}/settings`.
  2. Server updates database and increments `config_version = config_version + 1`.
  3. Device sends routine heartbeat `POST /api/device/heartbeat`.
  4. Server heartbeat response contains current `config_version`.
  5. Device compares server `config_version` against locally stored version in NVS.
  6. If server version is greater, device issues `GET /api/device/config`.
  7. Device persists updated configuration into NVS Preferences and dynamically applies hardware settings (e.g., updates OLED brightness, updates display format, reconfigures NTP offset).

---

### Task 5: Modern Web Dashboard
- Objective: Replace static HTML with a modern, reactive, accessible single-page application.
- Technology Stack:
  - React 18+
  - TypeScript
  - Vite (fast build system)
  - Tailwind CSS (responsive styling and clean design system)
  - Lucide Icons (clean iconography)
- Application Architecture (`server/frontend/`):
  ```text
  server/frontend/
    src/
      api/              # Typed API clients for admin endpoints
      components/
        Header.tsx      # App brand, connection badge, theme toggle, logout
        Sidebar.tsx     # Navigation links, mobile responsive drawer
        DeviceCard.tsx  # Device status card with online badge and quick actions
        PairModal.tsx   # 6-digit pair code modal with countdown and instructions
        ConfigForm.tsx  # Dynamic per-device configuration form
        CommandLab.tsx  # Interactive assistant testing console
        Toaster.tsx     # Toast feedback system
      views/
        Overview.tsx    # Fleet summary stats and activity stream
        Devices.tsx     # Device grid/list view and management
        Settings.tsx    # Device detail and configuration editor
        Lab.tsx         # AI command testing environment
      App.tsx
      main.tsx
    package.json
    tsconfig.json
    vite.config.ts
    tailwind.config.js
  ```
- Design Standard:
  - Visual Identity: Dark slate with vibrant indigo accents, crisp typography, clean cards, and responsive layouts.
  - Zero mock data: All views, metrics, and actions are wired directly to the real backend API.
  - Built output compiled to `server/static/` and served directly by FastAPI.

---

### Task 6: ESP32 Firmware Refactoring
- Objective: Modularize firmware into discrete C++ modules with non-blocking state management, safe FreeRTOS task handling, and zero memory leaks.
- Target Board: ESP32 DevKit V1 / ESP32-WROOM-32 (no PSRAM).
- Module Architecture:
  ```text
  firmware/
    include/
      config_store.h    # NVS Preferences storage for credentials and settings
      display.h         # SSD1306 OLED interface and screen state machine
      audio_in.h        # INMP441 I2S microphone driver and LittleFS recording
      audio_out.h       # MAX98357A I2S amplifier driver and WAV playback
      net_client.h      # HTTPClient wrapper for bootstrap, status, heartbeat, config
      wifi_setup.h      # WiFiManager captive portal and reconnect logic
      pins.h            # Central pin definitions and hardware constants
      secrets.h.example # Template for LAN IP and enrollment key
    src/
      main.cpp          # System initialization, state machine, button polling
      config_store.cpp  # Implementation of NVS persistence
      display.cpp       # SSD1306 rendering routines for 10 screen states
      audio_in.cpp      # Microphone I2S sampling and WAV writing
      audio_out.cpp     # Streaming WAV parser and speaker I2S output
      net_client.cpp    # HTTP communication routines
      wifi_setup.cpp    # Captive portal management
  ```
- Memory & Performance Safeguards:
  - LittleFS audio spooling retained: Avoids keeping 96 KB raw WAV in scarce internal SRAM.
  - Stack allocation limits: Dynamic JSON documents capped to prevent FreeRTOS stack overflow.
  - Non-blocking loop: Delay calls eliminated or minimized to keep button polling and display updates responsive.

---

### Task 7: OLED Display Interface
- Objective: Implement SSD1306 128x64 monochrome OLED driver over I2C (SDA=18, SCL=19).
- Screen States:
  1. `BOOTING`: Display MyVoice OS logo, version, and hardware init status.
  2. `WIFI_CONNECTING`: Show Wi-Fi SSID and connection attempt animation.
  3. `SERVER_CONNECTING`: Show server IP and handshake indicator.
  4. `PAIRING_CODE`: Large, high-contrast 6-digit pairing code with 10-minute timer.
  5. `IDLE_CLOCK`: Formatted local time (12h/24h), date, and Wi-Fi signal indicator.
  6. `IDLE_WEATHER`: Temperature, condition icon, and city name.
  7. `LISTENING`: "Listening..." banner with visual recording indicator.
  8. `THINKING`: "Thinking..." animation while server processes Whisper/LLM.
  9. `SPEAKING`: "Speaking..." waveform animation during audio playback.
  10. `ERROR`: Explicit error message (e.g., "Server unreachable", "Token rejected").
  11. `DIAGNOSTICS`: Multi-line hardware diagnostic results screen.

---

### Task 8: Hardware Diagnostics & Bring-Up
- Objective: Implement interactive boot-time diagnostic mode and provide a comprehensive bring-up guide.
- Diagnostic Routine:
  - Triggered by holding the GPIO 27 button down during power-on or hardware reset.
  - Test Sequence:
    1. Memory Check: Measure free heap, minimum free heap, and LittleFS storage capacity.
    2. Button Test: Confirm GPIO 27 pull-up state and press detection.
    3. I2C Bus Scan: Probe 0x3C / 0x3D to verify SSD1306 presence.
    4. OLED Screen Test: Render checkerboard and border patterns to confirm display pixels.
    5. Microphone Test: Sample 100 ms of audio from INMP441, calculating RMS noise floor and peak amplitude.
    6. Speaker Test: Synthesize and output a 440 Hz test tone burst for 500 ms to confirm MAX98357A output.
    7. Wi-Fi Scan: List nearby SSIDs and signal strength.
    8. Server Handshake: Issue test HTTP GET to `/api/health` and report latency.
- Artifact: Create `docs/BRINGUP.md` documenting wiring tables, power supply considerations, jumper settings, and expected serial diagnostic outputs.

---

### Task 9: Headless Device Simulator
- Objective: Provide a Python script (`tools/simulator.py`) simulating an ESP32 hardware device.
- Capabilities:
  - Emulates ESP32 MAC address generation and persistent credential caching (`.simulator_creds.json`).
  - Executes device bootstrap (`POST /api/device/bootstrap`) using `ENROLLMENT_KEY`.
  - Simulates pairing wait loop (`GET /api/device/status`).
  - Sends regular heartbeats (`POST /api/device/heartbeat`) with heap/RSSI telemetry.
  - Detects `config_version` increments and fetches updated configuration (`GET /api/device/config`).
  - Generates synthetic 3-second 16 kHz 16-bit PCM test WAV files and uploads to `/api/device/voice`.
  - Receives and saves server audio response WAV files to disk.

---

### Task 10: Automated Testing and Acceptance
- Verification Steps:
  1. Pytest Test Suite:
     - Run existing tests in `server/tests/test_app.py` - all must pass.
     - Add new test modules in `server/tests/` covering:
       - Single-use pairing code consumption and expiration.
       - Pairing rate limiting (brute-force defense).
       - Token rotation and revocation.
       - Configuration validation, persistence, and version incrementing.
       - Heartbeat version signaling.
       - Alembic database migration round-trip.
  2. Device Simulator Test:
     - Run `tools/simulator.py` end-to-end against live backend instance.
  3. Frontend Build Check:
     - Run `npm run build` in `server/frontend/` to ensure zero TypeScript or bundling errors.
  4. PlatformIO Firmware Build:
     - Run `pio run` in `firmware/` to ensure modular C++ firmware compiles cleanly for ESP32.
  5. Hardware Bring-Up Manual:
     - Verify `docs/BRINGUP.md` matches physical wiring pinouts.

---

## 3. Strict Safety & Phase 1 Boundary Rules

1. Stop after Phase 1 completion and wait for explicit user approval before proceeding to Phase 2.
2. Maintain plain HTTP push-to-talk voice pipeline without breaking changes.
3. No em dashes used in documentation or code comments.
4. Physical hardware validation must be explicitly marked as UNVERIFIED until physically confirmed on workbench.
5. All sensitive credentials (.env, secrets.h, database files) must remain excluded from version control.
