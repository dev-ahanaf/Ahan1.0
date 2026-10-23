#pragma once
#include <Arduino.h>

#if __has_include("secrets.h")
#include "secrets.h"
#else
// Safe fallback defaults for compiling/linting without secrets.h
#define API_BASE_URL "http://192.168.1.100:8000"
#define ENROLLMENT_KEY "replace-with-long-random-enrollment-key"
#define PROVISIONING_AP_PASSWORD "CHANGE_ME_1234"
#define DEVICE_FW_VERSION "0.1.0"
#define GMT_OFFSET_SEC (6 * 3600)
#endif

// ============================================================================
// SKR WIRING DIAGRAM PINOUT (XiaoZhi Bread-Compact ESP32 Standard)
// ============================================================================

// Tactile push-to-talk button: Onboard BOOT button (GPIO 0 has built-in hardware pullup on ESP32)
static constexpr int BUTTON_BOOT_PIN = 0;
// Optional external button pin (set to -1 when not physically wired to prevent floating auto-triggers)
static constexpr int BUTTON_PIN = -1;

inline bool isVoiceButtonPressed() {
    if (digitalRead(BUTTON_BOOT_PIN) == LOW) {
        return true;
    }
    if (BUTTON_PIN >= 0 && digitalRead(BUTTON_PIN) == LOW) {
        return true;
    }
    return false;
}

// Status LED (GPIO 18 via 220-ohm resistor)
static constexpr int LED_PIN = 18;

// INMP441 I2S Microphone pins (I2S0)
static constexpr int MIC_BCLK = 26; // SCK
static constexpr int MIC_WS   = 25; // WS / LRCL
static constexpr int MIC_DATA = 32; // SD / DOUT

// MAX98357A I2S Amplifier pins (I2S1)
static constexpr int SPK_BCLK = 14; // BCLK
static constexpr int SPK_WS   = 27; // LRC / WS
static constexpr int SPK_DATA = 33; // DIN

// SSD1306 128x64 OLED Display pins (I2C)
static constexpr int OLED_SDA = 4;
static constexpr int OLED_SCL = 15;
static constexpr uint8_t OLED_I2C_ADDR = 0x3C;
static constexpr int SCREEN_WIDTH = 128;
static constexpr int SCREEN_HEIGHT = 64;

// Audio acquisition parameters
static constexpr int RECORD_HZ = 16000;
static constexpr int RECORD_SECONDS = 3;
static constexpr size_t RECORD_SAMPLES = RECORD_HZ * RECORD_SECONDS;

// Default polling intervals (milliseconds)
static constexpr unsigned long POLL_STATUS_MS = 5000;
static constexpr unsigned long HEARTBEAT_INTERVAL_MS = 30000;
static constexpr unsigned long WEATHER_POLL_MS = 5UL * 60UL * 1000UL;
static constexpr unsigned long CLOCK_UPDATE_MS = 1000UL;
