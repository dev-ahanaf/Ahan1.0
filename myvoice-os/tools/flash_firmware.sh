#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FIRMWARE_DIR="$PROJECT_ROOT/firmware"
PIO_BIN="$PROJECT_ROOT/server/.venv/bin/pio"

echo "=================================================="
echo "      MyVoice OS - ESP32 Firmware Flasher         "
echo "=================================================="

# Check for PlatformIO binary
if [ ! -f "$PIO_BIN" ]; then
    echo "[-] Error: PlatformIO not found at $PIO_BIN"
    exit 1
fi

# Detect serial port
PORTS=$(ls /dev/cu.usbserial* /dev/cu.wchusbserial* /dev/cu.SLAB_USBtoUART* /dev/cu.usbmodem* 2>/dev/null || true)

if [ -z "$PORTS" ]; then
    echo "[!] No ESP32 serial port detected."
    echo "    Please plug your ESP32 board into a USB port on this Mac."
    echo "    Available /dev/cu.* ports:"
    ls /dev/cu.*
    exit 1
fi

SELECTED_PORT=$(echo "$PORTS" | head -n 1)
echo "[+] Detected ESP32 on port: $SELECTED_PORT"

echo "[+] Building and uploading firmware..."
cd "$FIRMWARE_DIR"
"$PIO_BIN" run --target upload --upload-port "$SELECTED_PORT"

echo ""
echo "[✓] Flash completed successfully!"
echo "[+] Opening serial monitor (Press Ctrl+C to exit)..."
"$PIO_BIN" device monitor -b 115200 --port "$SELECTED_PORT"
