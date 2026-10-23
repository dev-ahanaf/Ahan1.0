#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include "pins.h"

bool setupWifi();
bool isWifiConnected();
void checkWifiReconnect();
