#pragma once
#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "pins.h"

enum class DisplayState {
    BOOTING,
    CONNECTING_WIFI,
    CONNECTING_SERVER,
    PAIRING_CODE,
    IDLE_CLOCK,
    IDLE_WEATHER,
    LISTENING,
    THINKING,
    SPEAKING,
    ERROR_STATE,
    DIAGNOSTICS
};

class DisplayManager {
public:
    static DisplayManager& instance();
    bool begin();
    
    void setState(DisplayState state);
    DisplayState getState() const { return currentState; }
    
    void setPairCode(const String &code);
    void setErrorMessage(const String &msg);
    void setWeatherInfo(const String &city, float tempC, const String &condition);
    void setDiagnosticsText(const String &line1, const String &line2, const String &line3);
    void setBrightness(uint8_t brightness);
    
    void update(); // Called in loop to render current state

private:
    DisplayManager();
    Adafruit_SSD1306 display;
    DisplayState currentState = DisplayState::BOOTING;
    String pairCode = "";
    String errorMsg = "";
    String weatherCity = "Dhaka";
    float weatherTemp = 28.0;
    String weatherCond = "Clear";
    String diag1, diag2, diag3;
    unsigned long lastRenderMs = 0;
    bool ready = false;
    
    void renderBooting();
    void renderConnectingWifi();
    void renderConnectingServer();
    void renderPairingCode();
    void renderIdleClock();
    void renderIdleWeather();
    void renderListening();
    void renderThinking();
    void renderSpeaking();
    void renderError();
    void renderDiagnostics();
};
