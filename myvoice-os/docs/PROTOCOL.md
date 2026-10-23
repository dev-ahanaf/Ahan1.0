# MyVoice OS - Device-Server Protocol Specification (v1.0)

Status: Authoritative Protocol Specification
Version: 1.0 (Phase 1 Baseline)
Transport: HTTP/1.1 over Local Area Network (Plaintext HTTP)
Payload Formats: JSON (`application/json`), Audio (`audio/wav`)

---

## 1. Protocol Architecture & Philosophy

The MyVoice OS protocol is designed for embedded microcontrollers (specifically ESP32-WROOM-32 without external PSRAM) communicating with a self-hosted FastAPI backend over a trusted local network.

Key Design Tenets:
- Stateless HTTP Transactions: Eliminates heavy persistent TCP/WebSocket connections from constrained microcontroller heap.
- Asymmetric Credentials: New devices bootstrap with a shared enrollment key, but immediately transition to per-device tokens. The enrollment key cannot manipulate or hijack already-paired devices.
- Configuration Synchronization: Configuration updates made via the web dashboard are versioned (`config_version`). Microcontrollers detect version increments via periodic heartbeats and fetch updated settings on demand.
- Audio Framing: Half-duplex push-to-talk audio streaming. Recordings are transmitted as canonical RIFF/WAV files, and synthesized responses are returned as streaming RIFF/WAV files for direct output to I2S DMA buffers.

---

## 2. Authentication & Identity Model

### 2.1. Headers
- `X-Enrollment-Key`: Secret pre-shared key shared between firmware configuration (`secrets.h`) and backend `.env`. Required solely for initial unprovisioned bootstrap.
- `X-Device-ID`: Hardware client identifier (MAC address formatted as `AA:BB:CC:DD:EE:FF` or lowercase with colons, normalized to uppercase by backend).
- `X-Device-Token`: 32-byte URL-safe secret token issued by the backend during bootstrap. Stored in ESP32 NVS flash and stored as a SHA-256 hash in the backend database.
- `Authorization`: HTTP Basic Auth (`admin:<ADMIN_PASSWORD>`) utilized exclusively for web dashboard and administrative management endpoints.

### 2.2. Device State Lifecycle

```text
[ Unprovisioned ]
       |
       | Wi-Fi captive portal setup
       v
[ Connected to LAN ]
       |
       | POST /api/device/bootstrap (Headers: X-Enrollment-Key)
       v
[ Pending Pairing ] <-------------+
       |                          | Code expired (>10m)
       | GET /api/device/status   | Automatic code renewal
       | (Poll every 5s) ---------+
       |
       | Admin submits 6-digit code via Dashboard
       | POST /api/admin/claim
       v
[ Paired & Active ]
       |
       |-- POST /api/device/heartbeat (every 30s)
       |-- GET /api/device/config (when config_version increments)
       |-- GET /api/device/weather (every 5-15m)
       `-- POST /api/device/voice (on button press)
```

---

## 3. Device API Endpoints

### 3.1. Device Bootstrap
- Method: `POST`
- Path: `/api/device/bootstrap`
- Purpose: Register a new device identity, generate a per-device authentication token, and issue an expiring 6-digit pairing code.
- Headers:
  - `Content-Type: application/json`
  - `X-Enrollment-Key: <ENROLLMENT_KEY>`
- Request Body:
```json
{
  "device_id": "AA:BB:CC:DD:EE:11",
  "firmware": "0.1.0"
}
```
- Response (200 OK):
```json
{
  "token": "dGhpc19pc19hX3VuaXF1ZV8zMl9ieXRlX3Rva2VuX3ZhbHVl",
  "pair_code": "849201",
  "expires_in_seconds": 600,
  "paired": false
}
```
- Error Codes:
  - `401 Unauthorized`: Missing or invalid `X-Enrollment-Key`.
  - `409 Conflict`: Device is already registered and paired. Must be unlinked/reset via dashboard before re-bootstrapping.

### 3.2. Device Status & Code Renewal
- Method: `GET`
- Path: `/api/device/status`
- Purpose: Polled by firmware while waiting for pairing. Returns pairing state and rotates expired pairing codes.
- Headers:
  - `X-Device-ID: AA:BB:CC:DD:EE:11`
  - `X-Device-Token: <DEVICE_TOKEN>`
- Response (200 OK):
```json
{
  "paired": false,
  "name": "My Desk Assistant",
  "pair_code": "849201",
  "city": "Dhaka",
  "timezone": "Asia/Dhaka",
  "config_version": 1
}
```
- Behavior: If `paired` is false and the existing code has expired (>10 minutes), a new 6-digit pairing code is generated and returned. When `paired` becomes true, `pair_code` is returned as `null`.

### 3.3. Heartbeat & Keepalive
- Method: `POST`
- Path: `/api/device/heartbeat`
- Purpose: Periodic keepalive (every 30s) to track device online status and notify client of configuration version changes.
- Headers:
  - `Content-Type: application/json`
  - `X-Device-ID: AA:BB:CC:DD:EE:11`
  - `X-Device-Token: <DEVICE_TOKEN>`
- Request Body:
```json
{
  "free_heap": 184512,
  "wifi_rssi": -58
}
```
- Response (200 OK):
```json
{
  "ok": true,
  "name": "My Desk Assistant",
  "server_utc": "2026-10-19T15:30:00Z",
  "config_version": 2
}
```
- Error Codes:
  - `401 Unauthorized`: Token invalid or revoked.
  - `403 Forbidden`: Device exists but is not yet claimed/paired.

### 3.4. Dynamic Configuration Retrieval
- Method: `GET`
- Path: `/api/device/config`
- Purpose: Fetched by device whenever heartbeat returns a `config_version` higher than local stored version.
- Headers:
  - `X-Device-ID: AA:BB:CC:DD:EE:11`
  - `X-Device-Token: <DEVICE_TOKEN>`
- Response (200 OK):
```json
{
  "config_version": 2,
  "name": "My Desk Assistant",
  "timezone": "Asia/Dhaka",
  "language": "en",
  "city": "Dhaka",
  "latitude": 23.8103,
  "longitude": 90.4125,
  "oled_brightness": 128,
  "idle_display_mode": "clock",
  "clock_format": "24h",
  "speaker_volume": 80,
  "mic_gain": 50,
  "wake_mode": "button",
  "weather_enabled": true,
  "search_enabled": true,
  "timers_enabled": true
}
```

### 3.5. Local Time Synchronization
- Method: `GET`
- Path: `/api/device/time`
- Headers:
  - `X-Device-ID: AA:BB:CC:DD:EE:11`
  - `X-Device-Token: <DEVICE_TOKEN>`
- Response (200 OK):
```json
{
  "local_time": "2026-10-19T21:30:00+06:00",
  "timezone": "Asia/Dhaka",
  "epoch_seconds": 1792423800,
  "utc_offset_seconds": 21600
}
```

### 3.6. Local Weather Information
- Method: `GET`
- Path: `/api/device/weather`
- Headers:
  - `X-Device-ID: AA:BB:CC:DD:EE:11`
  - `X-Device-Token: <DEVICE_TOKEN>`
- Response (200 OK):
```json
{
  "city": "Dhaka",
  "temperature_c": 28.5,
  "conditions": "partly cloudy",
  "wind_kmh": 6.2,
  "weather_code": 2
}
```

### 3.7. Push-to-Talk Voice Exchange
- Method: `POST`
- Path: `/api/device/voice`
- Headers:
  - `Content-Type: audio/wav`
  - `X-Device-ID: AA:BB:CC:DD:EE:11`
  - `X-Device-Token: <DEVICE_TOKEN>`
- Request Body: Binary RIFF/WAVE PCM mono audio, 16,000 Hz sample rate, 16-bit signed integer depth. Maximum allowed payload size: 192,000 bytes (~6 seconds max, default 3 seconds = 96,044 bytes).
- Response (200 OK):
  - `Content-Type: audio/wav`
  - `X-Transcript-Available: true`
  - `X-Transcript-Text: <URL-encoded transcription string>`
  - Response Body: Binary RIFF/WAVE PCM mono audio, 16,000 or 24,000 Hz, 16-bit depth.
- Error Codes:
  - `400 Bad Request`: Invalid WAV header or corrupted data.
  - `413 Payload Too Large`: Audio exceeds maximum byte limit.
  - `415 Unsupported Media Type`: Non-WAV Content-Type.
  - `502 Bad Gateway`: Cloud speech or LLM provider failure.
  - `503 Service Unavailable`: Voice processing keys not configured.

---

## 4. Administrative & Management API Endpoints

### 4.1. System Health
- Method: `GET`
- Path: `/api/health`
- Auth: None
- Response (200 OK):
```json
{
  "status": "ok",
  "service": "MyVoice OS",
  "version": "0.1.0"
}
```

### 4.2. List Registered Devices
- Method: `GET`
- Path: `/api/admin/devices`
- Auth: HTTP Basic Auth (`admin`)
- Response (200 OK):
```json
{
  "devices": [
    {
      "id": "AA:BB:CC:DD:EE:11",
      "name": "My Desk Assistant",
      "paired": true,
      "created_at": "2026-10-19T14:00:00Z",
      "last_seen": "2026-10-19T15:29:45Z",
      "firmware": "0.1.0",
      "city": "Dhaka",
      "latitude": 23.8103,
      "longitude": 90.4125,
      "timezone": "Asia/Dhaka",
      "config_version": 2,
      "online": true
    }
  ]
}
```

### 4.3. Claim Device by Pairing Code
- Method: `POST`
- Path: `/api/admin/claim`
- Auth: HTTP Basic Auth (`admin`)
- Rate Limit: Maximum 5 failed attempts per minute per IP address.
- Request Body:
```json
{
  "code": "849201",
  "name": "Living Room Assistant"
}
```
- Response (200 OK):
```json
{
  "paired": true,
  "device_id": "AA:BB:CC:DD:EE:11",
  "name": "Living Room Assistant"
}
```
- Error Codes:
  - `404 Not Found`: Invalid or expired pairing code.
  - `429 Too Many Requests`: Rate limit exceeded.

### 4.4. Update Device Settings
- Method: `POST`
- Path: `/api/admin/devices/{device_id}/settings`
- Auth: HTTP Basic Auth (`admin`)
- Request Body:
```json
{
  "name": "Living Room Assistant",
  "timezone": "Asia/Dhaka",
  "language": "en",
  "city": "Dhaka",
  "latitude": 23.8103,
  "longitude": 90.4125,
  "oled_brightness": 128,
  "idle_display_mode": "clock",
  "clock_format": "24h",
  "speaker_volume": 80,
  "mic_gain": 50,
  "wake_mode": "button",
  "weather_enabled": true,
  "search_enabled": true,
  "timers_enabled": true
}
```
- Response (200 OK):
```json
{
  "ok": true,
  "config_version": 3
}
```

### 4.5. Rotate Device Token
- Method: `POST`
- Path: `/api/admin/devices/{device_id}/rotate-token`
- Auth: HTTP Basic Auth (`admin`)
- Purpose: Generates a new token. The new token is returned once to admin and can be flashed or re-injected.
- Response (200 OK):
```json
{
  "ok": true,
  "device_id": "AA:BB:CC:DD:EE:11",
  "new_token": "bmV3X3Rva2VuX3ZhbHVlX2hlcmU"
}
```

### 4.6. Revoke Device
- Method: `POST`
- Path: `/api/admin/devices/{device_id}/revoke`
- Auth: HTTP Basic Auth (`admin`)
- Purpose: Permanently un-pairs and marks device token as revoked. Future device requests return 401.
- Response (200 OK):
```json
{
  "ok": true,
  "revoked": true,
  "device_id": "AA:BB:CC:DD:EE:11"
}
```

### 4.7. Admin Test Command
- Method: `POST`
- Path: `/api/admin/ask`
- Auth: HTTP Basic Auth (`admin`)
- Request Body:
```json
{
  "text": "What is the weather today?",
  "device_id": "AA:BB:CC:DD:EE:11"
}
```
- Response (200 OK):
```json
{
  "answer": "In Dhaka, it's 28.5 degrees Celsius with partly cloudy skies."
}
```

---

## 5. Summary of Safety & Security Guarantees

1. Hashed Storage: Server stores only `sha256(device_token)` and `sha256(ENROLLMENT_KEY + ":" + pair_code)`. Plaintext credentials are never kept in database tables.
2. Single-Use Codes: Upon successful claim, `pair_hash` and `pair_expires` are nulled immediately.
3. Strict Expiry: Pairing codes automatically expire after 10 minutes.
4. Non-Interference: A bootstrap request targeting an already-paired device ID returns `409 Conflict` and does NOT overwrite or compromise existing credentials.

---

## 6. Real-Time WebSocket Protocol (`/ws/device`)

### 6.1. Connection & Authentication Transport
- URL: `ws://<SERVER_IP>:<PORT>/ws/device`
- Authentication Mechanism:
  - Query parameters: `?device_id=<DEVICE_MAC>&token=<DEVICE_TOKEN>`
  - Initial `hello` message payload (fallback when query parameters cannot be appended).
- Authentication Handshake:
  1. Microcontroller opens WebSocket connection with `device_id` and `token`.
  2. Server queries `devices` table by `id=device_id`.
  3. Server computes `sha256(token)` and compares with stored `token_hash`.
  4. If device is unverified, revoked, or token mismatch: Server sends `error` message and closes WebSocket with code `4001` (Unauthorized) or `4003` (Revoked).
  5. Session Concurrency: Each physical device is allowed exactly ONE active WebSocket session. If a new connection initiates for an already connected `device_id`, the preceding session is closed with code `4009` (Session Replaced) to avoid split-brain audio state.

### 6.2. Frame Framing Rules
- Text Frames: UTF-8 encoded JSON objects containing a mandatory `"type"` string.
- Binary Frames: Raw uncompressed PCM16 signed little-endian audio samples at 16,000 Hz mono (default 60 ms frames = 960 samples = 1,920 bytes).
- Server to Device Audio: Sent as raw binary PCM16 frames preceded by a `tts_start` JSON frame and concluded by a `tts_stop` JSON frame.

### 6.3. Control Message Schemas

#### Device -> Server: `hello`
```json
{
  "type": "hello",
  "firmware": "1.0.0",
  "audio": {
    "codec": "pcm16",
    "sample_rate": 16000,
    "channels": 1,
    "frame_ms": 60
  }
}
```

#### Server -> Device: `hello_ack`
```json
{
  "type": "hello_ack",
  "session_id": "c7a8b3e2-6320-42f1-bc8b-d72b21cfbc80",
  "config": {
    "language": "en",
    "speaker_volume": 80,
    "mic_gain": 50,
    "idle_display_mode": "clock",
    "clock_format": "24h"
  },
  "config_version": 1
}
```

#### Device -> Server: `listen_start`
Signals the beginning of voice input (e.g., button press or local VAD trigger).
```json
{
  "type": "listen_start",
  "mode": "manual"
}
```

#### Binary Audio Streaming (Device -> Server)
Continuous stream of binary frames (1,920 bytes each). Server ingests frames into an in-memory session buffer.

#### Device -> Server: `listen_stop`
Signals completion of voice input (e.g., button release). Triggers speech recognition.
```json
{
  "type": "listen_stop"
}
```

#### Server -> Device: `stt`
Emitted immediately when speech-to-text finishes.
```json
{
  "type": "stt",
  "text": "What time is it in Tokyo?",
  "final": true
}
```

#### Server -> Device: `llm`
Emitted incrementally as the language model generates response tokens.
```json
{
  "type": "llm",
  "delta": "The current time in Tokyo is ",
  "final": false
}
```

#### Server -> Device: `tts_start`
Notifies client that synthesized audio playback is beginning.
```json
{
  "type": "tts_start",
  "codec": "pcm16",
  "sample_rate": 16000,
  "channels": 1
}
```

#### Binary Audio Playback (Server -> Device)
Continuous stream of binary PCM16 audio chunks for direct feed to I2S amplifier DMA.

#### Server -> Device: `tts_stop`
Notifies client that synthesis and streaming have completed.
```json
{
  "type": "tts_stop"
}
```

#### Device -> Server: `abort` (Barge-In / Interruption)
Emitted when user interrupts an ongoing AI response (e.g., button press during playback).
```json
{
  "type": "abort",
  "reason": "user_interrupt"
}
```
Server action:
1. Immediately cancels active background tasks for LLM generation and TTS synthesis.
2. Flushes any queued binary audio chunks.
3. Sends `abort_ack` to client.
4. Transitions server session state back to `LISTENING` or `IDLE`.

#### Server -> Device: `abort_ack`
```json
{
  "type": "abort_ack"
}
```

#### Heartbeat & Keep-Alive: `ping` / `pong`
Either peer may send:
```json
{"type": "ping"}
```
Recipient must reply immediately with:
```json
{"type": "pong"}
```

#### Server -> Device: `config_update`
Sent when an administrator alters device configuration in the dashboard while a WebSocket connection is active.
```json
{
  "type": "config_update",
  "config": {
    "speaker_volume": 90
  },
  "config_version": 2
}
```

#### Error Frame
```json
{
  "type": "error",
  "code": "BUFFER_OVERFLOW",
  "message": "Audio stream exceeded maximum allowed duration of 30 seconds."
}
```

### 6.4. Session Lifecycle State Machine

```text
                  +-------------+
                  | Disconnected|
                  +-------------+
                         |
                 TCP + WS Handshake
                 (Auth verified)
                         v
                  +-------------+
           +----->|    IDLE     |<----+
           |      +-------------+     |
           |             |            |
     tts_stop /      listen_start     |
      abort_ack          |            |
           |             v            |
           |      +-------------+     |
           |      |  LISTENING  |     |
           |      +-------------+     |
           |             |            |
           |        listen_stop       |
           |             v            |
           |      +-------------+     |
           |      |   THINKING  |-----+ (abort received)
           |      |  (STT + LLM)|
           |      +-------------+
           |             |
           |         tts_start
           |             v
           |      +-------------+
           +------|   SPEAKING  |-----+ (abort received)
                  |    (TTS)    |
                  +-------------+
```

### 6.5. Backward-Compatible HTTP Fallback
The Phase 1 HTTP endpoints (`/api/device/voice`, `/api/device/heartbeat`, `/api/device/config`) remain fully supported. Devices can operate in HTTP polling mode or WebSocket streaming mode according to firmware capability.

---

## 7. Phase 3 Protocol Extensions: Real-Time Alerts, Tools, Display & Management

### 7.1. OLED Display Events: `display` (Server -> Device)
Dispatched whenever the backend executes a tool or changes the UI state that requires visual feedback on the SSD1306 128x64 screen.

```json
{
  "type": "display",
  "screen": "weather",
  "data": {
    "city": "Dhaka",
    "temp": 26,
    "condition": "Clear sky",
    "humidity": 62
  }
}
```

Supported screens:
- `weather`: Temperature, weather condition string, city, humidity.
- `clock`: Time (24h/12h), formatted date, timezone abbreviation.
- `timer`: Active timer label, duration, remaining seconds.
- `alarm`: Alarm label, scheduled trigger time.
- `alert`: Pop-up warning or notification banner (`kind`, `label`, `text`).

### 7.2. Real-Time Alert Event: `alert` (Server -> Device)
Dispatched when a countdown timer finishes or a scheduled alarm rings. Accompanied by streaming TTS spoken audio.

```json
{
  "type": "alert",
  "kind": "timer",
  "id": "f9be95b5-dfe4-4a61-8979-40fb57944c97",
  "label": "Pasta",
  "text": "Your timer for Pasta has finished."
}
```

#### Device Acknowledgment: `alert_ack` (Device -> Server)
Sent by the device when the alert has been received and rendered on screen or audio playback started.

```json
{
  "type": "alert_ack",
  "id": "f9be95b5-dfe4-4a61-8979-40fb57944c97"
}
```

### 7.3. Secure Over-The-Air Firmware Update: `ota` (Server -> Device)
Triggers an autonomous firmware binary download and flash update on targeted devices.

```json
{
  "type": "ota",
  "version": "1.0.1",
  "url": "/api/ota/download/1.0.1/firmware.bin?device_id=AA:BB:CC:DD:EE:FF",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size": 1186557
}
```

Device Update Workflow:
1. Validates available flash partition space.
2. Streams binary chunk-by-chunk via HTTP GET using device authentication token.
3. Computes running SHA-256 digest of downloaded payload.
4. Verifies computed SHA-256 matches expected digest.
5. Writes to inactive OTA partition (`ota_0` or `ota_1`).
6. Calls `esp_ota_set_boot_partition()` and reboots upon completion.

### 7.4. Remote Hardware Actions (Server -> Device)

#### Remote Reboot: `reboot`
Instructs the ESP32 to gracefully flush LittleFS / NVS storage and invoke `esp_restart()`.

```json
{
  "type": "reboot"
}
```

#### Clear Wi-Fi Credentials: `reset_wifi`
Clears persisted Wi-Fi credentials from NVS and WiFiManager, then restarts into AP captive portal mode (`MyVoice-Setup-XXXX`).

```json
{
  "type": "reset_wifi"
}
```

### 7.5. Periodic Telemetry & Health Reporting: `status_report` (Device -> Server)
Dispatched every 30 seconds over the active WebSocket channel to report vital statistics.

```json
{
  "type": "status_report",
  "rssi": -64,
  "free_heap": 184512,
  "min_free_heap": 162100,
  "uptime_s": 8420,
  "dropped_frames": 0,
  "error_count": 0
}
```

