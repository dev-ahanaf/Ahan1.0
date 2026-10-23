#pragma once
#include <Arduino.h>
#include <WiFiClient.h>
#include <driver/i2s.h>
#include "pins.h"

bool initAudioOut();
bool playWavStream(WiFiClient &stream, int volume_percent = 80);
bool writeAudioSamples(const uint8_t *pcm_bytes, size_t length, int volume_percent = 80);
void stopAudioPlayback();
void setAudioSampleRate(uint32_t sample_rate);
void playTestTone(int freqHz = 440, int durationMs = 500);
