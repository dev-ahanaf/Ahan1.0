#include "wifi_setup.h"
#include "display.h"

bool setupWifi() {
    WiFi.mode(WIFI_STA);
    WiFiManager manager;
    manager.setConfigPortalTimeout(180);
    
    DisplayManager::instance().setState(DisplayState::CONNECTING_WIFI);
    Serial.println("[WiFi] Starting auto-connect or portal...");
    
    bool connected = manager.autoConnect("FalconAI-Setup", PROVISIONING_AP_PASSWORD);
    if (!connected) {
        Serial.println("[WiFi] Provisioning portal timed out. Restarting...");
        DisplayManager::instance().setErrorMessage("WiFi Timeout");
        DisplayManager::instance().setState(DisplayState::ERROR_STATE);
        delay(3000);
        ESP.restart();
    }
    
    Serial.printf("[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
    return true;
}

bool isWifiConnected() {
    return WiFi.status() == WL_CONNECTED;
}

void checkWifiReconnect() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[WiFi] Connection lost, reconnecting...");
        DisplayManager::instance().setState(DisplayState::CONNECTING_WIFI);
        WiFi.reconnect();
    }
}
