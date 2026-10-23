#include "diagnostics.h"
#include <Wire.h>
#include <WiFi.h>
#include <LittleFS.h>
#include "pins.h"
#include "display.h"
#include "audio_in.h"
#include "audio_out.h"
#include "config_store.h"

void runHardwareDiagnostics() {
    Serial.println("\n=========================================");
    Serial.println("  MYVOICE OS - HARDWARE DIAGNOSTICS SUITE");
    Serial.println("=========================================\n");

    DisplayManager::instance().setDiagnosticsText("RAM/Flash Check", "Testing...", "");
    DisplayManager::instance().setState(DisplayState::DIAGNOSTICS);

    // 1. Memory Check
    uint32_t freeHeap = ESP.getFreeHeap();
    uint32_t minHeap = ESP.getMinFreeHeap();
    size_t totalBytes = LittleFS.totalBytes();
    size_t usedBytes = LittleFS.usedBytes();
    Serial.printf("[1/7] Memory: Free Heap=%u B, Min Free=%u B, Flash Storage=%u/%u B\n",
                  freeHeap, minHeap, usedBytes, totalBytes);

    // 2. Button Test
    int btnState = digitalRead(BUTTON_PIN);
    Serial.printf("[2/7] Button (GPIO 27): %s (Expected: Pressed/LOW)\n",
                  btnState == LOW ? "DETECTED (LOW)" : "RELEASED (HIGH)");

    // 3. I2C Bus Scan
    Serial.println("[3/7] Scanning I2C bus (SDA=18, SCL=19)...");
    byte oledFound = 0;
    for (byte addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.printf("  - I2C device detected at 0x%02X\n", addr);
            if (addr == OLED_I2C_ADDR || addr == 0x3D) oledFound = addr;
        }
    }
    Serial.printf("  OLED SSD1306 Status: %s\n", oledFound ? "PASSED" : "NOT FOUND");

    // 4. Microphone Test (INMP441)
    DisplayManager::instance().setDiagnosticsText("Testing Mic...", "Speak / Tap mic", "");
    DisplayManager::instance().update();
    Serial.println("[4/7] Testing INMP441 Microphone sampling...");
    float micRms = measureMicRms(1024);
    Serial.printf("  Mic Noise Floor / Signal RMS: %.2f (Normal silent range: 50-800)\n", micRms);

    // 5. Speaker Test (MAX98357A)
    DisplayManager::instance().setDiagnosticsText("Testing Speaker...", "440 Hz Tone Burst", "");
    DisplayManager::instance().update();
    Serial.println("[5/7] Testing MAX98357A Speaker tone (440 Hz for 400ms)...");
    playTestTone(440, 400);
    Serial.println("  Speaker tone playback completed");

    // 6. Wi-Fi Scan
    DisplayManager::instance().setDiagnosticsText("Scanning Wi-Fi...", "Finding APs", "");
    DisplayManager::instance().update();
    Serial.println("[6/7] Scanning Wi-Fi networks...");
    int n = WiFi.scanNetworks();
    Serial.printf("  Found %d Wi-Fi networks nearby\n", n);
    for (int i = 0; i < min(n, 5); i++) {
        Serial.printf("    - %s (%d dBm)\n", WiFi.SSID(i).c_str(), WiFi.RSSI(i));
    }

    // 7. Identity & Firmware
    String mac = WiFi.macAddress();
    Serial.printf("[7/7] Identity: MAC=%s, FW Version=%s\n", mac.c_str(), DEVICE_FW_VERSION);

    char line1[24];
    char line2[24];
    char line3[24];
    snprintf(line1, sizeof(line1), "Heap:%uk Mic:%.0f", freeHeap / 1024, micRms);
    snprintf(line2, sizeof(line2), "OLED:%s Spk:OK", oledFound ? "OK" : "NO");
    snprintf(line3, sizeof(line3), "MAC:%s", mac.substring(9).c_str());

    DisplayManager::instance().setDiagnosticsText(line1, line2, line3);
    DisplayManager::instance().update();

    Serial.println("\n[Diagnostics Completed] Release button and reboot to enter normal mode.\n");
    while (true) {
        DisplayManager::instance().update();
        delay(100);
    }
}
