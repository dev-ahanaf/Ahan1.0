# Suggested implementation stages and acceptance checks

## Phase 1: browser + device onboarding
- Run backend, browse from a second phone/device on the local network.
- Confirm empty registry, bad admin password => 401, bad enrollment key => 401.
- Flash an ESP32, join the Wi-Fi setup portal, pair with a 6-digit code; confirm that the device appears as paired and sends heartbeats.
- Prove weather appears in serial, browser clock/weather text commands work, profile updates affect returned local time and weather location.

## Phase 2: push-to-talk proof of concept
- Connect INMP441 and MAX98357A pins per README.
- Obtain cloud API credentials, set only on the backend.
- Press GPIO27 and speak for the next 3 seconds; confirm 96,044-byte WAV uploaded and audible reply.
- If silence: check INMP441 L/R strap, BCLK/WS/SD wiring, and 32-bit shift/gain. If reply is silent: inspect MAX98357A VIN, shared GND, speaker terminals, mono/stereo I2S settings.
- Try Bangla and English; check pronunciation and transcription. Add speaker volume limiter and wake-word only after reliable audio.

## Phase 3: secure pairing and HTTPS
- Add one-time factory identity provisioning; replace `ENROLLMENT_KEY`.
- Add trust-anchor/certificate validation to firmware before using a public endpoint.
- Add unpair/reset UI plus deliberate physical confirmation, enrollment revocation and pairing rate limits.

## Phase 4: real-time conversational architecture
- Test Opus codec feasibility on board (regular ESP32 has limited memory) and WebSocket PCM/Opus frame transport.
- Make sessions event-based (wake-word, start, partial transcription, final, tool-call, cancel, TTS chunks).
- Add response interruption, latency metrics and audio buffering.

## Phase 5: tools, assistant and ecosystem
- Weather, clock, search, persisted alarms, reminders, GPIO via allowlisted function calls, MQTT/Home Assistant, optional display/UI.
- Add per-device configuration and scoped capabilities, OTA partitions & signature checks, firmware release channel, fleet dashboard.

Production schema should add `users`, `user_devices`, `device_credentials`, `device_events`, `capabilities`, `firmware_releases`; consider PostgreSQL once you go beyond a local prototype.
