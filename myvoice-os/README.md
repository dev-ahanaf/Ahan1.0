# MyVoice OS - Smart AI Voice Assistant Ecosystem (v1.0.0-rc1)

[![CI](https://github.com/myvoice-os/myvoice-os/actions/workflows/ci.yml/badge.svg)](https://github.com/myvoice-os/myvoice-os)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release: v1.0.0-rc1](https://img.shields.io/badge/Release-v1.0.0--rc1-indigo.svg)](https://github.com/myvoice-os/myvoice-os/releases)

> **Hardware Verification Notice: UNVERIFIED (Awaiting Physical Workbench Testing)**
> All firmware logic, memory limits (320 KB SRAM without PSRAM), and communication protocols have been verified via PlatformIO compilation, 30 automated test cases, and real-time simulator streaming. Physical acoustic validation on hardware silicon is pending bench testing.

MyVoice OS is an open-source, independently branded XiaoZhi-inspired voice assistant and edge IoT device management ecosystem. It runs on low-cost standard ESP32-WROOM-32 microcontrollers without requiring external PSRAM, communicating directly with your self-hosted server and reactive administration studio.

---

## Key Features

- **Real-Time Full-Duplex Audio**: Low-latency WebSocket audio streaming (PCM16 16 kHz) with client-side user barge-in speech interruption.
- **Visual OLED Feedback**: Real-time SSD1306 128x64 display state machine rendering clock, live weather, countdown timers, alarm popups, and animated speech waveforms.
- **Modular AI Tool and Skill Framework**: Server-side tool execution engine supporting:
  - Local Clock & Date (Timezone-aware)
  - Live Weather (Open-Meteo REST API with geocoding and offline fallback)
  - Web Search (Brave Search API integration with attribution)
  - Countdown Timers (Persistent, server-scheduled)
  - Scheduled Alarms (Daily and repeating alarms)
  - Remote Hardware Settings (Speaker volume, screen brightness, idle display mode)
- **Background Scheduler & Spoken Alerts**: Dispatches real-time spoken audio alerts and OLED notifications when timers finish or alarms trigger, with delivery acknowledgment (`alert_ack`).
- **Secure Over-The-Air (OTA) Updates**: Authenticated firmware rollout with SHA-256 integrity verification, 2 MB size guards, and ESP32 `0xE9` header validation.
- **Enterprise Fleet Management**: Live device telemetry (RSSI, free heap, uptime, dropped frames), remote reboot, Wi-Fi clear, device token revocation, and immutable audit logs.
- **Backward-Compatible HTTP Fallback**: Standard HTTP push-to-talk is preserved as a fallback for intermittent network environments.
- **Modern Management Studio**: React 18 + Vite + Tailwind CSS dashboard with 8 dedicated workspaces and Progressive Web App (PWA) installation.
- **Production Hardened**: Docker Compose with multi-stage builds, Caddy reverse proxy with automatic HTTPS, HTTP security headers, and SQLite WAL database migrations.

---

## System Architecture

```text
+-----------------------------------------------------------------------------+
|                             ESP32 Client Device                             |
|  - Microcontroller: ESP32-WROOM-32 (240 MHz, 320 KB SRAM, No PSRAM)        |
|  - Audio Input: INMP441 I2S MEMS Microphone (16 kHz, 16-bit Mono)           |
|  - Audio Output: MAX98357A I2S Class D Amplifier + 3W Speaker               |
|  - Visual Display: SSD1306 0.96" OLED (128x64 I2C)                          |
|  - User Input: Push-to-Talk button with hardware debounce                   |
+-----------------------------------------------------------------------------+
                                       |
                   Full-Duplex WebSockets / HTTP Fallback
                                       v
+-----------------------------------------------------------------------------+
|                      MyVoice OS Server (FastAPI Async)                      |
|  - Core Router: WebSocket Message Broker with Barge-In Cancellation         |
|  - Tool Registry: Modular AI Skills with per-device permission enforcement  |
|  - Background Scheduler: 1-second interval timer and alarm monitor          |
|  - OTA Engine: SHA-256 authenticated binary distribution                    |
|  - Multi-Provider Pipeline: OpenAI, Groq, Edge-TTS, and Offline Mocks       |
|  - Storage: SQLite 3 with SQLAlchemy 2.0 and Alembic migrations             |
+-----------------------------------------------------------------------------+
                                       ^
                                       | REST API + SSE
                                       v
+-----------------------------------------------------------------------------+
|                     Management Studio (React 18 + Vite)                     |
|  Fleet Management | Voice Lab | AI Personas | Skills | Timers | OTA | Logs  |
+-----------------------------------------------------------------------------+
```

---

## Hardware Pinout Reference

| Peripheral | Signal | ESP32 Pin | Voltage Rail | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **INMP441 Mic** | VDD | 3V3 | 3.3V Only | Power from 3.3V rail |
| | GND | GND | Ground | Common ground |
| | SD | GPIO 32 | Logic | I2S Serial Data In |
| | WS | GPIO 25 | Logic | I2S Word Select (LRCLK) |
| | SCK | GPIO 33 | Logic | I2S Continuous Clock (BCLK) |
| | L/R | GND | Ground | Tie to GND for Left channel |
| **MAX98357A Amp** | VIN | 5V / VIN | 5V Power | 5V recommended for 3W output |
| | GND | GND | Ground | Common ground |
| | DIN | GPIO 26 | Logic | I2S Serial Data Out |
| | BCLK | GPIO 27 | Logic | I2S Bit Clock |
| | LRC | GPIO 14 | Logic | I2S Left/Right Clock (WS) |
| | GAIN | GND | Ground | 9dB gain (or floating for 12dB) |
| **SSD1306 OLED** | VCC | 3V3 | 3.3V Logic | Standard I2C display |
| | GND | GND | Ground | Common ground |
| | SCL | GPIO 22 | Logic | Hardware I2C Clock |
| | SDA | GPIO 21 | Logic | Hardware I2C Data |
| **Push Button** | Pin 1 | GPIO 0 | Logic | Pull-up enabled in firmware |
| | Pin 2 | GND | Ground | Pressing connects pin to GND |

For detailed power filtering, decoupling capacitors, and wake-word analysis, see [docs/HARDWARE.md](docs/HARDWARE.md).

---

## Quick Start Guide

### 1. Backend Server Setup

```bash
# Clone the repository
git clone <repository_url> myvoice-os
cd myvoice-os

# Create and populate server configuration
cat << 'EOF' > server/.env
ADMIN_PASSWORD=replace-with-a-16-character-or-longer-password
ENROLLMENT_KEY=replace-with-a-24-character-or-longer-random-string
DATABASE_PATH=./myvoice.db
AI_MODEL=gpt-4.1-mini
OPENAI_API_KEY=your-openai-api-key-optional
BRAVE_SEARCH_API_KEY=your-brave-key-optional
EOF

# Install dependencies and launch server
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open your browser to `http://localhost:8000` to access the Management Studio. Login with username `admin` and your configured password.

### 2. Frontend Studio Development

```bash
cd server/frontend
npm install
npm run dev
```

To build production assets served directly by FastAPI:
```bash
npm run build
```

### 3. ESP32 Firmware Build & Flash

```bash
cd firmware
cp include/secrets.h.example include/secrets.h
# Edit include/secrets.h with your Wi-Fi SSID, password, server IP, and enrollment key

# Compile and upload firmware via PlatformIO
pio run --target upload
pio devicemonitor
```

### 4. Running the Software Simulator

You can test the entire voice pipeline, WebSocket streaming, and OTA updates without physical hardware:
```bash
python tools/simulator.py --server http://127.0.0.1:8000 --action ws-cycle
```

---

## Production Deployment with Docker Compose

MyVoice OS includes a production Docker setup featuring Caddy with automatic TLS certificates:

```bash
# Edit domain in Caddyfile
docker compose up -d --build
```

See [docs/DEPLOY.md](docs/DEPLOY.md) for complete production hardening, systemd instructions, and database backup procedures.

---

## Documentation Index

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): Complete system architecture, FreeRTOS dual-core tasks, and WebSocket broker.
- [docs/PROTOCOL.md](docs/PROTOCOL.md): Authoritative device-server communication specification.
- [docs/HARDWARE.md](docs/HARDWARE.md): Hardware schematics, memory budgeting, and wake-word technical feasibility study.
- [docs/BRINGUP.md](docs/BRINGUP.md): Step-by-step physical bring-up guide and smoke test procedures.
- [docs/DEPLOY.md](docs/DEPLOY.md): Production deployment with Docker, Caddy, TLS, and systemd.
- [docs/API.md](docs/API.md): Comprehensive REST and WebSocket API reference.
- [docs/SECURITY.md](docs/SECURITY.md): Threat model, authentication architecture, and token lifecycle.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): Audio noise debugging, Wi-Fi recovery, and common failure modes.

---

## License

MyVoice OS is licensed under the MIT License.
