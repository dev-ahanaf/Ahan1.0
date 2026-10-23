# Falcon AI Known Limitations & Hardware Trade-Offs

## 1. Hardware RAM Limitations (Standard ESP32 vs ESP32-S3)

### ESP32-WROOM-32 Constraints
- The standard ESP32 Dev Board (ESP32-WROOM-32) has **320 KB internal SRAM** and **NO external PSRAM**.
- Upstream XiaoZhi server projects frequently use Opus audio encoding with 60 ms frames, requiring extensive double-buffering and dynamic heap allocations that can cause memory fragmentation or panic crashes on standard ESP32 boards without PSRAM.
- **Falcon AI Solution**: We adopted a 16 kHz 16-bit mono PCM stream over WebSocket with double-buffered 1920-byte chunks. This keeps free heap consistently above **140 KB**, ensuring zero Out-Of-Memory (OOM) crashes on standard ESP32 hardware.

---

## 2. Audio Processing: Full-Duplex AEC vs Push-to-Talk

- **Full-Duplex Acoustic Echo Cancellation (AEC)** requires high-speed DSP processing and substantial circular buffer memory (typically requiring an ESP32-S3 with 8 MB Octal PSRAM or dedicated DSP chips such as the ES7210 / ES8311).
- On standard ESP32-WROOM-32 without external DSP, full-duplex AEC leads to severe audio distortion and frame dropping.
- **Falcon AI Solution**: We implement a responsive **Push-to-Talk (PTT)** interaction flow with software barge-in. Pressing the button immediately silences speaker playback and begins microphone capture cleanly.

---

## 3. Battery Voltage Measurement

- Battery monitoring via ADC is only accurate if the hardware includes an onboard voltage divider (e.g., two 100kΩ resistors dividing battery voltage to < 3.3V connected to an ADC pin such as GPIO 34).
- If powered via 5V USB cable, the battery indicator is disabled in firmware to avoid reporting fabricated or noisy floating ADC voltages.

---

## 4. Local Wake Word vs Cloud VAD

- High-accuracy local wake word detection models (e.g., wake net) require considerable neural weights in RAM.
- Falcon AI provides manual Push-To-Talk via dual buttons (`GPIO 0` BOOT and `GPIO 27`), as well as server-side energy-based Voice Activity Detection (VAD) once triggered.
