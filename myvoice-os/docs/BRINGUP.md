# MyVoice OS - Hardware Bring-Up and Validation Guide

Target Hardware: ESP32 DevKit V1 / ESP32-WROOM-32 (Standard ESP32, No PSRAM)
Firmware Version: 1.0.0-rc1 (Release Candidate 1)
Validation Status: UNVERIFIED (Awaiting Physical Workbench Testing)

---

## 1. Hardware Pinout and Interconnect Table

Ensure all electrical connections strictly follow the wiring specifications below before applying power. **Never feed 5V into the 3V3 rail or ESP32 GPIO pins.**

| Peripheral | Module Pin | ESP32 GPIO | Voltage Domain | Wiring Notes |
|---|---|---|---|---|
| **INMP441 Mic** | VDD | 3V3 | 3.3V Only | Do NOT connect to 5V. Sensitive MEMS element. |
| **INMP441 Mic** | GND | GND | Common GND | Solid ground connection to prevent audio buzz. |
| **INMP441 Mic** | SD / DOUT | GPIO 33 | 3.3V Logic | Serial audio data output from microphone. |
| **INMP441 Mic** | WS / LRCL | GPIO 25 | 3.3V Logic | Word select / left-right clock. |
| **INMP441 Mic** | SCK / BCLK | GPIO 26 | 3.3V Logic | Bit clock for I2S0. |
| **INMP441 Mic** | L/R | GND | Ground | Strapped to GND to select Left audio channel. |
| **MAX98357A Amp** | VIN | VIN / 5V | 5.0V Supply | Connect to board 5V / VIN (or clean 3.7V - 5.5V). |
| **MAX98357A Amp** | GND | GND | Common GND | Tie to common ground. |
| **MAX98357A Amp** | DIN | GPIO 22 | 3.3V Logic | Audio data in for I2S1. |
| **MAX98357A Amp** | BCLK | GPIO 14 | 3.3V Logic | Bit clock for I2S1. |
| **MAX98357A Amp** | LRC / WS | GPIO 13 | 3.3V Logic | Left/Right word select for I2S1. |
| **MAX98357A Amp** | GAIN | Unconnected | Default 9dB | Floating gives +9dB gain. Tie to GND for +3dB. |
| **MAX98357A Amp** | SD_MODE | Unconnected | Active | Leave floating or pull up to VIN through 100k. |
| **Speaker** | + / - | Amp +/- | Differential | 4-8 Ohm, 2-3W speaker. Do NOT short to GND! |
| **SSD1306 OLED** | VCC | 3V3 | 3.3V Supply | 0.96-inch monochrome I2C display (128x64). |
| **SSD1306 OLED** | GND | GND | Common GND | Ground rail. |
| **SSD1306 OLED** | SCL | GPIO 19 | 3.3V Logic | I2C Clock line. |
| **SSD1306 OLED** | SDA | GPIO 18 | 3.3V Logic | I2C Data line. |
| **Tactile Button** | Contact 1 | GPIO 27 | 3.3V Logic | Active LOW with internal pull-up enabled. |
| **Tactile Button** | Contact 2 | GND | Common GND | Closes to ground when pressed. |

---

## 2. Power Supply and Decoupling Recommendations

1. USB Power Limits: Standard PC USB ports often limit current to 500 mA. The ESP32 with active Wi-Fi transmit bursts requires up to 260 mA peak, and the MAX98357A driving an 8-ohm speaker can draw up to 400 mA peak.
2. Brownout Prevention: If your board resets unexpectedly during audio playback or Wi-Fi association:
   - Place a 470uF or 1000uF electrolytic capacitor across the 5V and GND rail near the amplifier.
   - Use a powered USB hub or dedicated 5V 2A USB power adapter.

---

## 3. Step-by-Step Hardware Validation Procedure

### Step 1: Visual and Multimeter Continuity Check
- With power disconnected, verify that 3V3 and GND are not shorted (measure resistance > 10k ohms).
- Verify that INMP441 VDD is wired to 3V3 and NOT 5V.
- Verify speaker terminals are connected only to the amplifier differential terminals.

### Step 2: Boot-Time Hardware Diagnostics Mode
To enter the built-in diagnostic test suite:
1. Hold down the tactile button (GPIO 27).
2. Connect USB to PC or press the ESP32 EN (Reset) button while holding the button.
3. Open PlatformIO Serial Monitor at 115200 baud:
   ```bash
   pio device monitor -b 115200
   ```
4. Observe the automated diagnostics test outputs.

### Expected Serial Diagnostics Output:
```text
=========================================
  MYVOICE OS - HARDWARE DIAGNOSTICS SUITE
=========================================

[1/7] Memory: Free Heap=284512 B, Min Free=278100 B, Flash Storage=24576/1441792 B
[2/7] Button (GPIO 27): DETECTED (LOW) (Expected: Pressed/LOW)
[3/7] Scanning I2C bus (SDA=18, SCL=19)...
  - I2C device detected at 0x3C
  OLED SSD1306 Status: PASSED
[4/7] Testing INMP441 Microphone sampling...
  Mic Noise Floor / Signal RMS: 145.20 (Normal silent range: 50-800)
[5/7] Testing MAX98357A Speaker tone (440 Hz for 400ms)...
  Speaker tone playback completed
[6/7] Scanning Wi-Fi networks...
  Found 4 Wi-Fi networks nearby
    - Home_Network (-48 dBm)
    - Studio_5G (-62 dBm)
[7/7] Identity: MAC=AA:BB:CC:DD:EE:11, FW Version=0.1.0

[Diagnostics Completed] Release button and reboot to enter normal mode.
```

### Visual OLED Verification:
The OLED should light up and display:
```text
---------------------
    HARDWARE DIAG    
---------------------
Heap:277k Mic:145
OLED:OK   Spk:OK
MAC:CC:DD:EE:11
```

---

## 4. Normal Boot and Device Provisioning Sequence

1. Release the button and power cycle the board.
2. The OLED displays: `Wi-Fi Setup / SSID: MyVoice-Setup`.
3. Connect your phone or laptop to the temporary Wi-Fi network `MyVoice-Setup` using the password defined in `secrets.h` (`PROVISIONING_AP_PASSWORD`).
4. The captive portal will open. Select your 2.4 GHz home Wi-Fi SSID, enter its password, and click Save.
5. The ESP32 joins your LAN and contacts the server backend.
6. The OLED transitions to `PAIRING CODE` displaying a large 6-digit code (e.g. `849201`).
7. Open the Web Dashboard at `http://<SERVER-LAN-IP>:8000`, enter the pairing code, and click "Pair Device".
8. The OLED updates to `IDLE CLOCK` showing synced time and date.

---

## 5. Troubleshooting Matrix

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| OLED remains dark | SCL/SDA swapped or wrong address | Check GPIO 18 (SDA) and GPIO 19 (SCL). Confirm I2C address is 0x3C or 0x3D. |
| Continuous ESP32 Brownout Reset | Peak current exceeded | Add 470uF electrolytic capacitor on 5V/VIN rail. Use a 2A power brick. |
| Mic RMS is 0 or all zeros | Mic wiring or power issue | Verify INMP441 VDD is on 3V3, L/R is on GND. Check GPIO 25, 26, 33 connections. |
| Speaker emits loud noise / buzz | Floating ground or bad power | Connect common GND between ESP32 and MAX98357A. Lower volume via dashboard. |
| Pairing code expired | Timed out after 10 minutes | Wait 5 seconds; firmware will automatically poll and display a renewed code. |
| WebSocket connection fails | Invalid token or server IP | Check server URL in dashboard. Verify token hash in database. |
| Audio playback stutter / underrun | Network latency or jitter | Ensure solid 2.4 GHz Wi-Fi signal. Increase server sentence chunk buffer if needed. |

---

## 6. Phase 2 Real-Time WebSocket Voice Bring-Up

### Architecture Overview
Phase 2 activates low-latency bidirectional voice streaming over `/ws/device`. When the device button (GPIO 27) is pressed:
1. Microphone PCM samples are captured at 16 kHz 16-bit mono.
2. 60 ms frames (1,920 bytes) stream over WebSocket to `/ws/device`.
3. When the button is released, the client sends `listen_stop`.
4. The server transcribes speech, streams LLM completion tokens, chunks text into clauses, synthesizes TTS speech chunks, and returns binary audio to the ESP32.
5. The ESP32 streams received audio directly into the MAX98357A I2S DAC.
6. Pressing the button while the assistant is speaking immediately transmits `abort`, stops speaker playback, clears buffers, and transitions to `LISTENING`.

### Protocol Fallback
- WebSocket is the default real-time protocol.
- If WebSocket connection fails, the device falls back to Phase 1 HTTP push-to-talk (`/api/device/voice`).

---

## 7. Physical Hardware Testing Checklist

Status: **UNVERIFIED (Bench Specification Ready)**
Note: In accordance with project safety guidelines, physical hardware behaviors below are marked UNVERIFIED until verified on physical bench hardware.

| Test Item | Verification Method | Status | Notes |
|---|---|---|---|
| I2S0 Mic Sampling (INMP441) | Boot diagnostics mic RMS check | UNVERIFIED | Expected RMS 50-800 under quiet ambient conditions. |
| I2S1 Speaker Output (MAX98357A) | 440 Hz test tone during diagnostics | UNVERIFIED | Clear tone without clipping or brownout. |
| OLED Display States | Observe LISTENING, THINKING, SPEAKING | UNVERIFIED | SSD1306 updates immediately on WebSocket events. |
| Button Push-to-Talk (GPIO 27) | Press and hold to speak | UNVERIFIED | Streams PCM frames until button release. |
| Button Barge-In Interruption | Press button during speech playback | UNVERIFIED | Must immediately halt speaker DMA and send abort frame. |
| Free Heap During Streaming | Serial monitor free heap logging | UNVERIFIED | Must maintain > 150 KB free SRAM (no heap leaks). |
| Automatic HTTP Fallback | Disconnect WebSocket / test fallback | UNVERIFIED | Falls back to HTTP push-to-talk if WS unavailable. |

---

## 8. Simulator Testing (Automated Verification)

Use `tools/simulator.py` to test the full WebSocket pipeline before flashing physical devices:

```bash
# 1. Run live WebSocket voice cycle with synthetic audio
python3 tools/simulator.py --protocol ws --action ws-cycle --server http://127.0.0.1:8000

# 2. Test button barge-in abort handling
python3 tools/simulator.py --protocol ws --action ws-cycle --abort-test --server http://127.0.0.1:8000

# 3. Stream a local WAV file to the AI assistant
python3 tools/simulator.py --protocol ws --action ws-voice --wav input.wav --server http://127.0.0.1:8000
```

