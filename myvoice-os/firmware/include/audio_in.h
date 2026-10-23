#pragma once
#include <Arduino.h>
#include <LittleFS.h>
#include <driver/i2s.h>
#include "pins.h"

bool initAudioIn();
bool recordWav(const char *path = "/voice.wav", int gain_percent = 50);
size_t readMicSamples(int16_t *dest, size_t max_samples, int gain_percent = 50);
float measureMicRms(size_t sampleCount = 512);
