# MyVoice OS - Security Architecture & Hardening Guide (v1.0.0-rc1)

## 1. Threat Model & Security Posture

MyVoice OS is engineered for self-hosted edge IoT environments. The architecture transitions from an unprovisioned hardware bootstrap to an isolated, per-device token-authenticated model.

### Threat Vectors & Countermeasures
| Threat Vector | Attack Scenario | Implemented Countermeasure |
| :--- | :--- | :--- |
| Pairing Brute-Force | Automated attacker guessing 6-digit pairing codes | Sliding-window IP rate limiting (max 5 failed attempts per 60 seconds triggers HTTP 429). |
| Eavesdropping & Tampering | Attacker sniffing unencrypted traffic on local network | Production Caddy reverse proxy with mandatory TLS/HTTPS and WSS. |
| Stolen Hardware / Token Leak | Compromised ESP32 device attempting server access | Administrative one-click revocation (`POST /api/admin/devices/{id}/revoke`) invalidates token and drops active WebSocket sessions. |
| Malicious Firmware Flashing | Attacker uploading corrupted or arbitrary OTA binary | Mandatory SHA-256 cryptographic checksum matching, 2 MB size guards, and ESP32 `0xE9` header validation. |
| Clickjacking & MIME Sniffing | Malicious site embedding dashboard in iframe | HTTP security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`). |
| Command Injection | LLM executing arbitrary firmware shell commands | Whitelisted tool registry (`ToolRegistry`) with strict Pydantic parameter validation and per-device permission controls. |

---

## 2. Authentication & Identity Lifecycle

### 2.1. Unprovisioned Bootstrap
- When an ESP32 first boots, it transmits `POST /api/device/bootstrap` accompanied by `X-Enrollment-Key`.
- The enrollment key is validated in constant time. Duplicate bootstrap requests for an existing MAC address are rejected with HTTP 409 Conflict.
- The server issues a cryptographically secure 32-byte secret token and generates an ephemeral 6-digit pairing code with a 10-minute time-to-live.

### 2.2. Per-Device Cryptographic Tokens
- The server stores only the SHA-256 hash of the device token in `myvoice.db`. The plaintext token is never stored on the server.
- The ESP32 persists the token in encrypted non-volatile storage (NVS).
- All subsequent transactions (WebSocket streaming, heartbeats, configuration queries, and OTA downloads) require the per-device token.

### 2.3. Dashboard Administrative Security
- Management endpoints under `/api/admin/*` require HTTP Basic Authentication (`admin:<ADMIN_PASSWORD>`).
- Passwords are verified using constant-time comparison (`secrets.compare_digest`) to eliminate timing side-channel attacks.
- Administrative actions (device claim, reboot, Wi-Fi clear, revocation, firmware upload, and deployment) generate immutable entries in `audit_logs` capturing user, action, target, details, and client IP address.

---

## 3. Over-The-Air (OTA) Firmware Integrity

All firmware distribution operations are guarded by three validation gates:
1. Header Validation: The server inspects the first byte of uploaded binaries, requiring the ESP32 magic byte (`0xE9`). Non-ESP32 binaries are rejected with HTTP 400.
2. Size Guards: Binaries must be between 10 KB and 2 MB to prevent partition overflow or truncated uploads.
3. Cryptographic SHA-256 Hash: The server computes and stores the SHA-256 digest upon upload. When the device downloads the binary, it computes a running SHA-256 digest and verifies it against the server-provided hash before calling `esp_ota_set_boot_partition()`.

---

## 4. Production Hardening Checklist

1. Change Default Secrets:
   - Ensure `ADMIN_PASSWORD` in `server/.env` is at least 16 characters long.
   - Ensure `ENROLLMENT_KEY` in `server/.env` and `firmware/include/secrets.h` is at least 24 characters long.
2. Network Isolation: Deploy ESP32 devices on an isolated IoT VLAN separated from personal computers and storage servers.
3. TLS Enforcement: Always use HTTPS/WSS in production via the included Caddy reverse proxy (`docker-compose.yml`).
4. Physical Security: Enable ESP32 Flash Encryption and Secure Boot V2 if deploying in untrusted physical environments.
