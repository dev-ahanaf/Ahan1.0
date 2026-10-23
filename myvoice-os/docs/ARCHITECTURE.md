# MyVoice OS - System Architecture Specification (v1.0.0-rc1)

## 1. Executive Architecture Summary

MyVoice OS is an open-source, independently branded XiaoZhi-inspired voice assistant and edge IoT device management ecosystem. The architecture bridges resource-constrained microcontroller hardware (ESP32-WROOM-32 with 320 KB usable SRAM and no external PSRAM) with a high-throughput, async Python backend and a reactive single-page administration studio.

```text
+-----------------------------------------------------------------------------------+
|                              ESP32 Hardware Client                                |
|  +------------------------+  +-----------------------+  +----------------------+  |
|  | INMP441 I2S Microphone |  | MAX98357A I2S Speaker |  | SSD1306 OLED (I2C)   |  |
|  +------------------------+  +-----------------------+  +----------------------+  |
|              |                           ^                         ^              |
|              v                           |                         |              |
|  +-----------------------------------------------------------------------------+  |
|  |                     FreeRTOS Dual-Core Architecture                         |  |
|  |   Core 0: Network Task (WiFi, WebSockets, HTTP, OTA stream, JSON parsing)   |  |
|  |   Core 1: Audio Task (I2S DMA buffering, Button debounce, OLED refresh)     |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
                                         |
                                         | Full-Duplex WebSockets / HTTP
                                         v
+-----------------------------------------------------------------------------------+
|                        MyVoice OS Backend Server (FastAPI)                        |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |             WebSocket Message Broker & Session Manager (ws_device.py)       |  |
|  +-----------------------------------------------------------------------------+  |
|         |                     |                       |               |           |
|         v                     v                       v               v           |
|  +--------------+    +-------------------+    +--------------+  +---------------+ |
|  | STT Pipeline |    | Tool & Skill      |    | LLM Engine   |  | TTS Streaming | |
|  | (OpenAI/     |--->| Framework         |--->| (OpenAI /    |->| (Edge-TTS /   | |
|  |  Groq/Mock)  |    | (Clock, Weather,  |    |  Groq / Mock)|  |  OpenAI/Mock) | |
|  +--------------+    |  Search, Timers,  |    +--------------+  +---------------+ |
|                      |  Alarms, Settings)|                                        |
|                      +-------------------+                                        |
|                                |                                                  |
|  +-----------------------------------------------------------------------------+  |
|  |       Background Services: Scheduler (Timers/Alarms) & OTA Catalog Manager  |  |
|  +-----------------------------------------------------------------------------+  |
|                                |                                                  |
|  +-----------------------------------------------------------------------------+  |
|  |        Database Layer: SQLite 3 + SQLAlchemy 2.0 + Alembic Migrations       |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
                                         ^
                                         | REST API + SSE
                                         v
+-----------------------------------------------------------------------------------+
|                  Management Dashboard (React 18 + Vite + Tailwind)                |
|  Fleet Management | Voice Playground | AI Personas | Skills | Timers | OTA | Logs|
+-----------------------------------------------------------------------------------+
```

---

## 2. Embedded Firmware Architecture (ESP32-WROOM-32)

### 2.1. Memory and Compute Budget
Standard ESP32-WROOM-32 modules possess only 320 KB of internal SRAM and zero external pseudo-static RAM (PSRAM). Firmware allocations are strictly bounded:
- Heap Reservation: Guaranteed minimum free heap >= 140 KB during active full-duplex streaming.
- Microcontroller Flash: 4 MB flash configured with dual OTA partitions (app0, app1) and LittleFS data partition.
- Flash Footprint: Firmware binary size is approximately 1.18 MB (90.5% of standard 1.3 MB partition, or 65% with custom 1.8 MB min_spiffs scheme).

### 2.2. Dual-Core Task Segregation
To prevent audio frame stutter during TLS or Wi-Fi network latency spikes, operations are split across both Xtensa LX6 cores:
- Core 0 (Network Worker): Executes the WebSockets client loop, TCP stack processing, HTTP fallback transactions, and OTA chunk flashing.
- Core 1 (Real-Time Audio Worker): Controls I2S DMA transfers for the INMP441 microphone and MAX98357A amplifier, hardware push-to-talk button debouncing, and I2C OLED display rendering.

### 2.3. Audio Streaming Protocol
Audio is recorded in signed 16-bit PCM mono at 16,000 Hz. The firmware groups samples into 60 ms packets (960 samples, 1,920 bytes) and dispatches them over binary WebSocket frames directly from DMA memory.

### 2.4. OLED Display Engine (SSD1306)
The 0.96 inch 128x64 display uses I2C (SDA: GPIO 21, SCL: GPIO 22). It renders dynamic state-driven layouts:
- Idle State: Centered clock, Wi-Fi RSSI bars, battery/power indicator.
- Listening State: Dynamic microphone audio level bars.
- Thinking State: Animated pulsating processing icon.
- Speaking State: Sound wave animation and assistant reply title.
- Weather Screen: City name, temperature, and condition icon.
- Timer / Alarm Screen: Countdown countdown timer and alert title.

---

## 3. Server Architecture (FastAPI Async)

### 3.1. Lifespan and Service Management
The FastAPI application lifespan manages background services:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler_service.start()
    yield
    scheduler_service.stop()
```

### 3.2. Modular AI Tool and Skill Framework
The `ToolRegistry` provides dynamic tool execution, parameter validation, and per-device access controls:
- Allowed Tools Whitelist: Configurable per device via `device.tools_enabled`.
- Timeout Shielding: Every tool execution is shielded with an async timeout (default 5.0 seconds).
- Registered Tools:
  - `get_current_time`: Timezone-aware local time, date, day of week.
  - `get_weather`: Open-Meteo REST API with geocoding and offline fallback.
  - `web_search`: Brave Search API integration with source attribution.
  - `manage_timer`: Persistent countdown timer creation, listing, and cancellation.
  - `manage_alarm`: Scheduled daily alarm management with timezone conversion.
  - `device_settings`: Remote hardware adjustments (volume, brightness, display mode).

### 3.3. Real-Time Scheduler and Alert Engine
The `SchedulerService` runs a non-blocking 1.0 second loop inspecting the SQLite database for:
1. Expired Timers: Updates status to `completed`, pushes `alert` frame over WebSocket, renders OLED pop-up, and streams synthesized Edge-TTS spoken alert.
2. Scheduled Alarms: Triggers alarms matching local device time, supports repeating schedules, and dispatches spoken alerts.
3. Delivery Acknowledgment: Waits for device `alert_ack` frame to log round-trip confirmation.

### 3.4. Over-The-Air (OTA) Firmware Distribution
- Binary Upload: Validates ESP32 magic byte (`0xE9`), file size limit (2 MB max, 10 KB min), and computes SHA-256 integrity hash.
- Targeted Deployment: Sends `ota` JSON frame over WebSocket to targeted devices or entire fleet.
- Authenticated Download: Serves binary chunk-by-chunk via `/api/ota/download/{version}/{filename}` verified against device token.

---

## 4. Frontend Architecture (React 18 + Vite)

The admin studio is built as a single-page reactive application:
- Modern Dark Aesthetic: Tailwind CSS with slate palette, indigo accents, and Lucide icons.
- Progressive Web App (PWA): Includes `manifest.json`, theme color `#0f172a`, and vector SVG icons for standalone desktop and mobile installation.
- 8 Functional Workspaces:
  1. Fleet Management: Real-time device cards, telemetry indicators, remote reboot, Wi-Fi clear, revoke.
  2. Voice Playground: Live browser microphone audio test with visual oscilloscope.
  3. AI Assistant Settings: System prompt, assistant name, personality, history depth.
  4. Tools and Skills: Tool discovery, execution test bench, and per-device permission switches.
  5. Timers and Alarms: Live countdown timers, alarm schedule editor, remote cancellation.
  6. OTA Updates: Binary upload dropzone, SHA-256 inspection, rollout deployment.
  7. Conversations: Searchable dialogue history, transcript viewer, message inspect.
  8. System and Audit: Administrative activity logs, IP tracking, provider health check.

---

## 5. Security Architecture

1. Authentication Tiers:
   - Device Bootstrap: Shared secret `X-Enrollment-Key` (minimum 24 characters).
   - Paired Operation: Asymmetric, per-device 32-byte secret token stored as SHA-256 hash.
   - Dashboard Admin: HTTP Basic Auth with constant-time cryptographic comparison (`secrets.compare_digest`).
2. Brute-Force Rate Limiting: Pairing attempts limited to 5 failures per 60 seconds per IP address.
3. HTTP Security Headers:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: strict-origin-when-cross-origin`
4. Firmware Integrity: Mandatory SHA-256 cryptographic hash verification on all OTA firmware downloads before partition activation.
