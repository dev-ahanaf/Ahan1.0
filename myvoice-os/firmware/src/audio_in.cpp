#include "audio_in.h"
#include <math.h>

static void writeLE16(File &file, uint16_t v) {
    file.write((uint8_t)(v & 255));
    file.write((uint8_t)(v >> 8));
}

static void writeLE32(File &file, uint32_t v) {
    for (int i = 0; i < 4; i++) {
        file.write((uint8_t)(v >> (i * 8)));
    }
}

static void writeWavHeader(File &file, uint32_t dataSize) {
    file.write((const uint8_t*)"RIFF", 4);
    writeLE32(file, dataSize + 36);
    file.write((const uint8_t*)"WAVEfmt ", 8);
    writeLE32(file, 16);
    writeLE16(file, 1); // PCM format
    writeLE16(file, 1); // Mono
    writeLE32(file, RECORD_HZ);
    writeLE32(file, RECORD_HZ * 2);
    writeLE16(file, 2); // Block align
    writeLE16(file, 16); // Bits per sample
    file.write((const uint8_t*)"data", 4);
    writeLE32(file, dataSize);
}

bool initAudioIn() {
    i2s_config_t micConfig = {};
    micConfig.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
    micConfig.sample_rate = RECORD_HZ;
    micConfig.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
    micConfig.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT; // INMP441 L/R strapped to GND
    micConfig.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    micConfig.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    micConfig.dma_buf_count = 4;
    micConfig.dma_buf_len = 256;
    micConfig.use_apll = false;

    i2s_pin_config_t micPins = {};
    micPins.bck_io_num = MIC_BCLK;
    micPins.ws_io_num = MIC_WS;
    micPins.data_out_num = I2S_PIN_NO_CHANGE;
    micPins.data_in_num = MIC_DATA;

    esp_err_t err = i2s_driver_install(I2S_NUM_0, &micConfig, 0, nullptr);
    if (err != ESP_OK) {
        Serial.printf("[AudioIn] I2S0 driver install failed: 0x%x\n", err);
        return false;
    }
    err = i2s_set_pin(I2S_NUM_0, &micPins);
    if (err != ESP_OK) {
        Serial.printf("[AudioIn] I2S0 pin config failed: 0x%x\n", err);
        return false;
    }
    Serial.println("[AudioIn] INMP441 microphone initialized");
    return true;
}

bool recordWav(const char *path, int gain_percent) {
    File f = LittleFS.open(path, "w");
    if (!f) {
        Serial.printf("[AudioIn] Cannot open %s for writing\n", path);
        return false;
    }
    
    writeWavHeader(f, RECORD_SAMPLES * 2);
    static int32_t incoming[256];
    static int16_t samples[256];
    size_t written = 0;
    
    float gainMultiplier = (float)gain_percent / 50.0f; // 50% = 1.0x gain
    Serial.printf("[AudioIn] Recording 3 seconds with gain %.2fx...\n", gainMultiplier);
    
    while (written < RECORD_SAMPLES) {
        size_t bytesRead = 0;
        esp_err_t res = i2s_read(I2S_NUM_0, incoming, sizeof(incoming), &bytesRead, pdMS_TO_TICKS(1500));
        if (res != ESP_OK || bytesRead == 0) {
            f.close();
            LittleFS.remove(path);
            Serial.println("[AudioIn] Microphone read timeout");
            return false;
        }
        
        size_t count = min(bytesRead / sizeof(int32_t), RECORD_SAMPLES - written);
        for (size_t i = 0; i < count; i++) {
            // INMP441 left channel is 24-bit left-aligned in 32-bit slot
            int32_t raw = incoming[i] >> 14;
            int32_t scaled = (int32_t)(raw * gainMultiplier);
            if (scaled > 32767) scaled = 32767;
            if (scaled < -32768) scaled = -32768;
            samples[i] = (int16_t)scaled;
        }
        
        if (f.write((const uint8_t*)samples, count * 2) != count * 2) {
            f.close();
            LittleFS.remove(path);
            Serial.println("[AudioIn] LittleFS write failure");
            return false;
        }
        written += count;
    }
    
    f.close();
    Serial.printf("[AudioIn] Saved %s: %u samples\n", path, (unsigned)written);
    return true;
}

size_t readMicSamples(int16_t *dest, size_t max_samples, int gain_percent) {
    if (!dest || max_samples == 0) return 0;

    static int32_t raw_buf[256];
    float gainMultiplier = (float)gain_percent / 50.0f;
    size_t samplesReadTotal = 0;

    while (samplesReadTotal < max_samples) {
        size_t batch = min((size_t)256, max_samples - samplesReadTotal);
        size_t bytesRead = 0;
        esp_err_t res = i2s_read(I2S_NUM_0, raw_buf, batch * sizeof(int32_t), &bytesRead, pdMS_TO_TICKS(100));
        if (res != ESP_OK || bytesRead == 0) break;

        size_t count = bytesRead / sizeof(int32_t);
        for (size_t i = 0; i < count; i++) {
            int32_t raw = raw_buf[i] >> 14;
            int32_t scaled = (int32_t)(raw * gainMultiplier);
            if (scaled > 32767) scaled = 32767;
            if (scaled < -32768) scaled = -32768;
            dest[samplesReadTotal + i] = (int16_t)scaled;
        }
        samplesReadTotal += count;
        if (count < batch) break;
    }
    return samplesReadTotal;
}

float measureMicRms(size_t sampleCount) {
    int32_t buffer[128];
    double sumSquares = 0.0;
    size_t totalRead = 0;
    
    while (totalRead < sampleCount) {
        size_t bytesRead = 0;
        size_t desired = min((size_t)sizeof(buffer), (sampleCount - totalRead) * sizeof(int32_t));
        if (i2s_read(I2S_NUM_0, buffer, desired, &bytesRead, pdMS_TO_TICKS(200)) == ESP_OK && bytesRead > 0) {
            size_t count = bytesRead / sizeof(int32_t);
            for (size_t i = 0; i < count; i++) {
                int16_t s = (int16_t)(buffer[i] >> 14);
                sumSquares += (double)s * (double)s;
            }
            totalRead += count;
        } else {
            break;
        }
    }
    if (totalRead == 0) return 0.0f;
    return (float)sqrt(sumSquares / totalRead);
}
