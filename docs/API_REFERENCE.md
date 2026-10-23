# Falcon AI API & Protocol Reference

## 1. Authentication

### Administrative REST APIs
- All `/api/admin/*` routes require **HTTP Basic Auth**:
  - `Username`: `admin`
  - `Password`: configured via `ADMIN_PASSWORD` (default: `12345678`)

### Device Bootstrap & Heartbeat
- `POST /api/device/bootstrap`: Requires header `X-Enrollment-Key: <ENROLLMENT_KEY>`
- `GET /api/device/status`, `POST /api/device/heartbeat`, `GET /api/device/config`:
  - Require headers:
    - `X-Device-ID: <MAC_ADDRESS>`
    - `X-Device-Token: <SECRET_TOKEN>`

### WebSocket Device Streaming
- Endpoint: `/ws/device?device_id=<MAC>&token=<TOKEN>`

---

## 2. Core REST Endpoints

### AI Agents Studio (`/api/admin/agents`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/agents` | List all AI agent personas with device counts |
| `POST` | `/api/admin/agents` | Create a new AI agent persona |
| `GET` | `/api/admin/agents/{id}` | Get agent details and assigned devices |
| `PUT` | `/api/admin/agents/{id}` | Update agent persona, prompt, voice, model |
| `DELETE` | `/api/admin/agents/{id}` | Delete an agent persona |
| `POST` | `/api/admin/agents/{id}/test` | Test prompt and measure real-time latency |
| `POST` | `/api/admin/devices/{id}/assign_agent` | Assign or unassign agent to device |

### Fleet & Device Management (`/api/admin/devices`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/devices` | List registered devices with online status |
| `POST` | `/api/admin/claim` | Claim an unassigned device with 6-digit code |
| `POST` | `/api/admin/devices/{id}/settings` | Update per-device configuration |
| `POST` | `/api/admin/devices/{id}/rotate-token` | Rotate device authentication token |
| `POST` | `/api/admin/devices/{id}/revoke` | Revoke device credentials immediately |
| `POST` | `/api/admin/devices/{id}/reboot` | Send remote reboot signal to device |
| `POST` | `/api/admin/devices/{id}/reset_wifi` | Send clear Wi-Fi command to device |
| `GET` | `/api/admin/devices/{id}/telemetry` | Get historical telemetry (RSSI, free heap) |

### Firmware & OTA Updates (`/api/admin/ota`)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/ota/releases` | List registered firmware releases |
| `POST` | `/api/admin/ota/upload` | Upload `.bin` firmware artifact |
| `POST` | `/api/admin/ota/deploy` | Broadcast OTA update to active devices |
| `GET` | `/api/admin/ota/download/{ver}` | Download firmware artifact binary |

---

## 3. WebSocket Protocol Specification

### Client to Server Frames
1. `{"type": "listen_start"}`: User pressed push-to-talk button.
2. Binary PCM16 audio frames (16,000 Hz, 16-bit signed, mono, little-endian).
3. `{"type": "listen_stop"}`: User released push-to-talk button.
4. `{"type": "abort"}`: User interrupted/barged-in during audio playback.
5. `{"type": "ping"}`: Keepalive heartbeat frame.
6. `{"type": "status_report", "rssi": -65, "free_heap": 142000, "uptime_s": 3600}`: Telemetry.
7. `{"type": "alert_ack", "id": "<TIMER_OR_ALARM_ID>"}`: Acknowledge alert.

### Server to Client Frames
1. `{"type": "stt", "text": "...", "final": true}`: Transcribed speech.
2. `{"type": "llm", "delta": "...", "final": false}`: Incremental token delta.
3. `{"type": "display", "screen": "weather", "data": {...}}`: OLED screen update.
4. `{"type": "tts_start", "codec": "pcm16", "sample_rate": 16000, "channels": 1}`: Audio header.
5. Binary PCM16 audio frames (16 kHz audio streamed from Edge-TTS or OpenAI).
6. `{"type": "tts_stop"}`: Audio playback completed.
7. `{"type": "ota", "version": "...", "url": "...", "sha256": "...", "size": ...}`: OTA trigger.
8. `{"type": "reboot"}` / `{"type": "reset_wifi"}`: Remote administrative commands.
