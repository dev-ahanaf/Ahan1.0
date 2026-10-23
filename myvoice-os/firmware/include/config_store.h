#pragma once
#include <Arduino.h>
#include <Preferences.h>

struct DeviceConfig {
    int config_version = 1;
    String name = "My ESP32";
    String timezone = "Asia/Dhaka";
    String language = "en";
    String city = "Dhaka";
    int oled_brightness = 128;
    String idle_display_mode = "clock";
    String clock_format = "24h";
    int speaker_volume = 80;
    int mic_gain = 50;
    String wake_mode = "button";
    bool weather_enabled = true;
    bool search_enabled = true;
    bool timers_enabled = true;
};

class ConfigStore {
public:
    static ConfigStore& instance();
    bool begin();
    
    String getDeviceId();
    void setDeviceId(const String &id);
    
    String getDeviceToken();
    void setDeviceToken(const String &token);
    
    String getPairCode();
    void setPairCode(const String &code);
    void clearPairCode();
    
    bool isPaired();
    void setPaired(bool paired);
    
    DeviceConfig& getConfig();
    void saveConfig(const DeviceConfig &newConfig);

private:
    ConfigStore() = default;
    Preferences prefs;
    String deviceId;
    String deviceToken;
    String pairCode;
    bool paired = false;
    DeviceConfig currentConfig;
};
