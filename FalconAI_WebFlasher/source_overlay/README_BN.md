# Falcon AI — ব্যক্তিগত ESP32 Firmware (Source + Installer)

এই প্যাকেজটি **Regular ESP32 DevKit/ESP32-WROOM-32 + INMP441 + MAX98357A + SSD1306 128×64 OLED**-এর জন্য নিজের `falcon-ai-esp32` board variant যুক্ত করে। এটি তোমার আগেই clone করা `78/xiaozhi-esp32` firmware repository-এর **working voice/audio/network stack reuse** করে। তুমি নিজস্ব self-hosted XiaoZhi-compatible server-এ connect করতে পারবে।

**কী পাচ্ছ:** স্বতন্ত্র board type/firmware name, নিজের GPIO pinmap, FalconAI boot log, নিজের OTA endpoint, বিদ্যমান Opus/WebSocket/Wi-Fi/OLED/voice firmware support, এবং build/flash instructions।

**কী পাচ্ছ না:** আগে থেকেই compiled `.bin` বা real hardware-এ verified firmware। এই পরিবেশে তোমার আসল repository, ESP-IDF toolchain ও physical device উপস্থিত নেই, তাই source installer তৈরি করে unit tests চালানো হয়েছে, device build/flash হয়নি। OLED-এ custom graphics/logo এবং নতুন OTA dashboard এই প্যাকেজের scope-এর বাইরে।

## 1. Wiring: default `myvoice` profile

এটি তোমার পুরোনো **MyVoice OS** project-এর পূর্বনির্ধারিত wiring অনুসারে। **চিপে বাস্তবে যে pin যুক্ত আছে তা যাচাই করে তবে flash করবে।**

| Peripheral | Module Pin | ESP32 Pin |
|---|---|---|
| INMP441 | SCK / BCLK | GPIO26 |
| INMP441 | WS / LRCLK | GPIO25 |
| INMP441 | SD | GPIO33 |
| MAX98357A | BCLK | GPIO14 |
| MAX98357A | LRC / WS | GPIO13 |
| MAX98357A | DIN | GPIO22 |
| OLED SSD1306 | SDA | GPIO18 |
| OLED SSD1306 | SCL | GPIO19 |
| Push-to-talk | Button to GND | GPIO27 |
| Onboard BOOT | Existing onboard button | GPIO0 |

INMP441 VDD = 3.3V, GND = GND। OLED VCC সাধারণত 3.3V (module rating দেখো)। Amplifier power তার board specification অনুযায়ী regulated supply দাও; all GND common। 3.7V battery-কে সরাসরি ESP32 5V/VIN pin-এ দিয়ো না।

`--profile xiaozhi` বেছে নিলে upstream bread-compact ESP32 pinmap অনুযায়ী build হবে: mic GPIO 26/25/32, amplifier GPIO14/27/33, OLED GPIO4/15, PTT touch GPIO5। **এটা default `myvoice` থেকে আলাদা।**

Push-to-talk: GPIO27 button চেপে ধরে বলো, ছেড়ে দিলে listening বন্ধ হবে। Onboard BOOT GPIO0-এ upstream click-to-toggle behavior থাকবে।

## 2. Requirements

- Clone করা `xiaozhi-esp32` repository, এই প্যাকেজটি তার বাইরে রাখবে।
- Python 3.10+।
- Installed and activated ESP-IDF matching your checked-out upstream revision (current upstream uses ESP-IDF 6.0.1+ / often 6.1).
- Self-hosted XiaoZhi-compatible server with reachable OTA + WebSocket endpoints.
- Actual flash size check (common DevKit 4MB, কিন্তু নিশ্চিত হও)।

**Server address example** (real computer LAN IP বসাতে হবে):

OTA: `http://192.168.1.100:8002/xiaozhi/ota/`

WebSocket: `ws://192.168.1.100:8000/xiaozhi/v1/`

`localhost`/`127.0.0.1` দেবে না, ESP32 থেকে তোমার computer-এ পৌঁছাতে হবে। Self-hosted server-এর `server.websocket` এবং `server.ota` configuration-ও ঠিক করতে হবে। Server অনুযায়ী OTA port আলাদা হতে পারে—config দেখে যাচাই করো।

## 3. Install custom firmware files

ZIP extract করো। Terminal-এ ZIP extracted folder থেকে:

```bash
python3 apply_falcon.py --repo ../xiaozhi-esp32 \
  --profile myvoice --flash-size 4MB \
  --ota-url http://192.168.1.100:8002/xiaozhi/ota/ \
  --dry-run
```

উপরের OTA IP **তোমার নিজের LAN IP দিয়ে বদলে** নাও। `--dry-run` দেখাবে কী হবে; তারপর `--dry-run` বাদ দিয়ে apply করো:

```bash
python3 apply_falcon.py --repo ../xiaozhi-esp32 \
  --profile myvoice --flash-size 4MB \
  --ota-url http://192.168.1.100:8002/xiaozhi/ota/
```

এই script `main/boards/falcon-ai-esp32/` নতুন করে বানাবে, `main/Kconfig.projbuild` এবং `main/CMakeLists.txt`-এ board register করবে। পুরনো board directory, other custom code, `.env` ও Git history অক্ষত থাকবে। Shared দুটি ফাইলের backup `.falcon-backups/` folder-এ রাখা হবে। একই custom folder আগে থাকলে **stop** করবে, overwrite করবে না।

## 4. Build

ESP-IDF environment active করে firmware repo-তে যাও:

```bash
cd ../xiaozhi-esp32
python scripts/build.py falcon-ai-esp32 --language en-US --wake-word disabled
```

Alternatively:

```bash
idf.py set-target esp32
idf.py menuconfig
# Xiaozhi Assistant > Target Board > Falcon AI - Personal ESP32 DevKit
# OLED type: SSD1306 128x64
# Verify OTA URL / partition table / flash size
idf.py build
```

Firmware output normally `build/`-এ থাকে; successful build হলে `build/merged-binary.bin` পাওয়া যেতে পারে। Build script supports `--zip` on compatible upstream versions.

**4MB important:** selected `partitions/v2/4m.csv` has factory partition but no dual OTA slots. তাই 4MB variant-কে remote dual-partition OTA supported বলে ধরে নিও না। 8MB বা বেশি flash থাকলে appropriate OTA-capable partition layout ব্যবহার করতে পারবে। **Flash size ভুল দিয়ে build/flash কোরো না।**

## 5. Flash & monitor

ESP32-কে USB-C/micro-USB দিয়ে computer-এ connect করো, তারপর **repo folder থেকে**:

```bash
idf.py -p /dev/cu.usbserial-0001 flash monitor
```

`/dev/cu.usbserial-0001` example macOS serial port। Windows হলে `COM3`, Linux হলে `/dev/ttyUSB0`; তোমার actual port বসাও। পুরনো firmware/settings প্রয়োজন হলে আগে backup নাও।

First boot-এ Wi-Fi provisioning setup করো। OLED status, mic, speaker ও PTT test করো। Server reachable না হলে local OTA URL, firewall ও server config চেক করো।

## 6. Verification

1. `FalconAI`-tagged serial boot log আসে।
2. OLED display জ্বলে এবং Wi-Fi setup হয়।
3. Device তোমার server-এর OTA endpoint reach করে।
4. Device activation/pairing নিজস্ব dashboard-এ হয়।
5. GPIO27 ধরে কথা বললে ASR → LLM → TTS → speaker response হয়।
6. PIN mismatch, no sound, frozen display হলে wiring / supply পরীক্ষা করো।

**Tests included:** `python3 -m unittest discover -s tests -v` — script patching tests, not hardware tests।

## 7. Limitations & safety

- `.bin` compile করার জন্য local ESP-IDF এবং actual upstream checkout প্রয়োজন। এখানে compile করা হয়নি।
- Script current documented upstream Kconfig/CMake structure-এর সঙ্গে লেখা; তোমার fork অনেক বেশি modified হলে safe error হতে পারে।
- OLED 128x64 SSD1306 0x3C assumed; SH1106 বা অন্য controller হলে driver adjust প্রয়োজন।
- Default board-specific MCP lamp is disabled because no lamp is part of this wiring.
- `--ota-url` must point to **your** own server, never official XiaoZhi cloud.
- Public deployment requires HTTPS/WSS, proper auth, server secret management.
- তুমিই exact GPIO hardware-তে verify করে flash করবে।

## Source / licenses

- Firmware upstream: https://github.com/78/xiaozhi-esp32
- Self-hosted server: https://github.com/xinnan-tech/xiaozhi-esp32-server
- Custom board instructions: https://github.com/78/xiaozhi-esp32/blob/main/docs/custom-board.md

Upstream firmware license and attribution must remain intact. This overlay ships none of the upstream source code and does not overwrite it; it copies your local upstream board implementation into a *new* board folder.
