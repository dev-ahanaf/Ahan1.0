#include "net_client.h"
#include <LittleFS.h>
#include <time.h>
#include "display.h"
#include "audio_in.h"
#include "audio_out.h"

NetClient& NetClient::instance() {
    static NetClient client;
    return client;
}

String NetClient::apiUrl(const char *path) {
    return String(API_BASE_URL) + path;
}

void NetClient::addAuthHeaders(HTTPClient &http) {
    http.addHeader("X-Device-ID", ConfigStore::instance().getDeviceId());
    http.addHeader("X-Device-Token", ConfigStore::instance().getDeviceToken());
}

bool NetClient::bootstrap() {
    if (ConfigStore::instance().isPaired()) return true;

    DisplayManager::instance().setState(DisplayState::CONNECTING_SERVER);
    HTTPClient http;
    http.begin(apiUrl("/api/device/bootstrap"));
    http.setTimeout(10000);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Enrollment-Key", ENROLLMENT_KEY);

    DynamicJsonDocument req(256);
    req["device_id"] = ConfigStore::instance().getDeviceId();
    req["firmware"] = DEVICE_FW_VERSION;
    String payload;
    serializeJson(req, payload);

    int code = http.POST(payload);
    String body = http.getString();
    http.end();

    if (code != 200) {
        Serial.printf("[Net] Bootstrap failed HTTP %d: %s\n", code, body.c_str());
        DisplayManager::instance().setErrorMessage("Bootstrap Err");
        DisplayManager::instance().setState(DisplayState::ERROR_STATE);
        return false;
    }

    DynamicJsonDocument doc(512);
    if (deserializeJson(doc, body)) {
        Serial.println("[Net] Bootstrap JSON parse error");
        return false;
    }

    String token = doc["token"].as<String>();
    String pairCode = doc["pair_code"].as<String>();
    if (token.length() == 0) return false;

    ConfigStore::instance().setDeviceToken(token);
    ConfigStore::instance().setPairCode(pairCode);
    ConfigStore::instance().setPaired(false);

    DisplayManager::instance().setPairCode(pairCode);
    DisplayManager::instance().setState(DisplayState::PAIRING_CODE);

    Serial.println("\n=========================================");
    Serial.printf("  FALCON AI PAIRING CODE: %s\n", pairCode.c_str());
    Serial.println("  Enter in web dashboard within 10 minutes");
    Serial.println("=========================================\n");

    return true;
}

bool NetClient::pollStatus() {
    if (ConfigStore::instance().getDeviceToken().length() == 0) return false;

    HTTPClient http;
    http.begin(apiUrl("/api/device/status"));
    http.setTimeout(10000);
    addAuthHeaders(http);

    int status = http.GET();
    String body = http.getString();
    http.end();

    if (status == 401) {
        Serial.println("[Net] Device token rejected or revoked. Re-bootstrapping...");
        ConfigStore::instance().setDeviceToken("");
        ConfigStore::instance().setPairCode("");
        bootstrap();
        return false;
    }
    if (status != 200) {
        Serial.printf("[Net] Status error HTTP %d\n", status);
        return false;
    }

    DynamicJsonDocument doc(512);
    if (deserializeJson(doc, body)) return false;

    bool isPaired = doc["paired"].as<bool>();
    String renewedCode = doc["pair_code"].as<String>();
    if (renewedCode.length() > 0) {
        ConfigStore::instance().setPairCode(renewedCode);
        DisplayManager::instance().setPairCode(renewedCode);
        DisplayManager::instance().setState(DisplayState::PAIRING_CODE);
        Serial.printf("[Net] Active Pairing Code: %s\n", renewedCode.c_str());
    } else if (!isPaired) {
        String savedCode = ConfigStore::instance().getPairCode();
        if (savedCode.length() > 0) {
            DisplayManager::instance().setPairCode(savedCode);
            DisplayManager::instance().setState(DisplayState::PAIRING_CODE);
        }
    }

    if (isPaired && !ConfigStore::instance().isPaired()) {
        ConfigStore::instance().setPaired(true);
        Serial.println("[Net] Device paired successfully!");
        fetchConfig();
        DisplayManager::instance().setState(DisplayState::IDLE_CLOCK);
    }

    return true;
}

bool NetClient::sendHeartbeat() {
    if (!ConfigStore::instance().isPaired()) return false;

    HTTPClient http;
    http.begin(apiUrl("/api/device/heartbeat"));
    http.setTimeout(8000);
    addAuthHeaders(http);
    http.addHeader("Content-Type", "application/json");

    DynamicJsonDocument req(128);
    req["free_heap"] = ESP.getFreeHeap();
    req["wifi_rssi"] = WiFi.RSSI();
    String payload;
    serializeJson(req, payload);

    int status = http.POST(payload);
    String body = http.getString();
    http.end();

    if (status == 401 || status == 403) {
        ConfigStore::instance().setPaired(false);
        DisplayManager::instance().setErrorMessage("Auth Expired");
        DisplayManager::instance().setState(DisplayState::ERROR_STATE);
        return false;
    }
    if (status != 200) return false;

    DynamicJsonDocument doc(256);
    if (deserializeJson(doc, body)) return false;

    int serverVer = doc["config_version"].as<int>();
    if (serverVer > ConfigStore::instance().getConfig().config_version) {
        Serial.printf("[Net] Server config version %d > local %d. Fetching config...\n",
                      serverVer, ConfigStore::instance().getConfig().config_version);
        fetchConfig();
    }

    return true;
}

bool NetClient::fetchConfig() {
    if (!ConfigStore::instance().isPaired()) return false;

    HTTPClient http;
    http.begin(apiUrl("/api/device/config"));
    http.setTimeout(10000);
    addAuthHeaders(http);

    int status = http.GET();
    String body = http.getString();
    http.end();

    if (status != 200) {
        Serial.printf("[Net] Fetch config failed HTTP %d\n", status);
        return false;
    }

    DynamicJsonDocument doc(768);
    if (deserializeJson(doc, body)) return false;

    DeviceConfig cfg;
    cfg.config_version = doc["config_version"].as<int>();
    cfg.name = doc["name"].as<String>();
    cfg.timezone = doc["timezone"].as<String>();
    cfg.language = doc["language"].as<String>();
    cfg.city = doc["city"].as<String>();
    cfg.oled_brightness = doc["oled_brightness"].as<int>();
    cfg.idle_display_mode = doc["idle_display_mode"].as<String>();
    cfg.clock_format = doc["clock_format"].as<String>();
    cfg.speaker_volume = doc["speaker_volume"].as<int>();
    cfg.mic_gain = doc["mic_gain"].as<int>();
    cfg.wake_mode = doc["wake_mode"].as<String>();
    cfg.weather_enabled = doc["weather_enabled"].as<bool>();
    cfg.search_enabled = doc["search_enabled"].as<bool>();
    cfg.timers_enabled = doc["timers_enabled"].as<bool>();

    ConfigStore::instance().saveConfig(cfg);
    DisplayManager::instance().setBrightness(cfg.oled_brightness);
    Serial.printf("[Net] Local config updated to version %d\n", cfg.config_version);
    return true;
}

bool NetClient::fetchWeather() {
    if (!ConfigStore::instance().isPaired() || !ConfigStore::instance().getConfig().weather_enabled) return false;

    HTTPClient http;
    http.begin(apiUrl("/api/device/weather"));
    http.setTimeout(12000);
    addAuthHeaders(http);

    int status = http.GET();
    String body = http.getString();
    http.end();

    if (status != 200) {
        Serial.printf("[Net] Weather failed HTTP %d\n", status);
        return false;
    }

    DynamicJsonDocument doc(512);
    if (deserializeJson(doc, body)) return false;

    String city = doc["city"].as<String>();
    float tempC = doc["temperature_c"].as<float>();
    String cond = doc["conditions"].as<String>();

    DisplayManager::instance().setWeatherInfo(city, tempC, cond);
    Serial.printf("[Weather] %s: %.1f C, %s\n", city.c_str(), tempC, cond.c_str());
    return true;
}

bool NetClient::syncNtpTime() {
    configTime(GMT_OFFSET_SEC, 0, "pool.ntp.org", "time.google.com");
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 5000)) {
        Serial.println("[NTP] Time synchronized successfully");
        return true;
    }
    Serial.println("[NTP] Time synchronization timed out");
    return false;
}

bool NetClient::sendVoiceRecording() {
    if (!ConfigStore::instance().isPaired()) {
        Serial.println("[Voice] Cannot record: Device not paired");
        return false;
    }

    DisplayManager::instance().setState(DisplayState::LISTENING);
    int gain = ConfigStore::instance().getConfig().mic_gain;
    if (!recordWav("/voice.wav", gain)) {
        DisplayManager::instance().setErrorMessage("Mic Fail");
        DisplayManager::instance().setState(DisplayState::ERROR_STATE);
        return false;
    }

    File f = LittleFS.open("/voice.wav", "r");
    if (!f) return false;

    DisplayManager::instance().setState(DisplayState::THINKING);
    HTTPClient http;
    http.begin(apiUrl("/api/device/voice"));
    http.setTimeout(60000);
    addAuthHeaders(http);
    http.addHeader("Content-Type", "audio/wav");

    // Stream from flash without loading entire file into RAM
    int status = http.sendRequest("POST", &f, f.size());
    f.close();
    LittleFS.remove("/voice.wav");

    if (status != 200) {
        Serial.printf("[Voice] Server returned HTTP %d: %s\n", status, http.getString().c_str());
        DisplayManager::instance().setErrorMessage("Audio Error");
        DisplayManager::instance().setState(DisplayState::ERROR_STATE);
        http.end();
        return false;
    }

    DisplayManager::instance().setState(DisplayState::SPEAKING);
    int volume = ConfigStore::instance().getConfig().speaker_volume;
    bool playbackOk = playWavStream(*http.getStreamPtr(), volume);
    http.end();

    DisplayManager::instance().setState(DisplayState::IDLE_CLOCK);
    return playbackOk;
}
