@echo off
setlocal
echo ==================================================
echo     Falcon AI v1.2 - Direct Firmware Flasher (Win)
echo ==================================================

if "%~1"=="" (
    echo Usage: flash.bat COM_PORT
    echo Example: flash.bat COM3
    exit /b 1
)

set PORT=%~1
echo Target Port: %PORT%

esptool.exe --chip esp32 --port %PORT% --baud 921600 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 40m --flash_size 4MB 0x1000 bootloader.bin 0x8000 partitions.bin 0xe000 boot_app0.bin 0x10000 firmware.bin

echo.
echo Flash completed! Check Falcon AI console.
