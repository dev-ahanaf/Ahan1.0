#include "audio_out.h"
#include <math.h>

static uint16_t readLE16(const uint8_t *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t readLE32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

bool initAudioOut() {
    i2s_config_t speakerConfig = {};
    speakerConfig.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
    speakerConfig.sample_rate = 24000;
    speakerConfig.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
    speakerConfig.channel_format = I2S_CHANNEL_FMT_ONLY_LEFT;
    speakerConfig.communication_format = I2S_COMM_FORMAT_STAND_I2S;
    speakerConfig.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
    speakerConfig.dma_buf_count = 6;
    speakerConfig.dma_buf_len = 256;
    speakerConfig.use_apll = false;
    speakerConfig.tx_desc_auto_clear = true;

    i2s_pin_config_t speakerPins = {};
    speakerPins.bck_io_num = SPK_BCLK;
    speakerPins.ws_io_num = SPK_WS;
    speakerPins.data_out_num = SPK_DATA;
    speakerPins.data_in_num = I2S_PIN_NO_CHANGE;

    esp_err_t err = i2s_driver_install(I2S_NUM_1, &speakerConfig, 0, nullptr);
    if (err != ESP_OK) {
        Serial.printf("[AudioOut] I2S1 driver install failed: 0x%x\n", err);
        return false;
    }
    err = i2s_set_pin(I2S_NUM_1, &speakerPins);
    if (err != ESP_OK) {
        Serial.printf("[AudioOut] I2S1 pin config failed: 0x%x\n", err);
        return false;
    }
    Serial.println("[AudioOut] MAX98357A amplifier initialized");
    return true;
}

bool playWavStream(WiFiClient &stream, int volume_percent) {
    stream.setTimeout(12000);
    uint8_t riffHeader[12];
    if (stream.readBytes((char*)riffHeader, 12) != 12 ||
        memcmp(riffHeader, "RIFF", 4) != 0 ||
        memcmp(riffHeader + 8, "WAVE", 4) != 0) {
        Serial.println("[AudioOut] Stream response is not RIFF/WAVE");
        return false;
    }

    uint16_t audioFormat = 0, channels = 0, depth = 0;
    uint32_t sampleRate = 0;
    bool fmtFound = false;
    uint32_t dataBytesLeft = 0;

    for (int part = 0; part < 16; part++) {
        uint8_t chunkHeader[8];
        if (stream.readBytes((char*)chunkHeader, 8) != 8) return false;
        uint32_t chunkLen = readLE32(chunkHeader + 4);

        if (memcmp(chunkHeader, "fmt ", 4) == 0) {
            if (chunkLen < 16 || chunkLen > 128) return false;
            uint8_t fmtBuf[128];
            if (stream.readBytes((char*)fmtBuf, chunkLen) != chunkLen) return false;
            audioFormat = readLE16(fmtBuf);
            channels = readLE16(fmtBuf + 2);
            sampleRate = readLE32(fmtBuf + 4);
            depth = readLE16(fmtBuf + 14);
            fmtFound = true;
        } else if (memcmp(chunkHeader, "data", 4) == 0) {
            dataBytesLeft = chunkLen;
            break;
        } else {
            if (chunkLen > 500000) return false;
            uint8_t skipBuf[128];
            uint32_t toSkip = chunkLen;
            while (toSkip > 0) {
                size_t step = min((uint32_t)sizeof(skipBuf), toSkip);
                if (stream.readBytes((char*)skipBuf, step) != step) return false;
                toSkip -= step;
            }
        }
        if ((chunkLen & 1) && stream.readBytes((char*)riffHeader, 1) != 1) return false;
    }

    if (!fmtFound || audioFormat != 1 || channels != 1 || depth != 16 ||
        sampleRate < 8000 || sampleRate > 48000 || dataBytesLeft == 0) {
        Serial.printf("[AudioOut] Unsupported WAV: fmt=%u chan=%u bits=%u hz=%lu bytes=%lu\n",
                      audioFormat, channels, depth, (unsigned long)sampleRate, (unsigned long)dataBytesLeft);
        return false;
    }

    i2s_set_clk(I2S_NUM_1, sampleRate, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_MONO);
    float volScale = (float)constrain(volume_percent, 0, 100) / 100.0f;
    Serial.printf("[AudioOut] Playing audio: %lu Hz, %lu bytes, vol: %d%%\n",
                  (unsigned long)sampleRate, (unsigned long)dataBytesLeft, volume_percent);

    int16_t buffer[512];
    while (dataBytesLeft > 0) {
        size_t toReadBytes = min((uint32_t)sizeof(buffer), dataBytesLeft);
        size_t actualBytes = stream.readBytes((char*)buffer, toReadBytes);
        if (actualBytes == 0) {
            Serial.println("[AudioOut] Speaker stream timeout");
            return false;
        }

        // Apply volume attenuation
        size_t sampleCount = actualBytes / sizeof(int16_t);
        for (size_t i = 0; i < sampleCount; i++) {
            buffer[i] = (int16_t)(buffer[i] * volScale);
        }

        size_t written = 0;
        esp_err_t res = i2s_write(I2S_NUM_1, buffer, actualBytes, &written, pdMS_TO_TICKS(1500));
        if (res != ESP_OK || written != actualBytes) return false;
        dataBytesLeft -= actualBytes;
    }

    i2s_zero_dma_buffer(I2S_NUM_1);
    return true;
}

void setAudioSampleRate(uint32_t sample_rate) {
    i2s_set_clk(I2S_NUM_1, sample_rate, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_MONO);
}

void stopAudioPlayback() {
    i2s_zero_dma_buffer(I2S_NUM_1);
}

bool writeAudioSamples(const uint8_t *pcm_bytes, size_t length, int volume_percent) {
    if (!pcm_bytes || length == 0) return true;

    float volScale = (float)constrain(volume_percent, 0, 100) / 100.0f;
    size_t sampleCount = length / sizeof(int16_t);
    int16_t buffer[256];

    for (size_t offset = 0; offset < sampleCount; offset += 256) {
        size_t count = min((size_t)256, sampleCount - offset);
        const int16_t *src = (const int16_t*)(pcm_bytes + offset * sizeof(int16_t));
        for (size_t i = 0; i < count; i++) {
            buffer[i] = (int16_t)(src[i] * volScale);
        }

        size_t written = 0;
        esp_err_t res = i2s_write(I2S_NUM_1, buffer, count * sizeof(int16_t), &written, pdMS_TO_TICKS(500));
        if (res != ESP_OK) return false;
    }
    return true;
}

void playTestTone(int freqHz, int durationMs) {
    i2s_set_clk(I2S_NUM_1, 16000, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_MONO);
    size_t totalSamples = (16000 * durationMs) / 1000;
    int16_t buffer[256];
    size_t writtenSamples = 0;

    while (writtenSamples < totalSamples) {
        size_t count = min((size_t)256, totalSamples - writtenSamples);
        for (size_t i = 0; i < count; i++) {
            float t = (float)(writtenSamples + i) / 16000.0f;
            buffer[i] = (int16_t)(16000.0f * sinf(2.0f * (float)M_PI * (float)freqHz * t));
        }
        size_t bytesWritten = 0;
        i2s_write(I2S_NUM_1, buffer, count * sizeof(int16_t), &bytesWritten, pdMS_TO_TICKS(200));
        writtenSamples += count;
    }
    i2s_zero_dma_buffer(I2S_NUM_1);
}
