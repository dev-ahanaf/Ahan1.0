# Falcon AI Device Pairing & Identity Guide

## 1. Zero-Trust Pairing Architecture

Falcon AI uses an end-to-end device activation mechanism inspired by XiaoZhi, but completely self-hosted on your private infrastructure without dependencies on `xiaozhi.me`.

```
  +--------------+            +--------------------+            +-------------------+
  | ESP32 Device |            | Falcon AI Server   |            | Web Console User  |
  +--------------+            +--------------------+            +-------------------+
         |                              |                                 |
         | 1. POST /api/device/bootstrap|                                 |
         |----------------------------->|                                 |
         |                              |                                 |
         | 2. Issues Ephemeral Code     |                                 |
         |<-----------------------------|                                 |
         | (e.g. 529143, expires in 5m) |                                 |
         |                              |                                 |
         | 3. Displays Code on OLED     |                                 |
         |    "PAIR: 529143"            |                                 |
         |                              |   4. User clicks "Pair Device"  |
         |                              |      enters "529143"            |
         |                              |-------------------------------->|
         |                              |                                 |
         |                              |   5. POST /api/admin/claim      |
         |                              |   { code: "529143", name: ... } |
         |                              |<--------------------------------|
         |                              |                                 |
         |                              |   6. Validates single-use hash  |
         |                              |      Sets paired = 1            |
         |                              |-------------------------------->|
         |                              |                                 |
         | 7. Polls /status or connects |                                 |
         |    WebSocket with token      |                                 |
         |----------------------------->|                                 |
         |                              |                                 |
         | 8. Authenticated & Ready     |                                 |
         |<-----------------------------|                                 |
```

---

## 2. Security Safeguards

1. **MAC Address Alone is Not Sufficient**:
   - The device MAC address is simply an identifier (`device_id`).
   - Ownership requires knowledge of the 32-byte cryptographically secure random `token` issued during enrollment.
2. **Single-Use Ephemeral Codes**:
   - Pairing codes are 6-digit integers generated with `secrets.randbelow(1000000)`.
   - The server only stores the SHA-256 digest of the code combined with an internal HMAC `ENROLLMENT_KEY`.
   - Codes expire automatically after 300 seconds (5 minutes).
   - Once claimed, the pairing code hash is instantly nulled.
3. **Brute-Force Rate Limiting**:
   - Pairing attempts on `/api/admin/claim` are strictly rate-limited per client IP.
   - More than 5 failed attempts within 60 seconds trigger an immediate `429 Too Many Requests` lockout.
4. **Token Revocation & Rotation**:
   - Device credentials can be rotated or revoked directly from the Web Console.
   - Revoking a device instantly closes any active WebSocket connection with code `4003 (Device Revoked)` and prevents reconnection.

---

## 3. Step-by-Step Pairing Walkthrough

1. **Power Up Device**:
   Plug your ESP32 board into USB power.
2. **Wi-Fi Connection**:
   The board connects to your Wi-Fi network.
3. **Activation Screen**:
   If unauthenticated, the OLED screen will display:
   ```
   [ FALCON AI ]
   PAIR CODE:
      529 143
   Expires in 5m
   ```
4. **Sign in to Falcon AI Console**:
   Open `http://<your-server-ip>:8000/` or your custom domain in your browser.
5. **Open Pair Modal**:
   Click **Pair Device** in the top-right header or dashboard view.
6. **Enter Pairing Code**:
   Enter the 6-digit code shown on the OLED and give your device a friendly name (e.g., "Living Room Falcon").
7. **Instant Pairing**:
   The Web Console registers the device, displays it on your dashboard, and links it with your chosen AI Agent persona!
   The device OLED automatically transitions from `Activation Required` to `READY`!
