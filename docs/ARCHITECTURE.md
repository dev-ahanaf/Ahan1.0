# Falcon AI - System Architecture Specification (Stage 1)

**System Name:** Falcon AI Platform  
**Target Hardware:** Regular ESP32 Development Board (ESP32-WROOM-32, 320 KB SRAM, No PSRAM)  
**Reference Model:** XiaoZhi Protocol & Architecture Principles  

---

## 1. Architectural Philosophy & Evaluation

Falcon AI is designed as a self-hosted, independent, low-latency AI voice assistant ecosystem. 

### Decision on Server Architecture:
During the Stage 0 audit, two potential architectures were evaluated:
1. **Upstream `xiaozhi-esp32-server`**:
   - Comprises a Java 17+ Spring Boot management backend (`manager-api`), a Vue 3 management frontend (`manager-web`), and a Python Opus audio streamer (`xiaozhi-server`).
   - Requires external runtime services: `mvn`, `mysqld`, and `redis-server`.
   - Forces Opus 60 ms frames, which exceeds the memory and compute capacity of standard ESP32 microcontrollers lacking external PSRAM.
2. **Existing Core (`myvoice-os`)**:
   - Asynchronous Python (FastAPI) runtime with an integrated WebSocket message broker and background asyncio scheduler.
   - Zero external infrastructure dependency; runs with high-performance SQLite WAL mode (and ready for PostgreSQL).
   - Designed around a FreeRTOS dual-core task partition on ESP32 using raw 16 kHz PCM16 frames, keeping total firmware RAM usage below 54 KB (16.4% of SRAM).
   - Already delivers verified 947 ms end-to-end voice turnaround.

**Decision**: Falcon AI adopts and expands the lightweight, high-throughput async FastAPI core and React 18 / Tailwind console, while importing the multi-agent management, Bengali speech pipelines, and MCP device skill framework inspired by XiaoZhi.

---

## 2. Platform Architecture Topology

```text
+-----------------------------------------------------------------------------------+
|                        Falcon AI ESP32 Client Device                              |
|  - Microcontroller: ESP32-WROOM-32 (240 MHz, 320 KB SRAM, No PSRAM)               |
|  - Audio Input: INMP441 I2S MEMS Microphone (16 kHz, 16-bit Mono)                 |
|  - Audio Output: MAX98357A I2S Class D Amplifier + 3W Speaker                     |
|  - Visual Display: SSD1306 0.96" OLED (128x64 I2C)                                |
|  - Input: Dual Push-to-Talk (Onboard BOOT GPIO 0 & External Tactile GPIO 27)      |
+-----------------------------------------------------------------------------------+
                                          |
                        Full-Duplex WebSockets / HTTP Fallback
                                          v
+-----------------------------------------------------------------------------------+
|                        Falcon AI Server (FastAPI Async)                           |
|  - Core Router: WebSocket Message Broker with Barge-In Interruption               |
|  - Agent Engine: Dynamic Agent Resolver (System Prompt, Personality, Voice)       |
|  - Tool Registry: Modular AI Skills (Clock, Weather, Search, Timers, Alarms)      |
|  - Background Worker: 1-second interval scheduler for Spoken Alerts               |
|  - Multilingual Pipeline: OpenAI, Groq, Ollama, Edge-TTS (Bangla & English)       |
|  - Database: SQLAlchemy 2.0 with SQLite WAL / PostgreSQL migrations               |
+-----------------------------------------------------------------------------------+
                                          ^
                                          | REST API + Server-Sent Events
                                          v
+-----------------------------------------------------------------------------------+
|                     Falcon AI Web Console (React 18 + Vite)                       |
|   Dashboard | My Devices | AI Agents | Voice Studio | Models | Tools | OTA | Admin|
+-----------------------------------------------------------------------------------+
```

---

## 3. Data Model & Entity Relationship

```text
[ User / Account ]
       │ 1
       │ N
[ AI Agent ] ─────────┐ 1
       │ 1            │ N
       │ N            ▼
[ Conversation ] ◄── [ Device ] ──── 1:N ──── [ Device Telemetry ]
       │ 1               │ 1
       │ N               │ N
   [ Message ]      [ Timer / Alarm ]
```

### Core Entities:
1. **`AIAgent`**: Defines personality, system prompt, preferred language (`en` or `bn`), model provider (`openai`, `groq`, `ollama`), model name, and TTS voice (`bn-BD-NabanitaNeural`, `en-US-AriaNeural`).
2. **`Device`**: Physical ESP32 identified by MAC address, persistent SHA-256 token hash, pairing status, assigned `agent_id`, audio volume, and screen brightness.
3. **`PairingCode`**: Short-lived (10-minute TTL) single-use 6-digit activation code.
4. **`Timer` & `Alarm`**: Persistent server-side scheduler jobs that dispatch spoken audio alerts and OLED notifications to the connected device upon expiry.
5. **`FirmwareRelease`**: Cryptographically authenticated binary artifact with SHA-256 checksum and hardware target tag.

---

## 4. Voice Processing Flow

```text
1. User presses button (GPIO 0 / 27)
     │
2. Firmware sends WebSocket frame: {"type":"listen_start"}
     │
3. Firmware streams 16 kHz 16-bit PCM binary audio frames over WebSocket
     │
4. User releases button -> Firmware sends {"type":"listen_stop"}
     │
5. Server ASR (Whisper / Groq) transcribes speech (supports Bengali & English)
     │
6. Server Agent Engine resolves assigned AI Agent's prompt & personality
     │
7. Server LLM executes authorized tools (Weather / Clock / Search / Timers)
     │
8. Server TTS generates streaming PCM16 audio chunks
     │
9. Server streams audio chunks to ESP32 over WebSocket
     │
10. ESP32 DAC/Amp plays audio through 3W speaker while OLED renders voice waves
```

---

## 5. Security & Authentication Architecture

1. **Device Provisioning**: Unpaired devices send an enrollment key over TLS to obtain an initial token and a 6-digit pairing code.
2. **Device Authentication**: Authenticated WebSocket handshakes validate `?device_id=MAC&token=TOKEN` against the database's SHA-256 hash.
3. **Console Security**: Administrative operations enforce HTTP Basic Auth or session tokens with role-based access control.
4. **Credential Isolation**: AI provider keys (OpenAI, Groq, Brave) remain strictly server-side and are never transmitted to client devices or browser frontends.
