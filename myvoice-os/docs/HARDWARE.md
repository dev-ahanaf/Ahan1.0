# MyVoice OS - Hardware Reference & Bring-Up Guide (v1.0.0-rc1)

## Hardware Verification Status: UNVERIFIED (Awaiting Physical Workbench Testing)
All firmware code and memory constraints are strictly verified through automated unit tests, PlatformIO build validation, and socket protocol simulation. Physical acoustic testing on actual silicon is pending bench assembly.

---

## 1. Supported Hardware & Components

MyVoice OS is designed to run on low-cost, readily available hardware components:

| Component | Part / Model | Interface | Operating Voltage | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Microcontroller | ESP32-WROOM-32 (30-pin or 38-pin DevKit) | Internal | 3.3V / 5V USB | Xtensa Dual-Core 240 MHz, 320 KB SRAM, 4 MB Flash |
| Microphone | INMP441 Omnidirectional Digital Mic | I2S (I2S_NUM_0) | 3.3V | 24-bit high-precision I2S MEMS microphone |
| Audio DAC / Amp | MAX98357A Class D Amplifier | I2S (I2S_NUM_0 shared/duplex) | 5V (or 3.3V) | 3.2W mono Class D amplifier with integrated DAC |
| Speaker | 4 Ohm or 8 Ohm / 3W Speaker | Analog Out | N/A | Wired to MAX98357A screw terminals |
| Display | 0.96 inch SSD1306 OLED (128x64) | I2C (Wire) | 3.3V | I2C address 0x3C |
| Input Button | Momentary Push Button (Normally Open) | GPIO with pull-up | 3.3V Logic | Push-to-Talk and Wake trigger |

---

## 2. Complete Wiring & Pinout Reference

### 2.1. INMP441 I2S Digital Microphone Wiring
| INMP441 Pin | ESP32 Pin | Function | Notes |
| :--- | :--- | :--- | :--- |
| VDD | 3V3 | Power Supply | 3.3V regulated power rail |
| GND | GND | Ground | Connect to shared ground plane |
| SD | GPIO 32 | I2S Serial Data In | Data stream from microphone |
| WS | GPIO 25 | I2S Word Select (LRCLK) | Audio word synchronization clock |
| SCK | GPIO 33 | I2S Continuous Clock (BCLK) | Bit clock |
| L/R | GND | Channel Select | Tie to GND for Left channel audio |

### 2.2. MAX98357A I2S Class D Amplifier Wiring
| MAX98357A Pin | ESP32 Pin | Function | Notes |
| :--- | :--- | :--- | :--- |
| VIN | 5V / VIN | Power Supply | 5V recommended for 3W output; 3.3V yields lower volume |
| GND | GND | Ground | Connect to shared ground plane |
| DIN | GPIO 26 | I2S Serial Data Out | Data stream from ESP32 to speaker |
| BCLK | GPIO 27 | I2S Bit Clock | Bit clock for speaker audio |
| LRC | GPIO 14 | I2S Left/Right Clock (WS) | Word clock for speaker audio |
| GAIN | GND | Gain Control | Tie to GND for 9dB gain (or floating for 12dB) |
| SD_MODE | Floating | Shutdown / Channel | Floating averages left and right stereo channels |

### 2.3. SSD1306 128x64 OLED Display Wiring
| SSD1306 Pin | ESP32 Pin | Function | Notes |
| :--- | :--- | :--- | :--- |
| VCC | 3V3 | Power Supply | 3.3V logic rail |
| GND | GND | Ground | Common system ground |
| SCL | GPIO 22 | I2C Clock | Standard hardware I2C clock |
| SDA | GPIO 21 | I2C Data | Standard hardware I2C data |

### 2.4. Push Button Wiring
| Button Terminal | ESP32 Pin | Function | Notes |
| :--- | :--- | :--- | :--- |
| Terminal 1 | GPIO 0 (or GPIO 4) | Input Pin | Firmware uses internal pull-up (`INPUT_PULLUP`) |
| Terminal 2 | GND | Ground | Pressing button pulls GPIO pin to LOW |

---

## 3. Power, Grounding, and Audio Decoupling Best Practices

1. Shared Ground: All components (ESP32, INMP441, MAX98357A, SSD1306) must share a common ground reference. Ground loops cause audible hum.
2. Power Decoupling:
   - Place a 100uF to 220uF electrolytic capacitor across the 5V and GND power pins of the MAX98357A amplifier. This eliminates audio distortion and prevents ESP32 brownout during high-volume playback.
   - Place a 0.1uF ceramic capacitor close to the INMP441 VDD/GND pins to filter high-frequency Wi-Fi transmission ripples.
3. Wi-Fi Power Requirements: ESP32 Wi-Fi bursts draw transient currents up to 450 mA. Ensure the USB power supply provides at least 5V / 1.5A to avoid spontaneous resets.

---

## 4. Memory Budget on ESP32-WROOM-32 (No PSRAM)

Standard ESP32-WROOM-32 contains 520 KB of internal SRAM, of which approximately 320 KB is usable by user applications after reserving memory for the FreeRTOS kernel and network stacks.

### 4.1. Memory Allocation Breakdown
| Subsystem | RAM Allocated | Lifetime | Purpose |
| :--- | :--- | :--- | :--- |
| FreeRTOS & Wi-Fi Stack | ~110 KB | Static | TCP/IP stack, WPA2 supplicant, event queues |
| I2S DMA Buffers | ~16 KB | Static | 8 buffers x 1024 bytes for zero-drop audio transfers |
| SSD1306 Display Buffer | 1 KB | Static | 128 x 64 pixels / 8 bits per byte = 1024 bytes monochrome buffer |
| WebSocket & TLS Buffers | ~35 KB | Dynamic | Frame buffering, TLS handshake, and JSON messages |
| Audio Ring Buffer | ~24 KB | Dynamic | PCM16 streaming frame queue |
| Free Heap Reserve | >= 140 KB | Dynamic | Unfragmented memory head-room for continuous operation |

Current compiled firmware metrics:
- Total RAM Used: 53,884 bytes (16.4% of 327,680 bytes).
- Flash Used: 1,186,557 bytes (90.5% of standard 1.3 MB partition).

---

## 5. Wake-Word Feasibility Study: ESP32 vs ESP32-S3

### 5.1. Technical Analysis: Wake-Word on Standard ESP32-WROOM-32
Running an on-device machine learning wake-word model (such as Espressif ESP-SR `WakeNet` or `MicroWakeWord`) on standard ESP32-WROOM-32 has severe technical constraints:
1. Memory Requirements:
   - ESP-SR WakeNet requires a minimum of 400 KB to 1.5 MB of RAM to load neural network weights and acoustic model feature extraction buffers. Standard ESP32 has only 320 KB total SRAM.
   - While quantized models (e.g., TFLite Micro WakeNet 16-bit or 8-bit) can squeeze into ~180 KB, running this concurrently with active Wi-Fi, TLS encryption, and WebSocket streaming leads to heap starvation, memory fragmentation, and spontaneous out-of-memory kernel panics.
2. Compute and Core Utilization:
   - The dual Xtensa LX6 cores lack SIMD (Single Instruction Multiple Data) or vector instructions. Calculating Mel-frequency cepstral coefficients (MFCC) and matrix multiplications continuously consumes 70% to 90% of a core at 240 MHz, leaving insufficient bandwidth for real-time I2S DMA servicing.
3. False Trigger Rates:
   - In noisy acoustic environments without digital noise suppression, lightweight microcontroller wake-word models exhibit unacceptably high false trigger rates (1 to 3 false triggers per hour).

### 5.2. Chosen Production Solution: Hardware Push-to-Talk + Energy VAD
MyVoice OS intentionally adopts a bulletproof, responsive approach for standard ESP32:
- Physical Push-to-Talk Button: Instant wake with zero CPU overhead, zero false activations, and complete user privacy.
- Lightweight Energy VAD: An algorithm running on the server or optionally on the device using basic amplitude thresholds to detect the end of speech without heavy neural network overhead.
- Total RAM overhead: Under 2 KB. Minimum free heap remains rock-solid above 170 KB.

### 5.3. ESP32-S3 Upgrade Roadmap
For users demanding hands-free on-device wake words ("Hey MyVoice" or "XiaoZhi"), MyVoice OS specifies an official upgrade path to the **ESP32-S3-WROOM-1**:
- Dual-Core Xtensa LX7 at 240 MHz with dedicated Vector Instructions (SIMD) for accelerating neural network matrix multiplications.
- 8 MB Octal PSRAM providing abundant memory for full ESP-SR WakeNet9 models.
- Hardware acoustic echo cancellation (AEC) and beamforming support.
- The MyVoice OS WebSocket protocol and server architecture remain 100% identical and compatible between ESP32 and ESP32-S3.
