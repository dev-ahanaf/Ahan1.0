#include "display.h"
#include <Wire.h>
#include <time.h>
#include "config_store.h"

DisplayManager::DisplayManager()
    : display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1) {}

DisplayManager& DisplayManager::instance() {
    static DisplayManager mgr;
    return mgr;
}

bool DisplayManager::begin() {
    Wire.begin(OLED_SDA, OLED_SCL);
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR)) {
        Serial.println("[OLED] SSD1306 allocation failed");
        ready = false;
        return false;
    }
    ready = true;
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    setBrightness(ConfigStore::instance().getConfig().oled_brightness);
    renderBooting();
    display.display();
    return true;
}

void DisplayManager::setBrightness(uint8_t brightness) {
    if (!ready) return;
    display.dim(brightness < 128);
}

void DisplayManager::setState(DisplayState state) {
    currentState = state;
    update();
}

void DisplayManager::setPairCode(const String &code) {
    pairCode = code;
}

void DisplayManager::setErrorMessage(const String &msg) {
    errorMsg = msg;
}

void DisplayManager::setWeatherInfo(const String &city, float tempC, const String &condition) {
    weatherCity = city;
    weatherTemp = tempC;
    weatherCond = condition;
}

void DisplayManager::setDiagnosticsText(const String &line1, const String &line2, const String &line3) {
    diag1 = line1;
    diag2 = line2;
    diag3 = line3;
}

void DisplayManager::update() {
    if (!ready) return;
    unsigned long now = millis();
    // Throttle rendering to ~20 FPS (50ms) to prevent I2C bus flooding
    if (now - lastRenderMs < 50) return;
    lastRenderMs = now;

    display.clearDisplay();
    switch (currentState) {
        case DisplayState::BOOTING:           renderBooting(); break;
        case DisplayState::CONNECTING_WIFI:   renderConnectingWifi(); break;
        case DisplayState::CONNECTING_SERVER: renderConnectingServer(); break;
        case DisplayState::PAIRING_CODE:      renderPairingCode(); break;
        case DisplayState::IDLE_CLOCK:        renderIdleClock(); break;
        case DisplayState::IDLE_WEATHER:      renderIdleWeather(); break;
        case DisplayState::LISTENING:         renderListening(); break;
        case DisplayState::THINKING:          renderThinking(); break;
        case DisplayState::SPEAKING:          renderSpeaking(); break;
        case DisplayState::ERROR_STATE:       renderError(); break;
        case DisplayState::DIAGNOSTICS:       renderDiagnostics(); break;
    }
    display.display();
}

void DisplayManager::renderBooting() {
    display.setTextSize(1);
    display.setCursor(18, 12);
    display.println("FALCON AI v1.2");
    display.drawFastHLine(10, 26, 108, SSD1306_WHITE);
    display.setCursor(16, 38);
    display.println("Booting System...");
}

void DisplayManager::renderConnectingWifi() {
    display.setTextSize(1);
    display.setCursor(14, 10);
    display.println("Wi-Fi Setup");
    display.drawFastHLine(10, 22, 108, SSD1306_WHITE);
    display.setCursor(10, 32);
    display.println("Connecting or AP:");
    display.setCursor(10, 46);
    display.println("SSID: FalconAI-Setup");
}

void DisplayManager::renderConnectingServer() {
    display.setTextSize(1);
    display.setCursor(10, 10);
    display.println("Server Handshake");
    display.drawFastHLine(10, 22, 108, SSD1306_WHITE);
    display.setCursor(10, 34);
    display.println("Reaching Backend...");
    display.setCursor(10, 48);
    display.println(ConfigStore::instance().getDeviceId().substring(9));
}

void DisplayManager::renderPairingCode() {
    display.setTextSize(1);
    display.setCursor(20, 4);
    display.println("PAIRING CODE");
    display.drawFastHLine(10, 15, 108, SSD1306_WHITE);
    
    display.setTextSize(2);
    display.setCursor(28, 22);
    if (pairCode.length() == 6) {
        display.println(pairCode);
    } else {
        display.println("------");
    }
    
    display.setTextSize(1);
    display.setCursor(8, 48);
    display.println("Enter at Web Console");
}

void DisplayManager::renderIdleClock() {
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 10)) {
        display.setTextSize(2);
        display.setCursor(18, 14);
        if (ConfigStore::instance().getConfig().clock_format == "12h") {
            int hour12 = timeinfo.tm_hour % 12;
            if (hour12 == 0) hour12 = 12;
            char buf[16];
            snprintf(buf, sizeof(buf), "%02d:%02d %s", hour12, timeinfo.tm_min, timeinfo.tm_hour >= 12 ? "PM" : "AM");
            display.println(buf);
        } else {
            char buf[16];
            snprintf(buf, sizeof(buf), "  %02d:%02d:%02d", timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
            display.println(buf);
        }
        
        display.setTextSize(1);
        display.setCursor(22, 42);
        char dateBuf[24];
        strftime(dateBuf, sizeof(dateBuf), "%a, %b %d %Y", &timeinfo);
        display.println(dateBuf);
    } else {
        display.setTextSize(1);
        display.setCursor(24, 28);
        display.println("NTP Syncing...");
    }
}

void DisplayManager::renderIdleWeather() {
    display.setTextSize(1);
    display.setCursor(10, 8);
    display.printf("%s Weather", weatherCity.c_str());
    display.drawFastHLine(10, 20, 108, SSD1306_WHITE);
    
    display.setTextSize(2);
    display.setCursor(12, 28);
    display.printf("%.1f C", weatherTemp);
    
    display.setTextSize(1);
    display.setCursor(12, 50);
    display.println(weatherCond.substring(0, 18));
}

void DisplayManager::renderListening() {
    display.setTextSize(1);
    display.setCursor(28, 8);
    display.println("LISTENING...");
    display.drawFastHLine(10, 20, 108, SSD1306_WHITE);
    
    // Simple visual mic waveform
    for (int i = 0; i < 9; i++) {
        int h = ((i % 3) + 1) * 8;
        display.fillRect(20 + i * 10, 42 - h / 2, 6, h, SSD1306_WHITE);
    }
    display.setCursor(24, 52);
    display.println("Speak for 3s");
}

void DisplayManager::renderThinking() {
    display.setTextSize(1);
    display.setCursor(30, 12);
    display.println("THINKING...");
    display.drawFastHLine(10, 24, 108, SSD1306_WHITE);
    
    static int anim = 0;
    anim = (anim + 1) % 4;
    display.setCursor(44, 40);
    if (anim == 0) display.println(".   ");
    else if (anim == 1) display.println("..  ");
    else if (anim == 2) display.println("... ");
    else display.println("....");
}

void DisplayManager::renderSpeaking() {
    display.setTextSize(1);
    display.setCursor(32, 10);
    display.println("SPEAKING...");
    display.drawFastHLine(10, 22, 108, SSD1306_WHITE);
    
    // Animated speaker soundwaves
    static int wavePhase = 0;
    wavePhase = (wavePhase + 1) % 5;
    for (int r = 1; r <= wavePhase; r++) {
        display.drawCircle(64, 44, r * 4, SSD1306_WHITE);
    }
}

void DisplayManager::renderError() {
    display.setTextSize(1);
    display.setCursor(44, 6);
    display.println("ERROR");
    display.drawFastHLine(10, 18, 108, SSD1306_WHITE);
    
    display.setCursor(6, 26);
    display.println(errorMsg.substring(0, 20));
    display.setCursor(6, 40);
    if (errorMsg.length() > 20) {
        display.println(errorMsg.substring(20, 40));
    }
    display.setCursor(14, 54);
    display.println("Press btn to retry");
}

void DisplayManager::renderDiagnostics() {
    display.setTextSize(1);
    display.setCursor(18, 4);
    display.println("HARDWARE DIAG");
    display.drawFastHLine(10, 15, 108, SSD1306_WHITE);
    
    display.setCursor(6, 20);
    display.println(diag1.substring(0, 20));
    display.setCursor(6, 34);
    display.println(diag2.substring(0, 20));
    display.setCursor(6, 48);
    display.println(diag3.substring(0, 20));
}
