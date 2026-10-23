# MyVoice OS - Phase 3 Implementation Plan

Title: Phase 3 - Complete Smart Assistant Ecosystem and Release Candidate (v1.0.0-rc1)
Target Architecture: Modular Function Calling, Real-Time Alerts, OLED Data Screens, Secure OTA Distribution, Advanced Device Management, Production Deployment & Security Hardening
Target Hardware: ESP32 DevKit V1 / ESP32-WROOM-32 (Standard ESP32, 520 KB SRAM / 320 KB usable, 4 MB Flash, No External PSRAM)
Status: Pending User Review and Approval

---

## 1. Overview and Executive Summary

Following the successful completion and verification of Phase 1 (Hardware Bring-Up, Pairing, Baseline Configuration) and Phase 2 (Real-Time Bidirectional WebSocket Streaming, Multi-Provider AI Architecture, Barge-In Interruption), Phase 3 elevates MyVoice OS into a complete, release-ready smart assistant ecosystem.

The goal is to deliver an independently branded, production-grade AI voice assistant ecosystem inspired by XiaoZhi, providing:
1. Grounded AI Tool & Skill Framework: Real function-calling execution for Clock, Weather, Web Search, Timers, Alarms, and Device Settings with strict allowlist validation and per-device permissions.
2. Real-Time Device Alerts & Spoken Notifications: Server-driven alerts over WebSocket for timer expiry and alarms with synchronized OLED visuals and spoken audio.
3. Rich OLED Screen Rendering: Server-to-device display events providing dedicated screens for Weather, Timers, Alarms, Clock, and Voice States on SSD1306 128x64.
4. Secure OTA Firmware Updates: Firmware catalog, cryptographic SHA-256 verification, size checks, protected binary downloads, and simulated rollout verification.
5. Advanced Device Management: Comprehensive telemetry (RSSI, free heap, uptime, errors), 30-second periodic status reports, remote reboot, Wi-Fi credential clearing, and administrative audit logging.
6. Wake Word Feasibility & Hardware Roadmap: Detailed technical investigation of ESP32-WROOM-32 compute and memory constraints, keeping push-to-talk rock-solid while charting the upgrade path to ESP32-S3.
7. Polished Multi-Page Dashboard: Overview, My Devices, AI Assistant, Tools and Skills, Conversations, Timers and Alarms, OTA Updates, and System Settings with dark/light themes and PWA manifest.
8. Comprehensive Security Hardening: Strict audit logs, rate limiting, request validation, upload boundaries, token rotation, and threat model in `docs/SECURITY.md`.
9. Production Deployment: Multi-stage Dockerfile, docker-compose.yml, Caddy reverse proxy with automatic TLS, and database migration bootstrapping.
10. Release Candidate Deliverable: Versioned release candidate tagged as `MyVoice OS v1.0.0-rc1` with full documentation and automated regression checks.

---

## 2. Detailed Task Breakdown & Implementation Strategy

### Task 1: AI Tool and Skill Framework
- Standardized Tool Architecture:
  - Base class `BaseTool` defined in `server/app/services/tools/base.py`:
    - `name: str`
    - `description: str`
    - `parameters_schema: dict` (standard JSON Schema compatible with OpenAI/Gemini function calling)
    - `async def execute(args: dict, context: ToolContext) -> ToolResult`
    - `enabled_by_default: bool`
    - `timeout_seconds: float` (default 5.0s)
    - `result_format: str`
  - Central `ToolRegistry`:
    - Registration decorator `@register_tool`.
    - Per-device permission check (resolves global defaults and device overrides in database).
    - Allowlisted parameter validation using Pydantic schemas.
    - Execution timeout shielding via `asyncio.wait_for`.
    - Structured error handling: Returns machine-readable failure messages rather than throwing uncaught exceptions.
- Core Functional Tools:
  1. `clock_tool`: Retrieves local time, date, day of week, and UTC offset based on device timezone (e.g., `Asia/Dhaka`).
  2. `weather_tool`: Queries Open-Meteo REST API (free, no API key required) for current weather, temperature, humidity, wind speed, and daily forecast. Defaults to device configured city, coordinates, or user-specified target.
  3. `search_tool`: Queries Brave Search REST API (with graceful fallback if unconfigured). Validates query length, extracts top 3 concise snippets, provides source attribution, and formats for voice output.
  4. `timer_tool`:
     - Actions: `set_timer(seconds, label)`, `list_timers()`, `cancel_timer(timer_id)`.
     - Database persistence in table `timers` (`id`, `device_id`, `label`, `duration_seconds`, `expires_at`, `status`).
     - Async background scheduler (`TimerManager`) running in server process: survives restarts by querying active timers on startup and scheduling `asyncio` sleep triggers.
  5. `alarm_tool`:
     - Actions: `create_alarm(time_str, days, label)`, `list_alarms()`, `cancel_alarm(alarm_id)`.
     - Database persistence in table `alarms` (`id`, `device_id`, `time_str`, `timezone`, `repeat_days`, `status`).
     - Timezone-aware calculation for next trigger timestamp.
  6. `device_settings_tool`:
     - Actions: `set_volume(level: 0-100)`, `set_brightness(level: 0-255)`, `set_display_mode(mode: clock|blank)`, `get_status()`.
     - Validates bounds strictly. Updates device row in database, increments `config_version`, and pushes real-time `config_update` frame over active WebSocket.

---

### Task 2: Smart Voice Interactions & Tool Calling Loop
- Integration with Real-Time WebSocket Pipeline (`server/app/routers/ws_device.py`):
  1. User audio stream completes (`listen_stop` or energy VAD).
  2. ASR transcribes speech to text.
  3. LLM receives conversation context, system prompt, and active tool schemas.
  4. If LLM generates a tool call:
     - WebSocket sends `tool_call_start` event to client (OLED transitions to `THINKING: [tool_name]`).
     - Server validates permissions and executes tool asynchronously with timeout guard.
     - Tool result is appended as a `tool` role message in the conversation.
     - LLM receives tool output and streams the final grounded conversational answer.
  5. Multilingual and Grounding Safeguards:
     - Handles English and Bangla prompts naturally ("What time is it?", "আজকের আবহাওয়া কেমন?", "দুই মিনিটের টাইমার দাও").
     - Grounding Guarantee: The assistant never invents weather readings, search results, or timer confirmations. If a tool fails or key is missing, the assistant honestly explains the limitation.

---

### Task 3: Real-Time Device Alerts & Spoken Notifications
- WebSocket Alert Message Protocol:
  ```json
  {
    "type": "alert",
    "kind": "timer",
    "id": "timer-uuid-1234",
    "label": "Tea",
    "text": "Your 2 minute timer for Tea has finished."
  }
  ```
- Workflow:
  1. `TimerManager` or `AlarmManager` detects trigger timestamp reached.
  2. Database marks timer status as `triggered`.
  3. Server checks if device has active WebSocket connection:
     - Connected: Emits `alert` JSON frame + streams synthesized TTS alert audio ("Your timer has finished") + triggers OLED alert screen.
     - Offline: Records missed alert in database. When device connects next, emits notification event.
  4. Client acknowledgment: Device responds with `{"type": "alert_ack", "id": "timer-uuid-1234"}`.

---

### Task 4: OLED Screen Rendering & Display Events
- Server-to-Device Display Frame:
  ```json
  {
    "type": "display",
    "screen": "weather",
    "data": {
      "city": "Dhaka",
      "temperature": 29,
      "condition": "Cloudy",
      "humidity": 65
    }
  }
  ```
- Supported Screen Types for SSD1306 (128x64 mono):
  1. `clock`: Autonomous local clock rendered every second. Synchronized at boot via NTP. Zero server traffic needed for standard clock operation.
  2. `weather`: Shows City, large temperature readout, condition text, and weather icon glyph.
  3. `timer`: Countdown timer display showing active label and remaining time (MM:SS).
  4. `alarm`: Upcoming alarm banner.
  5. `alert`: Flashing inverted banner for timer/alarm firing.
  6. `voice_state`: Displays LISTENING, THINKING, SPEAKING, and ERROR animations.
- Embedded Constraints: Low CPU overhead, minimal frame redraws, no complex sprite calculations that could introduce I2S audio jitter.

---

### Task 5: Secure OTA Firmware Updates
- Dashboard Management:
  - Upload compiled `.bin` binary with semantic version string (e.g. `1.1.0`), target hardware (`esp32dev`), and markdown release notes.
  - Server calculates SHA-256 hash, validates file headers (magic byte `0xE9`), and stores binary in protected `server/firmware_catalog/`.
- Device OTA Protocol:
  ```json
  {
    "type": "ota",
    "version": "1.1.0",
    "url": "/api/ota/download/1.1.0/firmware.bin?token=...",
    "sha256": "3a8c7b...",
    "size": 1077760
  }
  ```
- Microcontroller Verification & Security:
  - Downloads binary chunk-by-chunk using authenticated HTTP GET.
  - Verifies running partition size vs incoming binary size before writing.
  - Calculates streaming SHA-256 during flash write.
  - Rejects corrupted or truncated binaries before rebooting.
- Partition Table & Rollback Technical Analysis:
  - Standard `esp32dev` default partition has a single factory app partition (1.3 MB).
  - True hardware rollback requires two separate OTA app partitions (`ota_0` and `ota_1`) plus an `otadata` partition in a 4 MB flash table.
  - Phase 3 will document the partition analysis in `docs/HARDWARE.md` and provide `partitions_two_ota.csv` for 2-OTA partition builds, while strictly enforcing pre-flash SHA-256 verification to avoid bricking on standard single-partition setups.
  - Simulator Support: `tools/simulator.py` handles the `ota` frame, downloads the binary, verifies hash, and reports simulated percentage progress back to the server.

---

### Task 6: Advanced Device Management & Telemetry
- Periodic Device Telemetry:
  - Device emits `status_report` frame every 30 seconds over WebSocket:
    ```json
    {
      "type": "status_report",
      "free_heap": 278520,
      "min_free_heap": 245100,
      "rssi": -58,
      "uptime_s": 3600,
      "dropped_frames": 0,
      "error_count": 0
    }
    ```
  - Server logs metrics in `device_telemetry` table and updates live dashboard cards.
- Administrative Remote Actions:
  - Remote Reboot: `{"type": "reboot"}` (prompts admin confirmation modal).
  - Clear Wi-Fi Credentials / Factory Reset: `{"type": "reset_wifi"}` (requires re-provisioning).
  - Device Revocation: Marks device as revoked in database, rotates credentials, and disconnects session with code 4003.
  - Audit Logging: Table `audit_logs` records admin user, IP address, timestamp, action, and target device.

---

### Task 7: Optional Wake Word Investigation & Roadmap
- Rigorous Technical Feasibility Analysis for ESP32-WROOM-32:
  - Compute Limits: Dual-core Xtensa LX6 at 240 MHz without vector extensions.
  - Memory Limits: Standard ESP32 has ~320 KB usable SRAM. Zero external PSRAM.
  - Library Requirements: Espressif ESP-SR (WakeNet) models require ESP32-S3 (with vector instructions) and 2-8 MB PSRAM for CNN weights.
  - Running continuous keyword spotting alongside Wi-Fi TCP/IP stack and I2S microphone sampling on standard ESP32 causes heap starvation and audio dropouts.
- Architectural Decision:
  - Push-to-talk (button GPIO 27) remains the rock-solid primary input mode for standard ESP32.
  - Energy-based voice activity detection (VAD) handles hands-free speech end-detection.
  - Document a clear hardware upgrade path in `docs/HARDWARE.md` for migrating to ESP32-S3 (e.g., XiaoZhi-style hardware with PSRAM) for continuous wake-word detection.

---

### Task 8: Complete Polished Dashboard
- UI Architecture:
  - Pages:
    1. Overview: Fleet health, total interactions, active devices, latency averages, recent audit logs.
    2. My Devices: Device list, pairing modal, hardware diagnostics, real-time telemetry gauges (heap, RSSI, uptime), remote action buttons.
    3. AI Assistant: Global and per-device assistant identity, system prompt, language, voice, and multi-provider settings.
    4. Tools and Skills: Master toggle list, per-device permission matrix, interactive tool testing playground, and execution history.
    5. Conversations: Searchable conversation history, transcript viewer, audio player, latency breakdown, deletion.
    6. Timers and Alarms: Live active timer countdown cards, alarm management, timezone badges.
    7. OTA Updates: Binary catalog, upload modal, SHA-256 badge, device targeting, rollout progress bar.
    8. System Settings: Admin credential management, backend environment summary, audit log viewer.
  - Polished Styling: Curated dark/light theme, modern typography, mobile-responsive layout, zero placeholder data, and PWA manifest (`manifest.json`) for home-screen installation.

---

### Task 9: Security Hardening & Threat Analysis
- Hardening Measures:
  1. Admin Authentication: Protected session cookies / Bearer auth for dashboard endpoints.
  2. Device Isolation: Device endpoints require authenticated device token; devices cannot query or manipulate other devices' data or conversations.
  3. Rate Limiting: Strict rate limits on `/api/device/bootstrap`, `/api/admin/claim`, and `/api/ota/download`.
  4. Payload & Upload Bounds: 5 MB limit on audio uploads, 2 MB limit on firmware uploads, input validation on all strings.
  5. Security Headers: HSTS, X-Content-Type-Options, X-Frame-Options, Content-Security-Policy.
  6. Secret Sanitization: Plaintext API keys never returned in GET responses.
  7. Comprehensive Threat Model: Documented in `docs/SECURITY.md`.

---

### Task 10: Production Deployment
- Reproducible Deployment Assets:
  - Multi-stage Dockerfile: Combines Python FastAPI backend with pre-compiled React frontend bundle.
  - `docker-compose.yml`: Services for backend, persistent database volume (`/data`), firmware catalog volume, and Caddy reverse proxy.
  - `Caddyfile`: Reverse proxy providing automated Let's Encrypt TLS (HTTPS / WSS), WebSocket proxying, and compression.
  - Startup Script: Automatically applies Alembic database migrations (`alembic upgrade head`) before starting Uvicorn.
  - Documentation: Step-by-step setup guide in `docs/DEPLOY.md` for Local Mac/PC, Raspberry Pi / Home Server, and Cloud VPS.

---

### Task 11: Automated Quality Checks & CI Workflow
- Test and Quality Suite:
  - Python tests: Pytest coverage covering tool registry, weather, clock, search, timers, alarms, OTA validation, device isolation, and WebSocket alerts.
  - Frontend checks: TypeScript build (`tsc --noEmit`) and Vite bundle build (`npm run build`).
  - Firmware compilation: PlatformIO compilation check (`pio run`).
  - GitHub Actions CI workflow: Created in `.github/workflows/ci.yml` (stored locally without pushing).

---

### Task 12: Comprehensive Documentation & Release Candidate
- Complete Documentation Overhaul:
  - `README.md`: Overview, quick start, architecture diagram, feature matrix.
  - `docs/ARCHITECTURE.md`: High-level system design, data flows, and component breakdown.
  - `docs/PROTOCOL.md`: Full specification of HTTP and WebSocket protocol messages.
  - `docs/BRINGUP.md`: Hardware wiring, bring-up checklist, diagnostics, and bench testing.
  - `docs/SECURITY.md`: Threat model, credential management, and attack surface mitigations.
  - `docs/DEPLOY.md`: Docker, Caddy, bare-metal, and Raspberry Pi deployment guide.
  - `docs/API.md`: Comprehensive REST and WebSocket API documentation.
  - `docs/HARDWARE.md`: Pinouts, power decoupling, partition tables, and ESP32-S3 roadmap.
  - `docs/TROUBLESHOOTING.md`: Common issues, serial debug interpretation, and audio fixes.
- Version Designation: Tagged as `MyVoice OS v1.0.0-rc1`.

---

## 3. Hardware Architecture & Memory Analysis (Standard ESP32)

| Resource | Available | Phase 3 Budget | Safety Margin | Notes |
|---|---|---|---|---|
| **Internal SRAM** | 320 KB usable | ~58 KB static + dynamic | > 260 KB free | No external PSRAM required. |
| **I2S Audio Buffers** | DMA memory | 2x 1,920 byte DMA + 12 KB ring buffer | ~16 KB total | Zero dynamic heap churn during voice streaming. |
| **Flash Partition (Standard)** | 4 MB total | ~1.1 MB firmware binary | ~200 KB free in app0 | Standard 1.3 MB app partition. Dual-OTA requires custom partition table. |
| **OLED Display RAM** | SSD1306 RAM | 1,024 bytes (128x64 bits) | Negligible | Managed directly by Adafruit_SSD1306 buffer. |
| **Wi-Fi + TCP/IP Stack** | ESP-IDF LwIP | ~40 KB RAM | Reserved | Managed by ESP32 network co-processor core. |

---

## 4. Acceptance Criteria & Verifiable Scenarios

| Scenario | Trigger / Input | Expected System Behavior | Verification Method |
|---|---|---|---|
| **Scenario A: Weather** | "What is the weather today?" | Queries Open-Meteo for device city; returns spoken audio and displays temperature/condition on OLED. | Simulator + Unit Test |
| **Scenario B: Timers** | "Set a timer for two minutes." | Saves timer in DB; runs async scheduler; emits `alert` over WebSocket with spoken audio and visual alert on expiry. | Simulator + Scheduler Test |
| **Scenario C: Feature Permissions** | Weather disabled for device in dashboard. | Tool registry rejects weather tool execution; assistant explains weather is disabled. | Unit Test + API check |
| **Scenario D: OTA Updates** | Admin uploads firmware `.bin` and targets device. | Server validates SHA-256; device/simulator downloads and verifies hash; reports progress to dashboard. | Simulator OTA Test |
| **Scenario E: Deployment** | Run `docker-compose up -d`. | Backend starts, runs Alembic migrations, passes health checks at `/api/health`, serves UI and WebSocket. | Docker validation |
| **Scenario F: Device Isolation** | Device A tries to query Device B's config or conversation. | Server returns HTTP 403 / 404; database queries enforce strict `device_id` tenant filtering. | Automated Security Test |
| **Scenario G: Dashboard Consistency** | Admin navigates all 8 dashboard pages. | Every page renders live data with zero crashes, mock stubs, or placeholder links. | Frontend Build + End-to-End Test |

---

## 5. Implementation Stages and Milestones

- **Stage 1 (Backend Core)**: Tool framework, functional tools (clock, weather, search, timers, alarms, device settings), database models & Alembic migration.
- **Stage 2 (WebSocket & Alert Engine)**: WebSocket alert messages, display frames, timer/alarm async scheduler, tool-calling LLM loop.
- **Stage 3 (OTA & Device Management)**: Firmware catalog, SHA-256 validation, protected download endpoints, telemetry logging, remote actions, audit logs.
- **Stage 4 (Dashboard Upgrade)**: Complete multi-page interface with tools, timers, OTA, devices, overview, dark theme, and PWA manifest.
- **Stage 5 (Firmware & Simulator)**: OLED screen renderers, display events, alert handling, status reports, simulator OTA & alert tests.
- **Stage 6 (Security & Deployment)**: Rate limiting, security headers, Dockerfile, docker-compose.yml, Caddyfile, CI workflow.
- **Stage 7 (Documentation & Release)**: Complete documentation suite, regression tests, and release candidate v1.0.0-rc1 summary.

---

## 6. Strict Boundary Rules

1. Wait for explicit user approval before modifying application code.
2. Maintain backward-compatible HTTP fallback and Phase 1/2 WebSocket functionality.
3. No em dashes used in generated text, documentation, or code comments (use ASCII hyphen `-` only).
4. Physical hardware verification remains marked as UNVERIFIED until tested on workbench.
5. Do not push to GitHub or deploy without explicit user permission.
6. Secrets remain excluded from Git and masked in administrative interfaces.
