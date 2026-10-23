# Ahan 1.0 - Smart AI Voice Assistant & Edge IoT Ecosystem

A complete AI voice assistant and edge IoT ecosystem for low-cost ESP32 microcontrollers, self-hosted FastAPI servers, and reactive web administration consoles.

---

## Workspace Architecture

```text
Ahan1.0/
├── myvoice-os/                     # Core Voice Assistant Stack
│   ├── server/                     # FastAPI Async Backend & WebSocket Broker
│   │   ├── app/                    # Routing, STT/TTS pipeline, LLM tools, Auth
│   │   ├── frontend/               # Vite + React 18 Xiaozhi Console Dashboard
│   │   └── static/                 # Production-built web dashboard
│   ├── firmware/                   # ESP32 Firmware
│   │   ├── MyVoiceAssistant/       # Standalone Arduino IDE Sketch (.ino)
│   │   ├── src/ & include/         # PlatformIO modular firmware (C++)
│   │   └── platformio.ini          # PlatformIO board build definitions
│   ├── tools/                      # Hardware simulator & flashing scripts
│   └── docs/                       # Architecture, hardware pinouts & API reference
│
├── xiaozhi-esp32/                  # ESP-IDF C++ Enterprise Voice Firmware
│   ├── main/                       # Application loop, Opus audio, AEC, wake-words
│   └── main/boards/                # 138+ board profiles (ESP32 breadboard, S3-BOX, M5Stack, etc.)
│
└── MyVoice_OS_ESP32_Starter.zip    # Original starter template package
```

---

## Quick Start

### 1. Run the Backend Server & Web Console
```bash
cd myvoice-os/server
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.
- **Username:** `admin`
- **Password:** Configured in `server/.env`

### 2. Frontend Development (Hot Reloading)
```bash
cd myvoice-os/server/frontend
npm install
npm run dev
```

### 3. ESP32 Firmware Options
- **Arduino IDE:** Open `myvoice-os/firmware/MyVoiceAssistant/MyVoiceAssistant.ino`, enter your Wi-Fi credentials, and hit **Upload**.
- **PlatformIO / Terminal:** Plug your ESP32 into USB and run:
  ```bash
  cd myvoice-os
  ./tools/flash_firmware.sh
  ```
- **ESP-IDF Enterprise Client:** See [`xiaozhi-esp32/README.md`](xiaozhi-esp32/README.md).

---

## License
MIT License
