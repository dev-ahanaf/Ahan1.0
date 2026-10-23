# Falcon AI ESP32 Firmware Binaries (v1.2.0)

This folder contains the complete, pre-compiled firmware binaries ready to flash onto any standard ESP32 board without needing PlatformIO or Arduino IDE.

## Files & Memory Map Offsets

| File | Memory Offset | Description |
| :--- | :--- | :--- |
| `bootloader.bin` | `0x1000` | 2nd stage bootloader |
| `partitions.bin` | `0x8000` | Custom partition table (1.3MB app / OTA) |
| `boot_app0.bin` | `0xe000` | OTA boot partition selector |
| `firmware.bin` / `falcon_ai_firmware_v1.2.0.bin` | `0x10000` | Falcon AI application binary |

## Quick Flash (Mac / Linux)

1. Plug your ESP32 board into USB.
2. Run:
```bash
./flash.sh
```
Or specify the port manually:
```bash
./flash.sh /dev/cu.usbserial-0001
```

## Direct esptool.py Command

```bash
esptool.py --chip esp32 --port /dev/cu.<YOUR_PORT> --baud 921600 \
    --before default_reset --after hard_reset write_flash -z \
    --flash_mode dio --flash_freq 40m --flash_size 4MB \
    0x1000 bootloader.bin \
    0x8000 partitions.bin \
    0xe000 boot_app0.bin \
    0x10000 firmware.bin
```

## Using ESP Web Tools / Chrome Browser

If using web-based tools like [ESP Web Tools](https://esphome.github.io/esp-web-tools/) or [Adafruit Web Serial ESPTool](https://adafruit.github.io/Adafruit_WebSerial_ESPTool/):
1. Connect at 921600 or 115200 baud.
2. Add files at the respective offsets:
   - `0x1000` -> `bootloader.bin`
   - `0x8000` -> `partitions.bin`
   - `0xe000` -> `boot_app0.bin`
   - `0x10000` -> `firmware.bin`
3. Click **Program / Flash**.
