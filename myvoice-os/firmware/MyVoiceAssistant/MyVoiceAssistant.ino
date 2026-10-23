/*
 * =====================================================================================
 *                           MYVOICE OS - ESP32 VOICE ASSISTANT
 *                           Official Firmware (Arduino IDE & PlatformIO)
 * =====================================================================================
 * 
 * Hardware Requirements:
 *  - ESP32 Development Board (ESP32-WROOM-32 / DevKit v1)
 *  - INMP441 I2S MEMS Microphone
 *  - MAX98357A I2S Class D DAC / Amplifier + 3W Speaker
 *  - SSD1306 0.96" OLED Display (128x64 I2C) [Optional - will run without it]
 *  - Push-to-Talk Button (Built-in BOOT button GPIO 0 OR external button on GPIO 27)
 * 
 * Pinout Wiring:
 * ┌─────────────────┬──────────┬──────────────┬───────────────────────────────────────┐
 * │ Module          │ Pin Name │ ESP32 Pin    │ Power / Notes                         │
 * ├─────────────────┼──────────┼──────────────┼───────────────────────────────────────┤
 * │ INMP441 Mic     │ VDD      │ 3.3V         │ 3.3V power only                       │
 * │                 │ GND      │ GND          │ Common ground                         │
 * │                 │ SD       │ GPIO 33      │ Serial Data Out                       │
 * │                 │ WS       │ GPIO 25      │ Word Select (LRCL)                    │
 * │                 │ SCK      │ GPIO 26      │ Bit Clock (BCLK)                      │
 * │                 │ L/R      │ GND          │ Left channel                          │
 * ├─────────────────┼──────────┼──────────────┼───────────────────────────────────────┤
 * │ MAX98357A Amp   │ VIN      │ 5V / VIN     │ 5V power recommended for 3W output    │
 * │                 │ GND      │ GND          │ Common ground                         │
 * │                 │ DIN      │ GPIO 22      │ Serial Data In                        │
 * │                 │ BCLK     │ GPIO 14      │ Bit Clock                             │
 * │                 │ LRC      │ GPIO 13      │ Left/Right Clock (WS)                 │
 * │                 │ GAIN     │ GND          │ 9dB gain (or leave floating for 12dB) │
 * ├─────────────────┼──────────┼──────────────┼───────────────────────────────────────┤
 * │ SSD1306 OLED    │ VCC      │ 3.3V         │ 3.3V power                            │
 * │                 │ GND      │ GND          │ Common ground                         │
 * │                 │ SDA      │ GPIO 18      │ I2C Data (or 21)                      │
 * │                 │ SCL      │ GPIO 19      │ I2C Clock (or 22)                     │
 * ├─────────────────┼──────────┼──────────────┼───────────────────────────────────────┤
 * │ Button          │ Pin 1    │ GPIO 0 / 27  │ Internal Pull-Up enabled              │
 * │                 │ Pin 2    │ GND          │ Pressing connects pin to GND          │
 * └─────────────────┴──────────┴──────────────┴───────────────────────────────────────┘
 * =====================================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <WebSocketsClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <driver/i2s.h>
#include <time.h>

// =====================================================================================
//                             USER CONFIGURATION
// =====================================================================================

// 1. Wi-Fi Configuration:
// Set your Wi-Fi credentials here for instant connection.
// If left empty (""), the ESP32 starts an AP hotspot: "MyVoice-Setup" (pwd: myvoice123)
const char* WIFI_SSID     = ""; 
const char* WIFI_PASSWORD = "";

// 2. Server Configuration:
// Change this to your Mac/PC local LAN IP running MyVoice OS (e.g., "http://192.168.0.101:8000")
const char* SERVER_BASE_URL = "http://192.168.0.101:8000";

// Must match ENROLLMENT_KEY in server/.env
const char* ENROLLMENT_KEY  = "Pd1yEDahouFs43Pm8P-cCNWX5MGQKzYgm4-p0OO48os";

// Firmware Version
const char* FIRMWARE_VER    = "1.1.0";

// 3. Hardware Pin Definitions:
#define BUTTON_EXTERNAL_PIN 27   // External push button (GPIO 27 to GND)
#define BUTTON_BOOT_PIN     0    // ESP32 on-board BOOT button (GPIO 0 to GND)

// INMP441 Microphone (I2S Port 0)
#define MIC_I2S_PORT    I2S_NUM_0
#define MIC_BCLK_PIN    26
#define MIC_WS_PIN      25
#define MIC_DATA_PIN    33

// MAX98357A Amplifier (I2S Port 1)
#define SPK_I2S_PORT    I2S_NUM_1
#define SPK_BCLK_PIN    14
#define SPK_WS_PIN      13
#define SPK_DATA_PIN    22

// OLED Display (SSD1306 128x64)
#define SCREEN_WIDTH    128
#define SCREEN_HEIGHT   64
#define OLED_RESET      -1
#define OLED_I2C_ADDR   0x3C
#define OLED_SDA_PIN    18
#define OLED_SCL_PIN    19

// Audio Parameters
#define SAMPLE_RATE     16000
#define DMA_BUF_COUNT   4
#define DMA_BUF_LEN     256

// =====================================================================================
//                             GLOBAL OBJECTS & STATE
// =====================================================================================

Preferences prefs;
WebSocketsClient webSocket;
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

enum SystemState {
    STATE_BOOTING,
    STATE_CONNECTING_WIFI,
    STATE_PAIRING,
    STATE_IDLE_READY,
    STATE_LISTENING,
    STATE_THINKING,
    STATE_SPEAKING,
    STATE_ERROR
};

SystemState currentState = STATE_BOOTING;

String deviceMac = "";
String deviceToken = "";
String pairCode = "";
bool isPaired = false;
bool oledReady = false;
bool micReady = false;
bool spkReady = false;
bool isWsConnected = false;
bool isStreamingAudio = false;

unsigned long lastPollMs = 0;
unsigned long lastHeartbeatMs = 0;
unsigned long lastDisplayMs = 0;
int wavePhase = 0;
String currentAssistantName = "MyVoice";
String lastStatusMsg = "Starting up...";

// =====================================================================================
//                             DISPLAY HELPERS
// =====================================================================================

void initOLED() {
    Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
    if (display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR)) {
        oledReady = true;
        display.clearDisplay();
        display.setTextColor(SSD1306_WHITE);
        display.setTextSize(1);
        display.setCursor(18, 15);
        display.println("MyVoice OS");
        display.setCursor(20, 35);
        display.println("Initializing...");
        display.display();
        Serial.println("[OLED] SSD1306 128x64 display initialized.");
    } else {
        Serial.println("[OLED] Display not detected (continuing in headless mode).");
        oledReady = false;
    }
}

void updateOLED() {
    if (!oledReady) return;
    display.clearDisplay();

    // Top status bar
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.print("MyVoice");
    display.setCursor(85, 0);
    if (WiFi.status() == WL_CONNECTED) {
        display.print("WiFi ");
        int rssi = WiFi.RSSI();
        display.print(rssi > -65 ? "+++" : "+");
    } else {
        display.print("Offline");
    }
    display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

    switch (currentState) {
        case STATE_BOOTING:
        case STATE_CONNECTING_WIFI:
            display.setCursor(10, 22);
            display.print("Connecting WiFi...");
            display.setCursor(10, 36);
            display.print(WIFI_SSID[0] ? WIFI_SSID : "Setup AP");
            break;

        case STATE_PAIRING:
            display.setCursor(15, 16);
            display.print("DEVICE NOT PAIRED");
            display.setTextSize(2);
            display.setCursor(26, 30);
            display.print(pairCode);
            display.setTextSize(1);
            display.setCursor(10, 52);
            display.print("Enter code in Console");
            break;

        case STATE_IDLE_READY: {
            time_t now = time(nullptr);
            struct tm timeinfo;
            localtime_r(&now, &timeinfo);
            char timeBuf[16];
            strftime(timeBuf, sizeof(timeBuf), "%H:%M:%S", &timeinfo);

            display.setTextSize(2);
            display.setCursor(18, 20);
            display.print(timeBuf);

            display.setTextSize(1);
            display.setCursor(12, 45);
            display.print("Hold Button to Talk");
            break;
        }

        case STATE_LISTENING:
            display.setCursor(30, 20);
            display.print("LISTENING...");
            // Animated audio wave
            for (int i = 10; i < 118; i += 4) {
                int h = 4 + (int)(sin((i + wavePhase) * 0.2) * 8);
                display.drawLine(i, 48 - h, i, 48 + h, SSD1306_WHITE);
            }
            wavePhase += 3;
            break;

        case STATE_THINKING:
            display.setCursor(35, 25);
            display.print("Thinking...");
            // Dot animation
            for (int d = 0; d < 3; d++) {
                int cx = 50 + d * 14;
                int cy = 46 + (int)(sin((wavePhase + d * 2) * 0.4) * 5);
                display.fillCircle(cx, cy, 3, SSD1306_WHITE);
            }
            wavePhase++;
            break;

        case STATE_SPEAKING:
            display.setCursor(25, 18);
            display.print("AI Speaking...");
            // Voice spectrum bars
            for (int b = 15; b < 113; b += 8) {
                int barHeight = random(4, 24);
                display.fillRect(b, 58 - barHeight, 5, barHeight, SSD1306_WHITE);
            }
            break;

        case STATE_ERROR:
            display.setCursor(10, 22);
            display.print("Connection Error");
            display.setCursor(10, 36);
            display.print(lastStatusMsg);
            break;
    }

    display.display();
}

// =====================================================================================
//                             I2S AUDIO DRIVERS
// =====================================================================================

bool initAudioHardware() {
    // 1. Microphone setup (I2S RX)
    i2s_config_t micConfig = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = DMA_BUF_COUNT,
        .dma_buf_len = DMA_BUF_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };

    i2s_pin_config_t micPins = {
        .bck_io_num = MIC_BCLK_PIN,
        .ws_io_num = MIC_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = MIC_DATA_PIN
    };

    if (i2s_driver_install(MIC_I2S_PORT, &micConfig, 0, NULL) == ESP_OK &&
        i2s_set_pin(MIC_I2S_PORT, &micPins) == ESP_OK) {
        micReady = true;
        Serial.println("[Audio] INMP441 Microphone initialized.");
    } else {
        Serial.println("[Audio] Failed to initialize INMP441 microphone.");
    }

    // 2. Speaker setup (I2S TX)
    i2s_config_t spkConfig = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = 24000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 6,
        .dma_buf_len = DMA_BUF_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    i2s_pin_config_t spkPins = {
        .bck_io_num = SPK_BCLK_PIN,
        .ws_io_num = SPK_WS_PIN,
        .data_out_num = SPK_DATA_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    if (i2s_driver_install(SPK_I2S_PORT, &spkConfig, 0, NULL) == ESP_OK &&
        i2s_set_pin(SPK_I2S_PORT, &spkPins) == ESP_OK) {
        spkReady = true;
        Serial.println("[Audio] MAX98357A Speaker initialized.");
    } else {
        Serial.println("[Audio] Failed to initialize MAX98357A speaker.");
    }

    return micReady && spkReady;
}

void playBeepTone(int freqHz = 880, int durationMs = 120) {
    if (!spkReady) return;
    int samples = (24000 * durationMs) / 1000;
    int16_t sampleBuffer[128];
    float phase = 0;
    float phaseInc = 2.0 * PI * freqHz / 24000.0;

    int remaining = samples;
    while (remaining > 0) {
        int count = min(remaining, 128);
        for (int i = 0; i < count; i++) {
            sampleBuffer[i] = (int16_t)(sin(phase) * 6000.0);
            phase += phaseInc;
        }
        size_t bytesWritten = 0;
        i2s_write(SPK_I2S_PORT, sampleBuffer, count * sizeof(int16_t), &bytesWritten, portMAX_DELAY);
        remaining -= count;
    }
}

// =====================================================================================
//                             WEBSOCKET EVENT HANDLER
// =====================================================================================

void webSocketEvent(WStype_t type, uint8_t *payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            Serial.println("[WS] Disconnected from MyVoice server.");
            isWsConnected = false;
            if (isPaired) currentState = STATE_IDLE_READY;
            break;

        case WStype_CONNECTED:
            Serial.printf("[WS] Connected to: %s\n", payload);
            isWsConnected = true;
            currentState = STATE_IDLE_READY;
            playBeepTone(1200, 80);
            break;

        case WStype_TEXT: {
            DynamicJsonDocument doc(1024);
            DeserializationError err = deserializeJson(doc, payload, length);
            if (err) return;

            const char* msgType = doc["type"] | "";
            if (strcmp(msgType, "stt") == 0) {
                const char* text = doc["text"] | "";
                Serial.printf("[Voice STT] %s\n", text);
                currentState = STATE_THINKING;
            } else if (strcmp(msgType, "llm") == 0) {
                const char* text = doc["text"] | "";
                Serial.printf("[Voice AI] %s\n", text);
                currentState = STATE_SPEAKING;
            } else if (strcmp(msgType, "tts_end") == 0) {
                Serial.println("[Voice] Speech playback finished.");
                currentState = STATE_IDLE_READY;
            } else if (strcmp(msgType, "ota") == 0) {
                Serial.println("[OTA] Firmware update requested by server!");
            }
            break;
        }

        case WStype_BIN:
            // Direct PCM16 streaming chunk received from TTS
            if (spkReady && length > 0) {
                currentState = STATE_SPEAKING;
                size_t written = 0;
                i2s_write(SPK_I2S_PORT, payload, length, &written, portMAX_DELAY);
            }
            break;

        default:
            break;
    }
}

void connectWebSocket() {
    if (!isPaired || deviceToken.length() == 0) return;

    // Parse host and port from SERVER_BASE_URL
    String url = String(SERVER_BASE_URL);
    int protoIdx = url.indexOf("://");
    String hostPort = (protoIdx >= 0) ? url.substring(protoIdx + 3) : url;
    int colonIdx = hostPort.indexOf(':');
    int slashIdx = hostPort.indexOf('/');

    String host = (colonIdx >= 0) ? hostPort.substring(0, colonIdx) : hostPort;
    int port = 8000;
    if (colonIdx >= 0) {
        String portStr = (slashIdx >= 0) ? hostPort.substring(colonIdx + 1, slashIdx) : hostPort.substring(colonIdx + 1);
        port = portStr.toInt();
    }

    String wsPath = "/ws/device?device_id=" + deviceMac + "&token=" + deviceToken;
    Serial.printf("[WS] Connecting to ws://%s:%d%s\n", host.c_str(), port, wsPath.c_str());

    webSocket.begin(host.c_str(), port, wsPath.c_str());
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(3000);
}

// =====================================================================================
//                             REST API / BOOTSTRAP
// =====================================================================================

bool bootstrapDevice() {
    if (deviceToken.length() > 0) return true;

    HTTPClient http;
    String url = String(SERVER_BASE_URL) + "/api/device/bootstrap";
    http.begin(url);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Enrollment-Key", ENROLLMENT_KEY);

    DynamicJsonDocument req(256);
    req["device_id"] = deviceMac;
    req["firmware"] = FIRMWARE_VER;
    String reqBody;
    serializeJson(req, reqBody);

    int httpCode = http.POST(reqBody);
    if (httpCode == 200) {
        String resp = http.getString();
        DynamicJsonDocument doc(512);
        deserializeJson(doc, resp);

        deviceToken = doc["token"].as<String>();
        pairCode = doc["pair_code"].as<String>();

        prefs.putString("token", deviceToken);
        prefs.putString("paircode", pairCode);

        Serial.println("\n========================================================");
        Serial.printf("  [SUCCESS] DEVICE BOOTSTRAPPED!\n");
        Serial.printf("  PAIRING CODE: %s\n", pairCode.c_str());
        Serial.printf("  Enter this code at %s to pair your assistant.\n", SERVER_BASE_URL);
        Serial.println("========================================================\n");

        currentState = STATE_PAIRING;
        http.end();
        return true;
    } else {
        Serial.printf("[Bootstrap] HTTP failed with code %d\n", httpCode);
        http.end();
        return false;
    }
}

void checkPairStatus() {
    if (isPaired || deviceToken.length() == 0) return;

    HTTPClient http;
    String url = String(SERVER_BASE_URL) + "/api/device/status";
    http.begin(url);
    http.addHeader("X-Device-ID", deviceMac);
    http.addHeader("X-Device-Token", deviceToken);

    int code = http.GET();
    if (code == 200) {
        String body = http.getString();
        DynamicJsonDocument doc(512);
        deserializeJson(doc, body);

        if (doc["paired"].as<bool>()) {
            isPaired = true;
            prefs.putBool("paired", true);
            Serial.println("[System] Device successfully paired by user in console!");
            currentState = STATE_IDLE_READY;
            playBeepTone(980, 100);
            delay(120);
            playBeepTone(1320, 150);
            connectWebSocket();
        }
    }
    http.end();
}

void sendHeartbeat() {
    if (!isPaired || deviceToken.length() == 0) return;

    HTTPClient http;
    String url = String(SERVER_BASE_URL) + "/api/device/heartbeat";
    http.begin(url);
    http.addHeader("X-Device-ID", deviceMac);
    http.addHeader("X-Device-Token", deviceToken);

    int code = http.GET();
    if (code == 200) {
        // Serial.println("[Heartbeat] OK");
    }
    http.end();
}

// =====================================================================================
//                             BUTTON & VOICE CYCLE
// =====================================================================================

bool isButtonPressed() {
    return (digitalRead(BUTTON_EXTERNAL_PIN) == LOW) || (digitalRead(BUTTON_BOOT_PIN) == LOW);
}

void streamVoiceAudio() {
    if (!isWsConnected) return;

    Serial.println("[Voice] User pressed button: Starting real-time stream...");
    playBeepTone(800, 60);

    // Send start frame
    webSocket.sendTXT("{\"type\":\"listen_start\",\"format\":\"pcm16\",\"sample_rate\":16000}");
    currentState = STATE_LISTENING;

    const size_t CHUNK_SAMPLES = 512;
    int32_t micRaw32[CHUNK_SAMPLES];
    int16_t pcm16[CHUNK_SAMPLES];

    while (isButtonPressed()) {
        size_t bytesRead = 0;
        if (micReady) {
            i2s_read(MIC_I2S_PORT, micRaw32, CHUNK_SAMPLES * sizeof(int32_t), &bytesRead, 100);
            int samples = bytesRead / sizeof(int32_t);
            for (int i = 0; i < samples; i++) {
                pcm16[i] = (int16_t)(micRaw32[i] >> 14); // Scale 24-bit to 16-bit
            }
            webSocket.sendBIN((uint8_t*)pcm16, samples * sizeof(int16_t));
        } else {
            // Simulated voice test sine wave if mic hardware is not yet attached
            for (int i = 0; i < 128; i++) {
                pcm16[i] = (int16_t)(sin(i * 0.2) * 5000);
            }
            webSocket.sendBIN((uint8_t*)pcm16, 128 * sizeof(int16_t));
            delay(16);
        }

        webSocket.loop();
        updateOLED();
        delay(2);
    }

    Serial.println("[Voice] Button released: Sending listen_stop...");
    webSocket.sendTXT("{\"type\":\"listen_stop\"}");
    currentState = STATE_THINKING;
    playBeepTone(1100, 60);
}

// =====================================================================================
//                             ARDUINO SETUP & LOOP
// =====================================================================================

void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n\n========================================================");
    Serial.println("         MYVOICE OS - ESP32 SMART ASSISTANT             ");
    Serial.printf("         Firmware: v%s\n", FIRMWARE_VER);
    Serial.println("========================================================");

    // Setup buttons with internal pull-up
    pinMode(BUTTON_EXTERNAL_PIN, INPUT_PULLUP);
    pinMode(BUTTON_BOOT_PIN, INPUT_PULLUP);

    initOLED();
    initAudioHardware();

    prefs.begin("myvoice", false);
    deviceToken = prefs.getString("token", "");
    pairCode = prefs.getString("paircode", "");
    isPaired = prefs.getBool("paired", false);

    // Setup Wi-Fi
    currentState = STATE_CONNECTING_WIFI;
    updateOLED();

    deviceMac = WiFi.macAddress();
    Serial.printf("[System] Device MAC: %s\n", deviceMac.c_str());

    if (strlen(WIFI_SSID) > 0) {
        Serial.printf("[WiFi] Connecting to '%s'...\n", WIFI_SSID);
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 30) {
            delay(500);
            Serial.print(".");
            attempts++;
        }
        Serial.println();
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
        configTime(6 * 3600, 0, "pool.ntp.org", "time.google.com");
    } else {
        Serial.println("[WiFi] Not connected to AP. Starting setup mode...");
        WiFi.mode(WIFI_AP_STA);
        WiFi.softAP("MyVoice-Setup", "myvoice123");
        Serial.printf("[WiFi] Provisioning AP active. Connect to 'MyVoice-Setup' (pwd: myvoice123) at 192.168.4.1\n");
    }

    // Check pairing or bootstrap
    if (!isPaired) {
        bootstrapDevice();
    } else {
        currentState = STATE_IDLE_READY;
        connectWebSocket();
    }
}

void loop() {
    webSocket.loop();

    unsigned long now = millis();

    // 1. OLED Refresh loop (30 FPS)
    if (now - lastDisplayMs >= 35) {
        lastDisplayMs = now;
        updateOLED();
    }

    // 2. Poll for device claim if unpaired
    if (!isPaired && (now - lastPollMs >= 3000)) {
        lastPollMs = now;
        checkPairStatus();
    }

    // 3. Heartbeat keepalive every 30 seconds
    if (isPaired && (now - lastHeartbeatMs >= 30000)) {
        lastHeartbeatMs = now;
        sendHeartbeat();
    }

    // 4. Voice push-to-talk button detection
    if (isPaired && isButtonPressed()) {
        delay(30); // Debounce
        if (isButtonPressed()) {
            if (currentState == STATE_SPEAKING || currentState == STATE_THINKING) {
                // User barge-in interrupt
                Serial.println("[Voice] Barge-in abort triggered!");
                webSocket.sendTXT("{\"type\":\"abort\"}");
                currentState = STATE_IDLE_READY;
                while (isButtonPressed()) delay(10);
            } else {
                streamVoiceAudio();
            }
        }
    }

    delay(2);
}
