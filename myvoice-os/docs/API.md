# MyVoice OS - REST & WebSocket API Reference (v1.0.0-rc1)

## 1. Authentication Schemas

| Scheme | Description | Target Endpoints |
| :--- | :--- | :--- |
| `X-Enrollment-Key` | Shared secret header for initial unprovisioned bootstrap | `/api/device/bootstrap` |
| `X-Device-Token` | Per-device token issued at bootstrap, stored as SHA-256 hash | `/api/device/heartbeat`, `/api/device/config`, `/api/device/voice` |
| HTTP Basic Auth | `admin:<ADMIN_PASSWORD>` base64-encoded in `Authorization` header | All `/api/admin/*` endpoints |
| WebSocket Query Auth | `?device_id=MAC&token=TOKEN` validated during WebSocket handshake | `/ws/device` |

---

## 2. Health & Status Endpoints

### `GET /api/health`
Public health status check.
- Auth: None
- Response (200 OK):
```json
{
  "status": "ok",
  "service": "MyVoice OS",
  "version": "1.0.0-rc1"
}
```

---

## 3. Device Provisioning & Pairing Endpoints

### `POST /api/device/bootstrap`
Initial device registration. Returns single-use pairing code.
- Auth: Header `X-Enrollment-Key`
- Request:
```json
{
  "device_id": "AA:BB:CC:DD:EE:FF",
  "firmware": "1.0.0"
}
```
- Response (200 OK):
```json
{
  "token": "32-byte-secret-token",
  "pair_code": "123456",
  "expires_in": 600,
  "config_version": 1
}
```

### `GET /api/device/status`
Device polls whether it has been claimed by the administrator.
- Auth: Headers `X-Device-Id`, `X-Device-Token`
- Response (200 OK):
```json
{
  "paired": true,
  "name": "Living Room Assistant",
  "config_version": 2
}
```

### `POST /api/admin/claim`
Admin claims a pending device using the 6-digit numeric code.
- Auth: HTTP Basic Auth (`admin`)
- Request:
```json
{
  "code": "123456",
  "name": "Living Room Assistant"
}
```
- Response (200 OK):
```json
{
  "status": "paired",
  "device_id": "AA:BB:CC:DD:EE:FF",
  "name": "Living Room Assistant"
}
```

---

## 4. Device Runtime & HTTP Fallback Endpoints

### `POST /api/device/heartbeat`
Periodic 30-second ping indicating device vitality and current state.
- Auth: Headers `X-Device-Id`, `X-Device-Token`
- Request:
```json
{
  "free_heap": 182400,
  "rssi": -65,
  "uptime": 3600
}
```
- Response (200 OK):
```json
{
  "status": "ok",
  "server_time_utc": "2026-10-19T17:00:00Z",
  "config_version": 2
}
```

### `GET /api/device/config`
Retrieves device configuration when `config_version` increments.
- Auth: Headers `X-Device-Id`, `X-Device-Token`
- Response (200 OK):
```json
{
  "name": "Living Room Assistant",
  "timezone": "Asia/Dhaka",
  "language": "en",
  "speaker_volume": 85,
  "mic_gain": 50,
  "oled_brightness": 128,
  "idle_display_mode": "clock",
  "clock_format": "24h",
  "config_version": 2
}
```

### `POST /api/device/voice`
Push-to-talk HTTP fallback endpoint. Streams WAV recording and receives synthesized WAV response.
- Auth: Headers `X-Device-Id`, `X-Device-Token`
- Request Body: `audio/wav` binary payload
- Response Body: `audio/wav` streaming synthesized speech

---

## 5. Fleet & Hardware Management Endpoints

### `POST /api/admin/devices/{id}/reboot`
Dispatches remote reboot instruction to active device.
- Auth: HTTP Basic Auth
- Response (200 OK):
```json
{
  "status": "success",
  "action": "reboot",
  "device_id": "AA:BB:CC:DD:EE:FF",
  "dispatched": true
}
```

### `POST /api/admin/devices/{id}/reset-wifi`
Dispatches Wi-Fi credential reset and restarts device into captive portal.
- Auth: HTTP Basic Auth
- Response (200 OK):
```json
{
  "status": "success",
  "action": "reset_wifi",
  "device_id": "AA:BB:CC:DD:EE:FF",
  "dispatched": true
}
```

### `POST /api/admin/devices/{id}/revoke`
Revokes device token and permanently closes active sessions.
- Auth: HTTP Basic Auth
- Response (200 OK):
```json
{
  "status": "success",
  "device_id": "AA:BB:CC:DD:EE:FF",
  "revoked": true
}
```

### `GET /api/admin/devices/{id}/telemetry`
Retrieves the 50 most recent telemetry records for a device.
- Auth: HTTP Basic Auth
- Response (200 OK):
```json
{
  "telemetry": [
    {
      "id": "uuid",
      "device_id": "AA:BB:CC:DD:EE:FF",
      "rssi": -62,
      "free_heap": 184500,
      "min_free_heap": 162000,
      "uptime_s": 7200,
      "dropped_frames": 0,
      "error_count": 0,
      "created_at": "2026-10-19T17:00:00Z"
    }
  ]
}
```

---

## 6. AI Tools & Skills Endpoints

### `GET /api/admin/tools`
Lists all discovered tools in the system registry.
- Auth: HTTP Basic Auth
- Response (200 OK):
```json
{
  "tools": [
    {"name": "get_current_time", "permission_key": "clock", "description": "...", "parameters": {...}},
    {"name": "get_weather", "permission_key": "weather", "description": "...", "parameters": {...}},
    {"name": "web_search", "permission_key": "search", "description": "...", "parameters": {...}},
    {"name": "manage_timer", "permission_key": "timer", "description": "...", "parameters": {...}},
    {"name": "manage_alarm", "permission_key": "alarm", "description": "...", "parameters": {...}},
    {"name": "device_settings", "permission_key": "device_settings", "description": "...", "parameters": {...}}
  ]
}
```

### `POST /api/admin/tools/test`
Executes a tool in isolation for testing and debugging.
- Auth: HTTP Basic Auth
- Request:
```json
{
  "tool_name": "get_weather",
  "device_id": "AA:BB:CC:DD:EE:FF",
  "args": {"city": "Dhaka"}
}
```
- Response (200 OK):
```json
{
  "success": true,
  "data": {"temperature_c": 26.0, "condition": "Clear sky"},
  "voice_summary": "In Dhaka, it is currently 26.0 degrees Celsius and clear sky.",
  "display_data": {"screen": "weather", "city": "Dhaka", "temp": 26}
}
```

### `POST /api/admin/devices/{id}/tools`
Configures enabled tool whitelist for a device.
- Auth: HTTP Basic Auth
- Request:
```json
{
  "tools_enabled": ["clock", "weather", "timer", "alarm"]
}
```
- Response (200 OK):
```json
{
  "status": "success",
  "tools_enabled": "clock,weather,timer,alarm"
}
```

---

## 7. Timers & Alarms Management Endpoints

### `GET /api/admin/timers`
Lists active and completed countdown timers.
- Auth: HTTP Basic Auth

### `DELETE /api/admin/timers/{id}`
Cancels an active timer.
- Auth: HTTP Basic Auth

### `GET /api/admin/alarms`
Lists scheduled alarms.
- Auth: HTTP Basic Auth

### `POST /api/admin/alarms`
Creates a new scheduled alarm for a device.
- Auth: HTTP Basic Auth
- Request:
```json
{
  "device_id": "AA:BB:CC:DD:EE:FF",
  "time_str": "07:30",
  "label": "Morning Wakeup"
}
```

### `DELETE /api/admin/alarms/{id}`
Cancels a scheduled alarm.
- Auth: HTTP Basic Auth

---

## 8. OTA Firmware Update Endpoints

### `POST /api/admin/ota/upload`
Uploads compiled ESP32 firmware binary (validates 0xE9 header and size).
- Auth: HTTP Basic Auth
- Form Fields: `file` (binary), `version` (string), `target_hardware` (string), `release_notes` (string)

### `GET /api/admin/ota/releases`
Lists all uploaded firmware releases with SHA-256 digests.
- Auth: HTTP Basic Auth

### `POST /api/admin/ota/deploy`
Triggers OTA update command to targeted devices over WebSocket.
- Auth: HTTP Basic Auth
- Request:
```json
{
  "version": "1.0.1",
  "target_device": "AA:BB:CC:DD:EE:FF"
}
```

### `GET /api/ota/download/{version}/{filename}`
Protected binary download endpoint validating device authorization.
- Auth: Header `X-Device-Token` or query `token=...`
- Returns: `application/octet-stream` with headers `X-Firmware-SHA256` and `X-Firmware-Size`

---

## 9. Audit Logs Endpoint

### `GET /api/admin/audit-logs`
Retrieves administrative audit logs with IP addresses and actions.
- Auth: HTTP Basic Auth
- Response (200 OK):
```json
{
  "audit_logs": [
    {
      "id": "uuid",
      "user": "admin",
      "action": "reboot_device",
      "target": "AA:BB:CC:DD:EE:FF",
      "ip_address": "127.0.0.1",
      "created_at": "2026-10-19T17:00:00Z"
    }
  ]
}
```
