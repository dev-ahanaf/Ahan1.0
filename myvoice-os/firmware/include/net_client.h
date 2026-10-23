#pragma once
#include <Arduino.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "pins.h"
#include "config_store.h"

class NetClient {
public:
    static NetClient& instance();
    
    bool bootstrap();
    bool pollStatus();
    bool sendHeartbeat();
    bool fetchConfig();
    bool fetchWeather();
    bool syncNtpTime();
    bool sendVoiceRecording();

private:
    NetClient() = default;
    String apiUrl(const char *path);
    void addAuthHeaders(HTTPClient &http);
};
