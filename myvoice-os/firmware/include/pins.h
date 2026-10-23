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

// Tactile push-to-talk button: Supports BOTH external button (GPIO 27) and onboard BOOT button (GPIO 0)
static constexpr int BUTTON_PIN = 27;
static constexpr int BUTTON_BOOT_PIN = 0;

inline bool isVoiceButtonPressed() {
    return (digitalRead(BUTTON_PIN) == LOW) || (digitalRead(BUTTON_BOOT_PIN) == LOW);
}

// INMP441 I2S Microphone pins (I2S0)
static constexpr int MIC_BCLK = 26; // SCK
static constexpr int MIC_WS   = 25; // WS / LRCL
static constexpr int MIC_DATA = 33; // SD / DOUT

// MAX98357A I2S Amplifier pins (I2S1)
static constexpr int SPK_BCLK = 14; // BCLK
static constexpr int SPK_WS   = 13; // LRC / WS
static constexpr int SPK_DATA = 22; // DIN

// SSD1306 128x64 OLED Display pins (I2C)
static constexpr int OLED_SDA = 18;
static constexpr int OLED_SCL = 19;
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
