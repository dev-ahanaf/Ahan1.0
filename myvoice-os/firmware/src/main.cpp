#include <Arduino.h>
#include <LittleFS.h>
#include "pins.h"
#include "config_store.h"
#include "display.h"
#include "audio_in.h"
#include "audio_out.h"
#include "wifi_setup.h"
#include "net_client.h"
#include "ws_client.h"
#include "diagnostics.h"

static unsigned long lastPoll = 0;
static unsigned long lastHeartbeat = 0;
static unsigned long lastWeather = 0;
static bool audioInReady = false;
static bool audioOutReady = false;
static bool wsInitialized = false;

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n[System] Falcon AI Firmware v1.2 Initializing...");

    pinMode(BUTTON_PIN, INPUT_PULLUP);
    pinMode(BUTTON_BOOT_PIN, INPUT_PULLUP);
    
    if (!LittleFS.begin(true)) {
        Serial.println("[LittleFS] Mount failed");
    }

    ConfigStore::instance().begin();
    DisplayManager::instance().begin();

    // Check for Hardware Diagnostics mode: Button held down on boot
    if (digitalRead(BUTTON_PIN) == LOW) {
        delay(50);
        if (digitalRead(BUTTON_PIN) == LOW) {
            audioInReady = initAudioIn();
            audioOutReady = initAudioOut();
            runHardwareDiagnostics();
        }
    }

    audioInReady = initAudioIn();
    audioOutReady = initAudioOut();

    setupWifi();
    ConfigStore::instance().setDeviceId(WiFi.macAddress());
    NetClient::instance().syncNtpTime();

    if (!ConfigStore::instance().isPaired()) {
        String savedCode = ConfigStore::instance().getPairCode();
        if (savedCode.length() > 0) {
            DisplayManager::instance().setPairCode(savedCode);
            DisplayManager::instance().setState(DisplayState::PAIRING_CODE);
        }
        NetClient::instance().bootstrap();
        NetClient::instance().pollStatus();
    } else {
        NetClient::instance().fetchConfig();
        NetClient::instance().fetchWeather();
        DisplayManager::instance().setState(DisplayState::IDLE_CLOCK);
        wsInitialized = initWebSocketClient();
    }
}

void loop() {
    checkWifiReconnect();
    DisplayManager::instance().update();

    if (wsInitialized) {
        loopWebSocketClient();
    }

    unsigned long ms = millis();

    // 1. Unpaired status polling loop
    if (!ConfigStore::instance().isPaired()) {
        if (ms - lastPoll >= POLL_STATUS_MS) {
            lastPoll = ms;
            NetClient::instance().pollStatus();
            if (ConfigStore::instance().isPaired() && !wsInitialized) {
                wsInitialized = initWebSocketClient();
            }
        }
    }

    // 2. Paired keepalive heartbeat loop
    if (ConfigStore::instance().isPaired()) {
        if (ms - lastHeartbeat >= HEARTBEAT_INTERVAL_MS) {
            lastHeartbeat = ms;
            NetClient::instance().sendHeartbeat();
        }

        // 3. Weather poll loop
        if (ms - lastWeather >= WEATHER_POLL_MS) {
            lastWeather = ms;
            NetClient::instance().fetchWeather();
        }
    }

    // 4. Voice Button Handling (WebSocket Real-Time with HTTP Fallback)
    if (ConfigStore::instance().isPaired() && audioInReady && audioOutReady) {
        if (isVoiceButtonPressed()) {
            delay(35); // Debounce
            if (isVoiceButtonPressed()) {
                if (isWebSocketConnected()) {
                    WsState currState = getWebSocketState();
                    if (currState == WS_STATE_SPEAKING || currState == WS_STATE_THINKING) {
                        // User barge-in interruption: cancel ongoing playback
                        Serial.println("[Button] User interrupt barge-in!");
                        triggerBargeInAbort();
                        while (isVoiceButtonPressed()) {
                            delay(10);
                        }
                    } else {
                        // Real-time voice stream while button is held
                        Serial.println("[Button] Starting real-time WebSocket voice stream...");
                        startVoiceStream();
                        while (isVoiceButtonPressed()) {
                            loopWebSocketClient();
                            DisplayManager::instance().update();
                            delay(5);
                        }
                        Serial.println("[Button] Button released. Stopping voice stream...");
                        stopVoiceStream();
                    }
                } else {
                    // Fallback to Phase 1 HTTP push-to-talk
                    Serial.println("[Button] WebSocket offline. Using HTTP fallback push-to-talk...");
                    NetClient::instance().sendVoiceRecording();
                    while (isVoiceButtonPressed()) {
                        delay(10);
                    }
                }
                delay(100);
            }
        }
    }

    delay(5);
}
