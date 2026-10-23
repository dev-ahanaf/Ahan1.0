#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$DIR")"
VENV_ESPTOOL="$ROOT_DIR/myvoice-os/server/.venv/bin/esptool.py"

echo "=================================================="
echo "    Falcon AI v1.2 - Direct Firmware Flasher      "
echo "=================================================="

# 1. Locate esptool
if [ -f "$VENV_ESPTOOL" ]; then
    ESPTOOL_BIN="$VENV_ESPTOOL"
elif command -v esptool.py >/dev/null 2>&1; then
    ESPTOOL_BIN="esptool.py"
elif command -v esptool >/dev/null 2>&1; then
    ESPTOOL_BIN="esptool"
else
    echo "[-] Error: esptool not found. Install it with: pip install esptool"
    exit 1
fi

echo "[+] Using flasher: $ESPTOOL_BIN"

# 2. Detect serial port if not provided as argument
if [ -n "$1" ]; then
    PORT="$1"
else
    PORTS=$(ls /dev/cu.usbserial* /dev/cu.wchusbserial* /dev/cu.SLAB_USBtoUART* /dev/cu.usbmodem* 2>/dev/null || true)
    if [ -z "$PORTS" ]; then
        echo "[!] No ESP32 serial port automatically detected."
        echo "    Please connect your ESP32 board to your computer via USB."
        echo "    Usage: ./flash.sh <PORT>"
        echo "    Available /dev/cu.* ports:"
        ls /dev/cu.*
        exit 1
    fi
    PORT=$(echo "$PORTS" | head -n 1)
fi

echo "[+] Target Port: $PORT"
echo "[+] Chip: ESP32"
echo "[+] Baud Rate: 921600"
echo ""
echo "[+] Flashing partitions:"
echo "    - 0x1000  : bootloader.bin"
echo "    - 0x8000  : partitions.bin"
echo "    - 0xe000  : boot_app0.bin"
echo "    - 0x10000 : firmware.bin (Falcon AI v1.2.0)"
echo ""

"$ESPTOOL_BIN" --chip esp32 --port "$PORT" --baud 921600 \
    --before default_reset --after hard_reset write_flash -z \
    --flash_mode dio --flash_freq 40m --flash_size 4MB \
    0x1000 "$DIR/bootloader.bin" \
    0x8000 "$DIR/partitions.bin" \
    0xe000 "$DIR/boot_app0.bin" \
    0x10000 "$DIR/firmware.bin"

echo ""
echo "=================================================="
echo "[✓] Flash Complete! ESP32 is rebooting into Falcon AI."
echo "=================================================="
echo "Next Steps:"
echo " 1. Look for 'FalconAI-Setup' Wi-Fi AP (pass: myvoice123)."
echo " 2. Connect and configure your local Wi-Fi network."
echo " 3. Read the 6-digit pairing code on the OLED screen."
echo " 4. Pair in Falcon AI Console at http://localhost:5173"
