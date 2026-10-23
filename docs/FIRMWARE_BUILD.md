# Falcon AI Firmware Build & Flashing Guide

## 1. Project Structure

Falcon AI provides two firmware development paths:

1. **PlatformIO Project (Recommended)**: Located in `myvoice-os/firmware/`
   - Complete C++ codebase with modular audio drivers, OLED state machine, captive portal Wi-Fi provisioning, WebSocket client, and OTA client.
   - Built with PlatformIO Core (`pio run -e esp32dev`).
2. **Standalone Arduino IDE Sketch**: Located in `myvoice-os/firmware/MyVoiceAssistant/`
   - Single-file sketch for quick flashing via Arduino IDE 2.x.

---

## 2. Partition Table & Memory Budget

Standard ESP32-WROOM-32 boards provide 4 MB SPI Flash and 320 KB internal SRAM.
Falcon AI uses the `default.csv` dual-app partition table:

```csv
# Name,   Type, SubType, Offset,  Size, Flags
nvs,      data, nvs,     0x9000,  0x5000,
otadata,  data, ota,     0xe000,  0x2000,
app0,     app,  ota_0,   0x10000, 0x140000,  # 1.31 MB Primary Firmware
app1,     app,  ota_1,   0x150000,0x140000,  # 1.31 MB Secondary OTA Firmware
spiffs,   data, spiffs,  0x290000,0x160000,
```

### Resource Utilization
- **Flash Memory**: 1,186,617 bytes (90.5% of 1.3 MB partition)
- **RAM Static**: 53,884 bytes (16.4% of 320 KB)
- **Runtime Free Heap**: > 140 KB during active 16 kHz streaming.

---

## 3. PlatformIO Build Instructions

### Prerequisites
- Python 3.10+
- PlatformIO Core CLI:
  ```bash
  pip install -U platformio
  ```

### Build Binary
Navigate to `myvoice-os/firmware`:
```bash
cd myvoice-os/firmware
pio run -e esp32dev
```

The compiled binary will be placed at:
`.pio/build/esp32dev/firmware.bin`

### Flash via USB Serial
Connect your ESP32 board via USB data cable and run:
```bash
pio run -e esp32dev --target upload
```

### Monitor Serial Boot Logs
```bash
pio device monitor -b 115200
```

Expected Serial Boot Log:
```text
==================================================
Falcon AI Firmware v1.2.0 (Self-Hosted Voice Assistant)
Hardware Target: ESP32-WROOM-32 (Standard Dev Board)
==================================================
[Display] SSD1306 OLED Initialized (SDA=23, SCL=18)
[Display] State: BOOTING ("FALCON AI v1.2")
[Storage] LittleFS mounted successfully.
[Audio] INMP441 Microphone Initialized (I2S0, 16kHz PCM16 Mono)
[Audio] MAX98357A Speaker Initialized (I2S1, 16kHz PCM16 Mono)
[Network] Checking saved Wi-Fi credentials...
```

---

## 4. Standalone Arduino IDE Instructions

1. Open Arduino IDE 2.x.
2. In **Board Manager**, install `esp32` by Espressif Systems (v2.0.14 or v3.0.x).
3. Select board: **ESP32 Dev Module**.
4. Configure Board Options:
   - **Flash Frequency**: 80MHz
   - **Flash Mode**: QIO / DIO
   - **Partition Scheme**: `Default (2 x 1.3MB app, 1.4MB SPIFFS)`
   - **Core Debug Level**: None / Info
5. Install Required Libraries via Library Manager:
   - `Adafruit SSD1306` & `Adafruit GFX Library`
   - `WebSockets` (by Markus Sattler)
   - `ArduinoJson` (v6.x or v7.x)
6. Open `myvoice-os/firmware/MyVoiceAssistant/MyVoiceAssistant.ino`.
7. Click **Verify / Upload**.

---

## 5. Wi-Fi Provisioning (Captive Portal)

If no Wi-Fi credentials are saved in LittleFS:
1. The OLED displays:
   `SSID: FalconAI-Setup`
   `IP: 192.168.4.1`
2. Connect your smartphone or computer to Wi-Fi network: **`FalconAI-Setup`**.
3. A captive portal page will automatically open.
4. Select your home 2.4 GHz Wi-Fi SSID, enter password, and click **Connect**.
5. Credentials are saved permanently in LittleFS. The device restarts and connects to your local network.
