# 🦅 FALCON AI - Self-Hosted ESP32 AI Voice Assistant Ecosystem

Falcon AI is a complete, independently branded, production-ready AI voice assistant platform inspired by XiaoZhi. It operates entirely on your own infrastructure without dependencies on official `xiaozhi.me` cloud servers or third-party device registries.

---

## 🌟 Key Features

- **Independently Branded Firmware**: Custom boot splash, SSD1306 OLED state machine, captive portal Wi-Fi setup (`FalconAI-Setup`), dual push-to-talk buttons (`GPIO 0` & `GPIO 27`), and LittleFS credential storage.
- **Hardware Target**: Standard ESP32 Dev Board (ESP32-WROOM-32, 240 MHz, 320 KB SRAM, NO PSRAM required), INMP441 I2S microphone, MAX98357A I2S amplifier, 3W speaker.
- **Real-Time AI Audio Gateway**: 16 kHz PCM16 full-duplex WebSocket audio streaming with barge-in interruption (< 1.05s turnaround).
- **Bilingual Speech Engine**: First-class support for English and Bengali (বাংলা) speech recognition and neural synthesis (`bn-BD-NabanitaNeural`, `bn-BD-PradeepNeural`).
- **AI Agent Studio**: Multi-agent management allowing custom avatars, prompts, language preferences, model providers (Gemini, OpenAI, Ollama), and real-time device assignment.
- **Enterprise Web Console**: Modern 9-tab SaaS dashboard with dark/light mode, device telemetry, live sessions, OTA release catalog, and interactive tool execution.
- **Zero-Trust Device Pairing**: Ephemeral 6-digit codes with cryptographic token verification, anti-brute-force rate limiting, and instant token revocation.
- **Over-The-Air (OTA) Updates**: Binary catalog management with SHA-256 verification and fail-safe dual-slot partition flashing.

---

## 📁 Repository Layout

```text
├── docs/                           # Comprehensive Engineering Documentation
│   ├── WORKSPACE_AUDIT.md          # Workspace audit and inventory
│   ├── EXISTING_FEATURES.md        # Feature implementation status matrix
│   ├── IMPLEMENTATION_ROADMAP.md   # 12-stage execution roadmap
│   ├── ARCHITECTURE.md             # Formal system architecture & ADRs
│   ├── HARDWARE_WIRING.md          # Complete ESP32 pinout and wiring guide
│   ├── FIRMWARE_BUILD.md           # PlatformIO & Arduino IDE build guide
│   ├── DEVICE_PAIRING.md           # Zero-trust device activation walkthrough
│   ├── AI_PROVIDER_SETUP.md        # Gemini, OpenAI, Ollama, Edge-TTS setup
│   ├── LOCAL_DEPLOYMENT.md         # Local & Docker Compose deployment
│   ├── PRODUCTION_DEPLOYMENT.md    # VPS, Caddy/Nginx, Systemd, Vercel guide
│   ├── OTA_GUIDE.md                # OTA packaging and broadcast update guide
│   ├── API_REFERENCE.md            # REST and WebSocket protocol specification
│   ├── TEST_REPORT.md              # 33/33 test report & latency benchmarks
│   └── KNOWN_LIMITATIONS.md        # Hardware RAM and audio trade-offs
│
├── myvoice-os/
│   ├── server/                     # FastAPI Async Real-Time Backend
│   │   ├── app/                    # Routers, providers, memory, tools, models
│   │   ├── frontend/               # Vite + React 18 Falcon AI Console
│   │   ├── static/                 # Production-built web console assets
│   │   └── tests/                  # Pytest automated test suite (33 tests)
│   ├── firmware/                   # Falcon AI ESP32 Firmware
│   │   ├── src/ & include/         # Modular C++ firmware (PlatformIO)
│   │   ├── MyVoiceAssistant/       # Standalone Arduino IDE sketch (.ino)
│   │   └── platformio.ini          # ESP-IDF / Arduino board configuration
│   └── tools/                      # Hardware simulator & flashing utilities
│
├── xiaozhi-esp32/                  # Upstream ESP-IDF reference implementation
├── xiaozhi-esp32-server/           # Upstream reference server repository
└── vercel.json                     # Multi-service Vercel deployment configuration
```

---

## 🚀 Quick Start

### 1. Launch the Backend Server
```bash
cd myvoice-os/server
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser:
- **Username:** `admin`
- **Password:** `12345678` (configured in `server/.env`)

### 2. Frontend Hot-Reload Development
```bash
cd myvoice-os/server/frontend
npm install
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** to access the live Falcon AI Console.

### 3. Flash ESP32 Firmware
Connect your ESP32 board via USB and run:
```bash
cd myvoice-os/firmware
pio run -e esp32dev --target upload
```

### 4. Run Hardware Simulator Test
```bash
cd myvoice-os
./server/.venv/bin/python tools/simulator.py --server http://127.0.0.1:8000 --action ws-cycle
```

---

## 📄 License & Attribution
- Falcon AI Platform is licensed under the Apache 2.0 / MIT licenses.
- Preserves upstream open-source attributions to XiaoZhi ESP32 and community projects.


## License
MIT License
