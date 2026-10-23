# MyVoice OS - Phase 2 Implementation Plan

Title: Phase 2 - Real-Time AI Voice Assistant and WebSocket Streaming
Target Architecture: Bidirectional WebSocket Streaming, Multi-Provider AI Engine, Conversation Memory, and Low-Latency Voice Pipeline
Target Hardware: ESP32 DevKit V1 / ESP32-WROOM-32 (Standard ESP32, No PSRAM)
Status: Approved and Completed (Verified via Automated Tests, Live Simulator & Firmware Compilation)

---

## 1. Overview and Objectives

Phase 2 advances MyVoice OS from a half-duplex HTTP push-to-talk prototype into a true real-time, low-latency conversational AI voice assistant inspired by XiaoZhi, while keeping control, branding, and telemetry self-hosted on our own server.

Primary Objectives:
1. Low-Latency WebSocket Transport: Implement `/ws/device` supporting authenticated sessions, JSON control frames, and binary PCM16 audio frames.
2. Lightweight Microcontroller Footprint: Keep the regular ESP32 (320 KB usable SRAM, no PSRAM) lightweight by doing speech recognition, intent routing, and voice synthesis on the server.
3. Multiple AI Providers: Abstract ASR, LLM, and TTS behind extensible provider interfaces:
   - ASR: OpenAI Whisper, Faster-Whisper.
   - LLM: OpenAI, Google Gemini, OpenAI-compatible endpoints, Ollama.
   - TTS: OpenAI TTS, Edge-TTS, Piper.
4. Hot-Swappable Provider Management: Configure global defaults and per-device overrides from the dashboard without restarting the server.
5. Conversation Memory: Isolate persistent conversation history per device with configurable history length, system prompts, custom personalities, and search.
6. Real-Time Interruption (Barge-In): Support client-triggered `abort` (via push button) to immediately halt pending LLM streaming, terminate TTS generation, and clear device playback buffers.
7. Rich Dashboard Additions: Add AI Provider Settings, Conversation History Explorer, Browser Voice Playground (in-browser mic testing), and Live Device Monitor.
8. Enhanced ESP32 Firmware: Add non-blocking WebSocket client, bounded ring buffers, underrun recovery, and OLED state synchronization.
9. Extended Simulator: Upgrade `tools/simulator.py` to test WebSocket handshakes, frame streaming, event processing, latency recording, and audio response verification.
10. Strict Fallback Compatibility: Retain the Phase 1 HTTP push-to-talk voice pipeline (`/api/device/voice`) behind a configuration toggle.

---

## 2. Task Breakdown & Implementation Strategy

### Task 1: WebSocket Protocol Specification & Design
- Endpoint: `/ws/device`
- Authentication Transport: Query parameter authentication `?device_id=...&token=...` or initial `hello` handshake message. Supported cleanly by embedded WebSocket libraries without requiring custom handshake headers.
- Session Management: One active WebSocket connection per physical device. Re-connections gracefully invalidate and close stale sessions.
- Message Framing:
  - Text Frames: JSON control messages (`hello`, `hello_ack`, `listen_start`, `listen_stop`, `stt`, `llm`, `tts_start`, `tts_chunk`, `tts_stop`, `abort`, `ping`, `pong`, `error`).
  - Binary Frames: Raw PCM16 mono 16 kHz audio chunks (60 ms frames = 1,920 bytes).
- Control Flow & State Machine:
  ```text
  Client                                     Server
    |                                           |
    | ----- [JSON: hello] --------------------> | (Validates token against DB)
    | <---- [JSON: hello_ack (session_id)] ---- |
    |                                           |
    | ----- [JSON: listen_start] -------------> | (Transitions to LISTENING)
    | ===== [Binary: 60ms PCM16 chunks] ======> | (Buffers & runs VAD / STT)
    | ----- [JSON: listen_stop] --------------> | (Triggers final transcription)
    |                                           |
    | <---- [JSON: stt (transcript)] ---------- | (Transitions to THINKING)
    | <---- [JSON: llm (delta / chunk)] ------- | (Streams LLM tokens)
    | <---- [JSON: tts_start (hz, format)] ---- | (Transitions to SPEAKING)
    | <==== [Binary: Audio playback chunk] ==== |
    | <---- [JSON: tts_stop] ------------------ | (Returns to IDLE)
  ```
- Action: Document the complete message schemas in `docs/PROTOCOL.md`.

---

### Task 2: Audio Streaming & ESP32 Memory Architecture
- Audio Standard: PCM16 mono audio at 16,000 Hz.
  - Bandwidth: 32,000 bytes/sec (32 KB/s).
  - Frame Size: 60 ms duration = 960 samples = 1,920 bytes.
- Embedded Buffer Management (No PSRAM):
  - Ingress / Egress Ring Buffers: Allocate bounded static buffers (e.g., 6 x 1,920 bytes = 11.5 KB DRAM max).
  - Prevent Heap Churn: Zero dynamic heap allocations during audio streaming; reuse static I2S DMA buffers.
  - Backpressure & Underrun Recovery: Discard incoming frames if device buffers fill beyond safe threshold, reporting `dropped_frames` metric to server.
- Optional Codecs:
  - Keep Opus disabled by default. Retain clean hooks for future lightweight Opus decoders, but prioritize rock-solid PCM16 stability.
- Fallback:
  - Keep HTTP push-to-talk `/api/device/voice` fully operational.

---

### Task 3: Real-Time Server Voice Pipeline
- Pipeline Architecture:
  1. WebSocket Ingest Worker: Validates audio frame sizes, pushes PCM chunks into session buffer.
  2. Voice Activity Detection (VAD): Configurable energy-based VAD with silence timeout (e.g., 800 ms of trailing silence after speech) or client-signaled manual `listen_stop`.
  3. ASR Dispatcher: Transcribes accumulated audio chunks into user prompt.
  4. Intent & Memory Resolver: Loads device conversation history, injects custom system prompts and personality, checks for built-in skills (time, weather, search).
  5. LLM Streaming Engine: Streams text completion tokens via async generator.
  6. Speech Segmenter: Buffers streamed text until clause or punctuation boundaries (`.`, `?`, `!`, `,`, newline) are reached, dispatching text chunks to TTS immediately to minimize time to first audio.
  7. TTS Audio Streamer: Synthesizes audio segments in parallel and pushes binary chunks to the WebSocket client.
  8. Dashboard Telemetry: Broadcasts session state (`idle`, `listening`, `thinking`, `speaking`) to the admin monitoring view.

---

### Task 4: Multi-Provider AI Architecture
- Extensible Interface Hierarchy:
  - `ASRProvider` Base Class:
    - `transcribe(audio_bytes: bytes, language: str) -> str`
    - Implementations: `OpenAIWhisperProvider`, `FasterWhisperProvider` (optional local), `MockASRProvider` (for deterministic tests).
  - `LLMProvider` Base Class:
    - `stream_chat(messages: list, model: str, temperature: float) -> AsyncGenerator[str, None]`
    - Implementations: `OpenAILLMProvider`, `GeminiLLMProvider`, `OpenAICompatibleProvider`, `OllamaProvider`, `MockLLMProvider`.
  - `TTSProvider` Base Class:
    - `synthesize_stream(text: str, voice: str, language: str) -> AsyncGenerator[bytes, None]`
    - Implementations: `OpenAITTSProvider`, `EdgeTTSProvider`, `PiperTTSProvider` (optional local), `MockTTSProvider`.
- Isolation: Provider implementations reside in isolated modules under `server/app/services/providers/`.
- Dependency Safety: Optional providers (Faster-Whisper, Piper) degrade gracefully if libraries or local models are uninstalled.

---

### Task 5: Dynamic Provider Configuration & Secrets
- Settings Hierarchy:
  1. System Defaults: Configured in `server/.env`.
  2. Database Defaults: Configurable via Dashboard for the whole server instance.
  3. Per-Device Overrides: Stored in `devices` table (e.g., `asr_provider`, `llm_provider`, `tts_provider`, `llm_model`, `tts_voice`).
- Hot-Swapping:
  - Changes take effect on the very next conversation turn without restarting Uvicorn or the FastAPI backend.
- Secret Protection:
  - API keys are stored only in server `.env` or in a dedicated write-only backend table.
  - Dashboard APIs return masked strings (e.g., `sk-...****`) and never leak plaintext keys to client JavaScript.
- Health Check Endpoints:
  - `POST /api/admin/providers/test`: Tests connectivity and credentials for any selected provider and model.

---

### Task 6: Conversation Memory Engine
- Database Schema Evolution (Alembic Migration):
  - Table `conversations`:
    - `id` (String PK, UUID)
    - `device_id` (String FK, index)
    - `title` (String)
    - `created_at` (String ISO)
    - `updated_at` (String ISO)
  - Table `messages`:
    - `id` (String PK, UUID)
    - `conversation_id` (String FK, index)
    - `role` (String: `user` | `assistant` | `system`)
    - `content` (Text)
    - `latency_ms` (Integer nullable)
    - `provider_info` (String JSON nullable)
    - `created_at` (String ISO)
- Features:
  - Configurable history window: Injects the last N conversation turns (default 6) into the LLM context.
  - Custom system prompt, assistant name, and personality configurable per device in dashboard.
  - Conversation search API (`GET /api/admin/conversations/search?q=...`).
  - Conversation deletion API (`DELETE /api/admin/conversations/{id}`).

---

### Task 7: Barge-In and Interruption Handling
- Abort Signal Flow:
  1. User presses button on physical device during AI speech output.
  2. ESP32 immediately stops speaker DMA output, clears local ring buffer, and sends `{"type": "abort"}` over WebSocket.
  3. Server receives `abort` message:
     - Cancels active asyncio background tasks for LLM generation.
     - Cancels pending TTS synthesis workers.
     - Drops queued audio chunks.
     - Sends `{"type": "abort_ack"}` to device.
     - Transitions server session state back to `LISTENING`.

---

### Task 8: Dashboard Upgrade
- Extended Frontend Components in `server/frontend/`:
  - `AIProviderSettings.tsx`: Form to select ASR, LLM, and TTS providers, models, voices, and run connection diagnostics.
  - `ConversationViewer.tsx`: Searchable list of conversations, message history viewer, latency breakdown badges, and deletion buttons.
  - `VoicePlayground.tsx`: Uses browser `MediaDevices.getUserMedia` to stream real audio over WebSocket directly to `/ws/device`, display live transcription, and play AI speech in browser.
  - `LiveDeviceMonitor.tsx`: Real-time session status card displaying whether a device is Idle, Listening, Thinking, or Speaking, with latency metrics.
- Output: Re-build frontend into `server/static/`.

---

### Task 9: ESP32 Firmware WebSocket Module
- Firmware Additions under `firmware/src/` and `firmware/include/`:
  - `ws_client.h` / `ws_client.cpp`: Lightweight WebSocket client using `arduinoWebSockets` or `ESP8266WebSockets` library.
  - Ring Buffer: Fixed 12 KB circular buffer for audio output streaming to MAX98357A.
  - Button Interruption: Button press during audio playback triggers immediate `abort` frame transmission and resets I2S DMA.
  - OLED Display Sync: OLED state changes seamlessly between `LISTENING`, `THINKING`, `SPEAKING`, and `IDLE_CLOCK` based on WebSocket events.

---

### Task 10: WebSocket Device Simulator (`tools/simulator.py`)
- Simulator Capabilities:
  - Connects to `ws://127.0.0.1:8000/ws/device?device_id=...&token=...`.
  - Performs `hello` handshake and waits for `hello_ack`.
  - Streams 60 ms PCM16 audio chunks from a WAV file or synthetic sine wave.
  - Sends `listen_stop` and listens for `stt`, `llm`, `tts_start`, binary audio chunks, and `tts_stop`.
  - Measures latency benchmarks (STT latency, LLM first-token time, TTS first-audio time, round-trip time).
  - Writes received audio to disk for audible verification.

---

### Task 11: Latency Telemetry & Benchmarking
- Metrics Recorded:
  - Connection Setup Time (ms)
  - Audio Stream Duration (ms)
  - ASR Transcription Latency (ms)
  - LLM Time to First Token (ms)
  - TTS Time to First Audio Chunk (ms)
  - Total Turnaround Time (ms)
- Telemetry stored with each message in database and surfaced in the dashboard.

---

### Task 12: Automated Testing & Verification
- Test Matrix:
  1. `test_ws_auth.py`: Validates WebSocket token authentication, rejection of revoked/invalid tokens, single session per device.
  2. `test_pipeline.py`: Tests end-to-end mocked audio streaming, transcription, LLM completion, speech chunking, and binary audio return.
  3. `test_interruption.py`: Validates abort message handling, task cancellation, and buffer purging.
  4. `test_providers.py`: Tests provider switching, fallback behavior, and timeout management.
  5. `test_conversations.py`: Tests conversation creation, isolation per device, search, and history trimming.
  6. Simulator Regression: Runs `tools/simulator.py --protocol ws --action voice-cycle`.
  7. Firmware Build Verification: Runs `pio run` to verify clean compilation of the WebSocket module.

---

## 3. Strict Safety & Phase 2 Boundary Rules

1. Stop after Phase 2 completion and wait for explicit user approval before proceeding to Phase 3.
2. Maintain backward-compatible HTTP fallback without breaking Phase 1 APIs.
3. No em dashes used in generated text, documentation, or code comments.
4. Physical hardware verification must remain marked as UNVERIFIED until tested on workbench.
5. All secrets (.env, database, tokens) remain excluded from Git.

---

## 4. Phase 2 Implementation Summary & Verification

### Deliverables Completed:
1. WebSocket Protocol: Documented in `docs/PROTOCOL.md` (Section 6) with full handshake, frame format, and control messages.
2. Endpoint: `/ws/device` implemented in `server/app/routers/ws_device.py`.
3. Multi-Provider AI Architecture: Abstracted under `server/app/services/providers/` for ASR (OpenAI Whisper, Faster-Whisper, Mock), LLM (OpenAI, Gemini, Ollama, OpenAI-compatible, Mock), and TTS (Edge-TTS, OpenAI TTS, Piper, Mock).
4. Audio Decoding: Integrated `miniaudio` and `edge-tts` for real-time neural voice synthesis in English and Bangla.
5. Conversation Memory: `conversations` and `messages` tables created via Alembic migration `ceb0f39334f2_phase2_schema.py`.
6. Dashboard AI Management: Added AI Provider Settings, Conversation History Explorer, Browser Voice Playground, and Live Device Monitor.
7. Device Firmware: Implemented `ws_client.cpp` / `ws_client.h` for ESP32 with 16 kHz PCM streaming and button barge-in abort. Compiled cleanly with PlatformIO (16.4% RAM used).
8. WebSocket Simulator: Extended `tools/simulator.py` with `ws-cycle` and `ws-voice` measuring round-trip latency and saving response audio.
9. Barge-In Interruption: Tested and verified client button abort stops server generation and resets state.
10. Fallback: Retained Phase 1 HTTP push-to-talk (`/api/device/voice`) behind configuration.

### Verification Status:
- Pytest Suite: 16/16 tests passing (`test_app.py`, `test_phase1.py`, `test_phase2.py`).
- PlatformIO Compilation: PASS (Flash: 82.2%, RAM: 16.4% on standard ESP32 without PSRAM).
- Frontend Build: PASS (`npm run build` completed in 1.79s, 0 errors).
- Live Simulator Test: PASS (1,989 ms turnaround, 12,800 bytes received audio saved).
- Physical Hardware Testing: Marked as UNVERIFIED pending bench testing.

