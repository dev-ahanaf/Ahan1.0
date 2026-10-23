#include "config_store.h"

ConfigStore& ConfigStore::instance() {
    static ConfigStore store;
    return store;
}

bool ConfigStore::begin() {
    if (!prefs.begin("myvoice", false)) {
        Serial.println("[NVS] Failed to initialize preferences");
        return false;
    }
    deviceToken = prefs.getString("token", "");
    pairCode = prefs.getString("paircode", "");
    paired = prefs.getBool("paired", false);
    
    currentConfig.config_version = prefs.getInt("cfg_ver", 1);
    currentConfig.name = prefs.getString("name", "My ESP32");
    currentConfig.timezone = prefs.getString("tz", "Asia/Dhaka");
    currentConfig.language = prefs.getString("lang", "en");
    currentConfig.city = prefs.getString("city", "Dhaka");
    currentConfig.oled_brightness = prefs.getInt("bright", 128);
    currentConfig.idle_display_mode = prefs.getString("idle_mode", "clock");
    currentConfig.clock_format = prefs.getString("clk_fmt", "24h");
    currentConfig.speaker_volume = prefs.getInt("spk_vol", 80);
    currentConfig.mic_gain = prefs.getInt("mic_gain", 50);
    currentConfig.wake_mode = prefs.getString("wake_mode", "button");
    currentConfig.weather_enabled = prefs.getBool("wtr_en", true);
    currentConfig.search_enabled = prefs.getBool("srch_en", true);
    currentConfig.timers_enabled = prefs.getBool("tmr_en", true);
    
    return true;
}

String ConfigStore::getDeviceId() {
    return deviceId;
}

void ConfigStore::setDeviceId(const String &id) {
    deviceId = id;
}

String ConfigStore::getDeviceToken() {
    return deviceToken;
}

void ConfigStore::setDeviceToken(const String &token) {
    deviceToken = token;
    prefs.putString("token", token);
}

String ConfigStore::getPairCode() {
    return pairCode;
}

void ConfigStore::setPairCode(const String &code) {
    pairCode = code;
    prefs.putString("paircode", code);
}

void ConfigStore::clearPairCode() {
    pairCode = "";
    prefs.remove("paircode");
}

bool ConfigStore::isPaired() {
    return paired;
}

void ConfigStore::setPaired(bool p) {
    paired = p;
    prefs.putBool("paired", p);
    if (p) {
        clearPairCode();
    }
}

DeviceConfig& ConfigStore::getConfig() {
    return currentConfig;
}

void ConfigStore::saveConfig(const DeviceConfig &newConfig) {
    currentConfig = newConfig;
    prefs.putInt("cfg_ver", newConfig.config_version);
    prefs.putString("name", newConfig.name);
    prefs.putString("tz", newConfig.timezone);
    prefs.putString("lang", newConfig.language);
    prefs.putString("city", newConfig.city);
    prefs.putInt("bright", newConfig.oled_brightness);
    prefs.putString("idle_mode", newConfig.idle_display_mode);
    prefs.putString("clk_fmt", newConfig.clock_format);
    prefs.putInt("spk_vol", newConfig.speaker_volume);
    prefs.putInt("mic_gain", newConfig.mic_gain);
    prefs.putString("wake_mode", newConfig.wake_mode);
    prefs.putBool("wtr_en", newConfig.weather_enabled);
    prefs.putBool("srch_en", newConfig.search_enabled);
    prefs.putBool("tmr_en", newConfig.timers_enabled);
}
