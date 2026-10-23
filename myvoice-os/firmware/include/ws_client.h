#pragma once
#include <Arduino.h>

enum WsState {
    WS_STATE_DISCONNECTED = 0,
    WS_STATE_CONNECTED,
    WS_STATE_LISTENING,
    WS_STATE_THINKING,
    WS_STATE_SPEAKING
};

bool initWebSocketClient();
void loopWebSocketClient();
bool isWebSocketConnected();
WsState getWebSocketState();
void startVoiceStream();
void stopVoiceStream();
void triggerBargeInAbort();
size_t getDroppedFrames();
