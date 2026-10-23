# Falcon AI OTA Firmware Update System

## 1. Overview

Falcon AI implements a complete Over-The-Air (OTA) update lifecycle:
1. **Binary Compilation**: Build firmware using PlatformIO or Arduino IDE.
2. **Release Registration & Artifact Storage**: Upload binary to Falcon AI Console (`/api/admin/ota/upload`), which calculates SHA-256 and records file size.
3. **Hardware Compatibility Checks**: Matches target hardware (`esp32dev`) and version eligibility.
4. **Broadcast / Targeted Deployment**: Pushes an `ota` event over active WebSocket sessions to devices.
5. **Fail-Safe Flashing**: ESP32 downloads binary in chunks into the secondary partition (`ota_1`), computes the running SHA-256 hash, verifies the checksum, and triggers a clean restart into the new slot.

---

## 2. Packaging & Publishing a Firmware Release

### Step 1: Compile Firmware
```bash
cd myvoice-os/firmware
pio run -e esp32dev
```
Binary output: `.pio/build/esp32dev/firmware.bin`

### Step 2: Upload to Falcon AI Catalog
Via Falcon AI Console:
1. Navigate to **Firmware & OTA**.
2. Click **Upload New Release**.
3. Select `.pio/build/esp32dev/firmware.bin`.
4. Enter Version (e.g., `1.2.0-falcon`).
5. Enter Release Notes.
6. Click **Upload Firmware**.

Or via curl CLI:
```bash
curl -u admin:<YOUR_PASSWORD> -X POST http://localhost:8000/api/admin/ota/upload \
  -F "version=1.2.0-falcon" \
  -F "target_hardware=esp32dev" \
  -F "release_notes=Falcon AI Boot Splash, dual button PTT, LittleFS pairing" \
  -F "file=@.pio/build/esp32dev/firmware.bin"
```

---

## 3. Triggering OTA Updates

1. In **Firmware & OTA**, locate your release in the catalog.
2. Select target: `ALL CONNECTED DEVICES` or a specific Device ID.
3. Click **Deploy Release**.
4. Active devices receive the real-time OTA frame:
   ```json
   {
     "type": "ota",
     "version": "1.2.0-falcon",
     "url": "/api/admin/ota/download/1.2.0-falcon",
     "sha256": "4f2a...",
     "size": 1186617
   }
   ```
5. The OLED switches to `OTA Updating` with progress percentage.
6. On success, the ESP32 switches boot partitions and reboots into the updated firmware!
