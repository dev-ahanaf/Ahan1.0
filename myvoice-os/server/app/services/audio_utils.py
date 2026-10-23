"""Audio format conversion and DSP utilities for MyVoice OS."""
import io
import math
import struct
import wave

def pcm16_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Wrap raw signed 16-bit PCM bytes in a canonical WAV header."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()

def wav_to_pcm16(wav_data: bytes, target_sample_rate: int = 16000) -> bytes:
    """Extract raw signed 16-bit PCM samples from WAV, resampling if necessary."""
    try:
        import miniaudio
        decoded = miniaudio.decode(wav_data, nchannels=1, sample_rate=target_sample_rate)
        return decoded.samples.tobytes()
    except Exception:
        # Fallback to standard library wave reader
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        # If already mono 16-bit at target rate, return directly
        if channels == 1 and width == 2 and rate == target_sample_rate:
            return frames
        return frames

def resample_pcm16(pcm_data: bytes, from_rate: int, to_rate: int) -> bytes:
    """Resample 16-bit mono PCM audio using linear interpolation."""
    if from_rate == to_rate or len(pcm_data) < 2:
        return pcm_data

    sample_count = len(pcm_data) // 2
    samples = struct.unpack(f"<{sample_count}h", pcm_data)
    target_count = int(sample_count * (to_rate / from_rate))
    if target_count <= 0:
        return b""

    out_samples = []
    ratio = from_rate / to_rate
    for i in range(target_count):
        pos = i * ratio
        idx = int(pos)
        frac = pos - idx
        if idx + 1 < sample_count:
            sample = int(samples[idx] * (1.0 - frac) + samples[idx + 1] * frac)
        elif idx < sample_count:
            sample = samples[idx]
        else:
            sample = 0
        sample = max(-32768, min(32767, sample))
        out_samples.append(sample)

    return struct.pack(f"<{len(out_samples)}h", *out_samples)

def generate_pcm16_tone(freq_hz: float = 440.0, duration_ms: int = 200, sample_rate: int = 16000) -> bytes:
    """Generate a clean sinusoidal tone as signed 16-bit PCM audio."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    samples = []
    for i in range(num_samples):
        val = int(32767 * 0.3 * math.sin(2.0 * math.pi * freq_hz * (i / sample_rate)))
        samples.append(val)
    return struct.pack(f"<{len(samples)}h", *samples)

def calculate_rms_energy(pcm_frame: bytes) -> float:
    """Calculate Root Mean Square (RMS) energy of a 16-bit mono PCM frame."""
    sample_count = len(pcm_frame) // 2
    if sample_count == 0:
        return 0.0
    samples = struct.unpack(f"<{sample_count}h", pcm_frame)
    sum_squares = sum(s * s for s in samples)
    return math.sqrt(sum_squares / sample_count)

def detect_energy_vad(pcm_frame: bytes, threshold: float = 400.0) -> bool:
    """Energy-based voice activity detection for individual audio frames."""
    return calculate_rms_energy(pcm_frame) > threshold
