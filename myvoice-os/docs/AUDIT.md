# MyVoice OS v0.1 - Comprehensive Codebase Audit

Date: October 2026
Auditor: Principal Embedded Systems Engineer, Security Architect & Full-Stack Lead
Target Project: MyVoice OS v0.1 (XiaoZhi-inspired voice assistant stack)
Hardware Target: ESP32 DevKit V1 / ESP32-WROOM-32 (No PSRAM)

---

## 1. Executive Summary

MyVoice OS v0.1 is a lightweight starter ecosystem designed to provide an independent, privately-hosted voice assistant stack for standard ESP32 microcontrollers. It circumvents proprietary XiaoZhi firmware and backends by utilizing an open architecture:
- Backend: Single-file FastAPI application (`server/app.py`) managing SQLite database persistence, Basic Auth dashboard, Open-Meteo weather lookups, optional Brave search, and optional OpenAI Whisper/GPT/TTS voice processing.
- Frontend: Minimal vanilla HTML/CSS/JavaScript dashboard served as static files (`server/static/`).
- Firmware: Monolithic Arduino-based ESP32 C++ application (`firmware/src/main.cpp`) utilizing WiFiManager for captive-portal configuration, LittleFS for temporary audio spooling, and I2S for half-duplex microphone recording and speaker playback.

While the conceptual model is functional for a quick local lab demo, the implementation contains critical security vulnerabilities, architectural debt, memory management risks on 520 KB SRAM ESP32s, missing display driver logic, and lack of configuration synchronization. This audit provides a thorough assessment of each component and establishes the engineering baseline for Phase 1.

---

## 2. Existing Architecture Overview

```text
[ Browser / Dashboard ]
       |
       | HTTP (Basic Auth: "admin" + ADMIN_PASSWORD)
       v
[ FastAPI Monolith (server/app.py) ]
  |-- Raw SQLite queries via sqlite3.connect ("server/myvoice.db")
  |-- Open-Meteo API (Weather via latitude/longitude)
  |-- Brave Search API (Optional live web snippets)
  |-- OpenAI Audio & Chat APIs (Whisper STT, GPT-4.1-mini, TTS-1)
  ^
  | HTTP POST/GET (Plaintext JSON & WAV payloads)
  | Headers: X-Device-ID, X-Device-Token, X-Enrollment-Key
  v
[ ESP32-WROOM-32 Hardware Client ]
  |-- WiFiManager Captive Portal (AP: MyVoice-Setup)
  |-- NVS (Preferences) for token and pair_code storage
  |-- LittleFS (Internal flash) for /voice.wav spooling
  |-- I2S0: INMP441 Microphone (16 kHz, 16-bit mono via 32-bit slot)
  |-- I2S1: MAX98357A Amplifier (24 kHz, 16-bit mono)
  |-- GPIO27: Tactile Push-to-Talk button
  `-- I2C (GPIO 18 SDA, GPIO 19 SCL): OLED Display (UNIMPLEMENTED IN v0.1)
```

---

## 3. Working Features (Verified)

1. Backend Test Suite:
   - Four test cases in `server/tests/test_app.py` pass when executed via `python -m pytest`:
     - Health endpoint (`GET /api/health`) and protected dashboard authentication.
     - Device bootstrap (`POST /api/device/bootstrap`) issuing token and pairing code.
     - Device claim (`POST /api/admin/claim`) and paired status polling.
     - Settings update (`POST /api/admin/devices/{id}/settings`) with timezone validation.
     - Mocked weather and mock audio round-trip via `POST /api/device/voice`.

2. Device Bootstrap Protocol:
   - New devices submit MAC address and firmware version with `X-Enrollment-Key`.
   - Server validates shared key and returns a 32-byte URL-safe device token and a random 6-digit pairing code with a 10-minute expiry window.

3. Database Schema Baseline:
   - A single `devices` table records device ID, name, token hash, pairing hash, expiration, last seen, firmware version, and default geolocation coordinates (Dhaka, Bangladesh).

4. Push-to-Talk Voice Pipeline Concept:
   - Device records audio to flash filesystem (`/voice.wav`) and uploads raw WAV via HTTP POST.
   - Server transcribes via Whisper, evaluates commands (weather, time, web search, or general LLM), synthesizes voice via TTS-1, and streams back a standard RIFF WAV.
   - ESP32 streams the response WAV directly to I2S DMA buffers.

5. External Service Integrations:
   - Open-Meteo API integration operates without API keys for weather forecasts.
   - Brave Search API handles web lookups when key is configured.
   - OpenAI API handles chat completion and speech synthesis when key is configured.

---

## 4. Incomplete Features & Gaps

1. OLED Display Interface:
   - Wire assignments exist in README (SDA=18, SCL=19), but `firmware/src/main.cpp` contains zero display code, libraries, or screen layout implementations.
   - Line 53 of `main.cpp` literally notes: `// Add OLED display rendering here in a board-specific extension.`

2. Configuration Synchronization:
   - There is no dynamic configuration sync mechanism.
   - When an administrator modifies device settings in the dashboard (name, timezone, location), the ESP32 never receives these updates unless it explicitly polls status or reboots.
   - Timezone changes on the server do not update the ESP32 hardware NTP clock or local time offset.
   - There is no `config_version` counter in the database or firmware.

3. Hardware Diagnostics:
   - There is no boot-time diagnostic mode.
   - No self-test routines exist for verifying microphone signal levels, speaker tone generation, button debouncing, I2C bus scanning, or free SRAM measurement.

4. Device Simulator:
   - No mock client or software simulator exists in `tools/` to validate device onboarding, heartbeat loops, config syncing, or audio streaming without physical ESP32 hardware.

5. Modern Web Interface:
   - Existing dashboard consists of a single unbundled HTML/CSS/JS file.
   - Lacks modularity, component structure, TypeScript safety, responsive mobile drawer, accessible forms, audio visualizer, token rotation controls, or state management.

---

## 5. Security Weaknesses & Credential Handling Review

### 5.1. Shared Global Enrollment Key
- Vulnerability: `ENROLLMENT_KEY` is shared across all devices and hardcoded in firmware `secrets.h`.
- Risk: Anyone who extracts the firmware binary or intercepts local network traffic obtains the enrollment key. With this key, an attacker can register arbitrary fake MAC addresses and flood the database.
- Assessment: While acceptable for a private home lab proof-of-concept, the enrollment key must not allow an attacker to hijack or overwrite an already-paired device. In v0.1, `bootstrap` rejects re-registration if `paired == 1`, which prevents immediate takeover, but an unpaired device or duplicate bootstrap race condition remains vulnerable.

### 5.2. Plaintext HTTP on Local Network
- Vulnerability: All network communications between the browser, server, and ESP32 run over unencrypted HTTP.
- Risk:
  - Admin credentials (`Basic Auth`) are sent in base64 on every dashboard request.
  - Device tokens (`X-Device-Token`) and pairing codes are transmitted in plaintext headers.
  - Spoken voice recordings and server speech outputs are exposed to packet capture.
- Assessment: This is documented as a LAN-only limitation in `docs/SECURITY.md`. In Phase 1, we must retain the HTTP transport for hardware simplicity, but harden the protocol with constant-time hash comparisons, token rotation capabilities, and strict input validation.

### 5.3. Device Credential Storage and Management
- Vulnerability:
  - The server stores `token_hash = sha256(token)` and `pair_hash = sha256(ENROLLMENT_KEY + ":" + code)`. While hashing is used, unsalted SHA-256 for a 6-digit code (1,000,000 possibilities) is trivially brute-forceable offline if the database is leaked.
  - The pairing code is not rate-limited on the admin claim endpoint (`/api/admin/claim`). An attacker with dashboard access or local network visibility could brute-force all 1,000,000 codes in seconds.
  - Device tokens cannot be revoked or rotated from the dashboard. Once a device token is compromised or lost, manual database intervention is required.

---

## 6. Bugs & Technical Debt

1. Monolithic Server Architecture (`server/app.py`):
   - 379 lines of intertwined concerns: database schema definitions, raw SQL execution, route handling, authentication, third-party HTTP clients, LLM prompting, and static asset serving all reside in one file.
   - No ORM abstraction or migration tracking.
   - Database operations use direct `sqlite3.connect` calls inside route handlers without connection pooling or schema migration management.

2. Fragile Timezone Handling:
   - When a user submits an invalid timezone string, `ZoneInfo(body.timezone)` catches it, but the fallback profile in `answer_question` defaults to `Asia/Dhaka` without validating the device row timezone dynamically.
   - ESP32 uses a static compile-time macro `#define GMT_OFFSET_SEC (6 * 3600)` instead of applying the device timezone configured in the database.

3. Brittle WAV Header Parsing on ESP32 (`playWavStream` in `main.cpp`):
   - Lines 220-265 attempt to parse RIFF chunks sequentially. If the cloud TTS response inserts unexpected chunks (e.g., `LIST`, `INFO`, `id3 `) larger than 500,000 bytes or chunks with padding bytes, parsing can fail silently or drop audio.
   - The stream read timeout is set to 12,000 ms, which can cause audio stuttering if network packets arrive unevenly.

4. LittleFS Flash Wear & Latency:
   - Every 3-second recording writes 96,000 bytes to internal flash memory (`/voice.wav`), flushes it, closes it, re-opens it for HTTP streaming, and deletes it.
   - Flash write cycles on SPI flash degrade over time, and write operations add 200-400 ms of latency before transmission can begin.

---

## 7. ESP32 Memory Constraints (No PSRAM Target)

The target hardware is the standard ESP32-WROOM-32 / DevKit V1:
- Total Internal SRAM: 520 KB (typically ~320 KB available to user application after FreeRTOS, Wi-Fi stack, and Bluetooth stack allocations).
- External PSRAM: NONE.
- Internal SPI Flash: 4 MB (shared between application binary, OTA partitions, LittleFS, and NVS).

### Memory Budget Analysis:
1. Wi-Fi + TCP/IP Stack (LwIP): ~50 KB DRAM.
2. LittleFS Cache & Descriptors: ~8-12 KB.
3. I2S DMA Buffers:
   - RX (Mic): 4 buffers x 256 samples x 4 bytes = 4 KB.
   - TX (Speaker): 6 buffers x 256 samples x 2 bytes = 3 KB.
4. Audio Spooling:
   - 3 seconds of 16 kHz 16-bit PCM = 96,000 bytes.
   - Keeping 96 KB in SRAM would consume nearly 35% of free heap, risking allocation failures during SSL handshakes or JSON parsing.
   - The LittleFS spooling strategy in v0.1 successfully protects heap headroom, but buffer management must be carefully tuned to prevent heap fragmentation.
5. Dynamic JSON Parsing:
   - `DynamicJsonDocument doc(512)` is allocated repeatedly on the stack. In modular C++, stack allocations must be capped to prevent FreeRTOS task stack overflow (default Arduino loop task stack is 8192 bytes).

---

## 8. Database Migration & Schema Evolution Requirements

Currently, `init_db()` in `server/app.py` runs raw `CREATE TABLE IF NOT EXISTS devices (...)`.
To support Phase 1 features, the schema must evolve to include:
- `config_version INTEGER NOT NULL DEFAULT 1`
- `language TEXT NOT NULL DEFAULT 'en'`
- `oled_brightness INTEGER NOT NULL DEFAULT 128`
- `idle_display_mode TEXT NOT NULL DEFAULT 'clock'`
- `clock_format TEXT NOT NULL DEFAULT '24h'`
- `speaker_volume INTEGER NOT NULL DEFAULT 80`
- `mic_gain INTEGER NOT NULL DEFAULT 50`
- `wake_mode TEXT NOT NULL DEFAULT 'button'`
- `weather_enabled INTEGER NOT NULL DEFAULT 1`
- `search_enabled INTEGER NOT NULL DEFAULT 1`
- `timers_enabled INTEGER NOT NULL DEFAULT 1`
- `revoked INTEGER NOT NULL DEFAULT 0`

Furthermore:
- Direct SQLite scripts must be replaced by SQLAlchemy 2.0 ORM models and Alembic migration scripts.
- Existing database records in `server/myvoice.db` must be safely preserved when migrating.
- The schema design must remain dialect-agnostic to facilitate future PostgreSQL support without code rewrites.

---

## 9. Incremental Development Approach for Phase 1

To maintain system stability and satisfy all requirements without introducing regressions:

1. Step 1: Architectural Baseline & Planning
   - Formulate and record the Phase 1 Implementation Plan in `docs/PHASE1_PLAN.md`.
   - Update protocol specifications in `docs/PROTOCOL.md`.
   - Wait for explicit user approval before modifying code.

2. Step 2: Backend Modularization & Database Evolution
   - Modularize `server/app/` into domain packages (`config`, `db`, `models`, `schemas`, `auth`, `routers`, `services`).
   - Implement SQLAlchemy 2.0 models and configure Alembic.
   - Migrate existing SQLite records cleanly while retaining full backward compatibility for existing endpoints (`/api/device/bootstrap`, `/api/device/status`, `/api/device/heartbeat`, `/api/device/voice`, etc.).
   - Verify that all existing unit tests continue to pass.

3. Step 3: Device Management, Security & Configuration Engine
   - Add single-use pairing code consumption and rate limiting.
   - Add token rotation and revocation endpoints.
   - Implement per-device configuration schema and `GET /api/device/config`.
   - Embed `config_version` in heartbeat responses to trigger automated client-side sync.

4. Step 4: Python Device Simulator
   - Build `tools/simulator.py` implementing the complete device lifecycle (bootstrap, pair code reporting, status polling, heartbeat loop, config fetch, and WAV voice transmission).

5. Step 5: Modern Dashboard Frontend
   - Develop a React + TypeScript + Vite + Tailwind CSS dashboard in `server/frontend/`.
   - Implement clean views: Overview, Device List, Device Pairing, Detailed Device Configuration, and Assistant Lab.
   - Configure Vite production build output to be served by FastAPI at `/`.

6. Step 6: Firmware Modularization & Display Bring-Up
   - Modularize firmware into `wifi_setup`, `net_client`, `audio_in`, `audio_out`, `display`, and `config_store`.
   - Integrate SSD1306 OLED driver over I2C (GPIO 18 SDA, GPIO 19 SCL).
   - Implement interactive hardware diagnostic mode triggered by holding GPIO 27 on boot.
   - Generate hardware bring-up manual in `docs/BRINGUP.md`.

7. Step 7: Verification & Acceptance
   - Run backend test suite and Alembic migrations.
   - Verify frontend build and type checking.
   - Compile firmware with `pio run`.
   - Run end-to-end simulation using `tools/simulator.py`.
