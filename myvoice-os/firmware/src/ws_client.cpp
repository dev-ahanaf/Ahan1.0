#include "ws_client.h"
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "config_store.h"
#include "display.h"
#include "audio_in.h"
#include "audio_out.h"
#include "pins.h"

static WebSocketsClient s_wsClient;
static WsState s_wsState = WS_STATE_DISCONNECTED;
static bool s_connected = false;
static size_t s_droppedFrames = 0;
static int16_t s_micFrame[960]; // 60 ms @ 16 kHz mono = 960 samples = 1920 bytes

static void parseServerUrl(String fullUrl, String &host, uint16_t &port) {
    host = "192.168.1.100";
    port = 8000;

    int protoIdx = fullUrl.indexOf("://");
    String rest = (protoIdx >= 0) ? fullUrl.substring(protoIdx + 3) : fullUrl;

    int slashIdx = rest.indexOf('/');
    String hostPort = (slashIdx >= 0) ? rest.substring(0, slashIdx) : rest;

    int colonIdx = hostPort.indexOf(':');
    if (colonIdx >= 0) {
        host = hostPort.substring(0, colonIdx);
        port = (uint16_t)hostPort.substring(colonIdx + 1).toInt();
    } else {
        host = hostPort;
        port = 80;
    }
}

static void onWebSocketEvent(WStype_t type, uint8_t *payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            s_connected = false;
            s_wsState = WS_STATE_DISCONNECTED;
            Serial.println("[WS] Disconnected from server");
            break;

        case WStype_CONNECTED: {
            s_connected = true;
            s_wsState = WS_STATE_CONNECTED;
            Serial.printf("[WS] Connected to %s\n", (char*)payload);

            // Send initial hello handshake
            StaticJsonDocument<256> hello;
            hello["type"] = "hello";
            hello["firmware"] = DEVICE_FW_VERSION;
            JsonObject audio = hello.createNestedObject("audio");
            audio["codec"] = "pcm16";
            audio["sample_rate"] = 16000;
            audio["channels"] = 1;
            audio["frame_ms"] = 60;

            String out;
            serializeJson(hello, out);
            s_wsClient.sendTXT(out);
            break;
        }

        case WStype_TEXT: {
            StaticJsonDocument<512> doc;
            DeserializationError err = deserializeJson(doc, payload, length);
            if (err) return;

            const char *mtype = doc["type"] | "";
            if (strcmp(mtype, "hello_ack") == 0) {
                Serial.printf("[WS] Handshake ACK: session=%s\n", (const char*)(doc["session_id"] | ""));
            } else if (strcmp(mtype, "config_update") == 0) {
                Serial.println("[WS] Received dynamic configuration update");
            } else if (strcmp(mtype, "stt") == 0) {
                const char *text = doc["text"] | "";
                Serial.printf("[WS] STT Transcript: %s\n", text);
            } else if (strcmp(mtype, "tts_start") == 0) {
                setAudioSampleRate(16000);
                s_wsState = WS_STATE_SPEAKING;
                DisplayManager::instance().setState(DisplayState::SPEAKING);
            } else if (strcmp(mtype, "tts_stop") == 0) {
                stopAudioPlayback();
                s_wsState = WS_STATE_CONNECTED;
                DisplayManager::instance().setState(DisplayState::IDLE_CLOCK);
            } else if (strcmp(mtype, "abort_ack") == 0) {
                stopAudioPlayback();
                s_wsState = WS_STATE_CONNECTED;
                DisplayManager::instance().setState(DisplayState::IDLE_CLOCK);
            } else if (strcmp(mtype, "display") == 0) {
                const char *screen = doc["screen"] | "";
                JsonObject data = doc["data"];
                if (strcmp(screen, "weather") == 0) {
                    const char *city = data["city"] | "Dhaka";
                    float temp = data["temp"] | 25.0;
                    const char *cond = data["condition"] | "Clear";
                    DisplayManager::instance().setWeatherInfo(city, temp, cond);
                    DisplayManager::instance().setState(DisplayState::IDLE_WEATHER);
                } else if (strcmp(screen, "clock") == 0) {
                    DisplayManager::instance().setState(DisplayState::IDLE_CLOCK);
                }
            } else if (strcmp(mtype, "alert") == 0) {
                const char *alertId = doc["id"] | "";
                const char *kind = doc["kind"] | "timer";
                const char *label = doc["label"] | "Alert";
                Serial.printf("[WS] Alert received: kind=%s, label=%s\n", kind, label);
                if (strlen(alertId) > 0) {
                    StaticJsonDocument<128> ack;
                    ack["type"] = "alert_ack";
                    ack["id"] = alertId;
                    String out;
                    serializeJson(ack, out);
                    s_wsClient.sendTXT(out);
                }
            } else if (strcmp(mtype, "reboot") == 0) {
                Serial.println("[WS] Remote reboot command received. Rebooting...");
                delay(200);
                ESP.restart();
            } else if (strcmp(mtype, "reset_wifi") == 0) {
                Serial.println("[WS] Reset Wi-Fi command received. Clearing Wi-Fi credentials and rebooting...");
                WiFi.disconnect(true, true);
                delay(200);
                ESP.restart();
            }
            break;
        }

        case WStype_BIN: {
            if (s_wsState == WS_STATE_SPEAKING) {
                int vol = ConfigStore::instance().getConfig().speaker_volume;
                bool ok = writeAudioSamples(payload, length, vol);
                if (!ok) {
                    s_droppedFrames++;
                }
            }
            break;
        }

        default:
            break;
    }
}

bool initWebSocketClient() {
    if (!ConfigStore::instance().isPaired()) {
        return false;
    }

    String host;
    uint16_t port;
    parseServerUrl(API_BASE_URL, host, port);

    String deviceId = ConfigStore::instance().getDeviceId();
    String token = ConfigStore::instance().getDeviceToken();
    String path = "/ws/device?device_id=" + deviceId + "&token=" + token;

    Serial.printf("[WS] Initializing ws://%s:%u%s\n", host.c_str(), port, path.c_str());
    s_wsClient.begin(host.c_str(), port, path.c_str());
    s_wsClient.onEvent(onWebSocketEvent);
    s_wsClient.setReconnectInterval(5000);
    s_wsClient.enableHeartbeat(15000, 3000, 2);
    return true;
}

void loopWebSocketClient() {
    s_wsClient.loop();

    // Periodic 30-second telemetry status report
    static unsigned long s_lastTelemetryMs = 0;
    if (s_connected && (millis() - s_lastTelemetryMs >= 30000)) {
        s_lastTelemetryMs = millis();
        StaticJsonDocument<256> tel;
        tel["type"] = "status_report";
        tel["rssi"] = WiFi.RSSI();
        tel["free_heap"] = ESP.getFreeHeap();
        tel["min_free_heap"] = ESP.getMinFreeHeap();
        tel["uptime_s"] = millis() / 1000;
        tel["dropped_frames"] = s_droppedFrames;
        tel["error_count"] = 0;
        String out;
        serializeJson(tel, out);
        s_wsClient.sendTXT(out);
    }

    // Stream microphone PCM16 frames when in listening state
    if (s_wsState == WS_STATE_LISTENING && s_connected) {
        int gain = ConfigStore::instance().getConfig().mic_gain;
        size_t samples = readMicSamples(s_micFrame, 960, gain);
        if (samples == 960) {
            s_wsClient.sendBIN((const uint8_t*)s_micFrame, 960 * sizeof(int16_t));
        }
    }
}


bool isWebSocketConnected() {
    return s_connected;
}

WsState getWebSocketState() {
    return s_wsState;
}

void startVoiceStream() {
    if (!s_connected) return;
    s_wsState = WS_STATE_LISTENING;
    DisplayManager::instance().setState(DisplayState::LISTENING);
    s_wsClient.sendTXT("{\"type\": \"listen_start\", \"mode\": \"manual\"}");
}

void stopVoiceStream() {
    if (!s_connected) return;
    s_wsState = WS_STATE_THINKING;
    DisplayManager::instance().setState(DisplayState::THINKING);
    s_wsClient.sendTXT("{\"type\": \"listen_stop\"}");
}

void triggerBargeInAbort() {
    stopAudioPlayback();
    if (s_connected) {
        s_wsClient.sendTXT("{\"type\": \"abort\", \"reason\": \"user_interrupt\"}");
    }
    s_wsState = WS_STATE_CONNECTED;
    DisplayManager::instance().setState(DisplayState::IDLE_CLOCK);
}

size_t getDroppedFrames() {
    return s_droppedFrames;
}
