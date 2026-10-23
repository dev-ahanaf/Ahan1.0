# Falcon AI Hardware Wiring & Pinout Guide

## 1. Hardware Overview

Falcon AI is optimized for the **Standard ESP32 Dev Board (ESP32-WROOM-32)** without requiring external PSRAM or custom microcontroller variants.

| Component | Specification | Interface |
|---|---|---|
| **Microcontroller** | ESP32-WROOM-32 (Dual Core 240 MHz, 320 KB SRAM, 4 MB Flash) | Core |
| **Microphone** | INMP441 Omnidirectional MEMS Microphone | I2S Rx |
| **Audio Amplifier** | MAX98357A 3.2W Class-D Mono Amplifier | I2S Tx |
| **Speaker** | 4Ω 3W or 8Ω 2W Dynamic Speaker | Analog Audio |
| **Display** | 0.96-inch Monochrome SSD1306 (128x64) | I2C |
| **PTT Input 1** | Onboard BOOT Button | GPIO 0 (Active-Low) |
| **PTT Input 2** | External Push Button (Breadboard / Enclosure) | GPIO 27 (Active-Low) |
| **Power Supply** | 5V 2A Micro-USB / Type-C or Regulated 5V Pin | Power |

---

## 2. Complete Pinout Table

### A. INMP441 I2S Microphone (Audio Input)

| INMP441 Pin | ESP32 Pin | Description |
|---|---|---|
| **VDD / VCC** | **3V3** (3.3V) | *Do NOT connect to 5V* |
| **GND** | **GND** | Common Ground |
| **SD** (Serial Data) | **GPIO 32** | I2S Data In (`I2S_MIC_DATA`) |
| **WS** (Word Select / L/R Clock) | **GPIO 25** | I2S Left/Right Clock (`I2S_MIC_WS`) |
| **SCK** (Serial Clock / BCLK) | **GPIO 33** | I2S Bit Clock (`I2S_MIC_BCLK`) |
| **L/R** (Channel Select) | **GND** | Pull to GND for Left Channel |

---

### B. MAX98357A I2S Audio Amplifier (Audio Output)

| MAX98357A Pin | ESP32 Pin | Description |
|---|---|---|
| **VIN / VDD** | **5V / VIN** | Connect to 5V rail for 3W dynamic range |
| **GND** | **GND** | Common Ground |
| **DIN** (Data In) | **GPIO 22** | I2S Data Out (`I2S_SPK_DATA`) |
| **LRC / WS** (Word Select) | **GPIO 26** | I2S Word Select (`I2S_SPK_WS`) |
| **BCLK** (Bit Clock) | **GPIO 19** | I2S Bit Clock (`I2S_SPK_BCLK`) |
| **SD_MODE** | Floating or 3V3 | Active (shutdown pin) |
| **GAIN** | Floating or GND | Default +9 dB / +12 dB |
| **SPK+ / SPK-** | Speaker Terminals | Connect to 4Ω 3W speaker |

---

### C. SSD1306 0.96" OLED Display (128x64 I2C)

| SSD1306 Pin | ESP32 Pin | Description |
|---|---|---|
| **VCC** | **3V3** (or 5V depending on module) | Logic and Display Power |
| **GND** | **GND** | Common Ground |
| **SCL** | **GPIO 18** (or GPIO 22 if software I2C) | I2C Clock (`OLED_SCL`) |
| **SDA** | **GPIO 23** (or GPIO 21 if software I2C) | I2C Data (`OLED_SDA`) |

> Default Falcon AI Firmware I2C Pin Configuration:
> - `SDA`: **GPIO 23**
> - `SCL`: **GPIO 18**
> - Address: `0x3C`

---

### D. Push-to-Talk (PTT) Dual Button Configuration

Falcon AI Firmware checks **both** buttons simultaneously so the device functions without requiring external breadboard switches:

| Button | ESP32 Pin | Mode | Purpose |
|---|---|---|---|
| **Onboard BOOT** | **GPIO 0** | `INPUT_PULLUP` | Built-in button on DevKit board; press to talk immediately |
| **External Switch** | **GPIO 27** | `INPUT_PULLUP` | External momentary push button wired between GPIO 27 & GND |

---

## 3. Power Decoupling & Noise Elimination

1. **Electrolytic Capacitor**: Place a 100 µF to 470 µF capacitor across the MAX98357A VIN and GND rails close to the amplifier to buffer instantaneous speaker current transients.
2. **Dedicated Ground**: Connect the INMP441 GND and MAX98357A GND to separate GND pins on the ESP32 if audible switching hum occurs.
3. **Short Wiring**: Keep I2S signal lines (BCLK, WS, SD) under 10 cm in length to prevent clock jitter and capacitive high-frequency attenuation.
