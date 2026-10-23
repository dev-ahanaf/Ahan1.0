#!/usr/bin/env python3
"""MyVoice OS ESP32 Hardware Simulator.

Simulates the complete ESP32 device lifecycle over HTTP without requiring
physical hardware: bootstrap, pairing, heartbeats, configuration syncing,
push-to-talk WAV uploading, and response playback caching.
"""

import argparse
import io
import json
import math
import os
import struct
import sys
import time
import wave
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin
import httpx

DEFAULT_SERVER = "http://127.0.0.1:8000"
CREDS_FILE = Path(__file__).resolve().parent / ".simulator_creds.json"

def generate_test_wav(duration_s=3, sample_rate=16000, freq=440.0) -> bytes:
    """Generate a valid 16 kHz, 16-bit mono PCM sine wave RIFF/WAV."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        num_samples = int(duration_s * sample_rate)
        samples = []
        for i in range(num_samples):
            t = float(i) / sample_rate
            val = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * freq * t))
            samples.append(struct.pack("<h", val))
        wav.writeframes(b"".join(samples))
    return buf.getvalue()

class ESP32Simulator:
    def __init__(self, server_url: str, enrollment_key: str, device_id: str = "FA:1E:CA:0A:DE:F1"):
        self.server_url = server_url.rstrip("/")
        self.enrollment_key = enrollment_key
        self.device_id = device_id
        self.token = None
        self.pair_code = None
        self.paired = False
        self.config_version = 1
        self.config = {}
        self.load_creds()

    def load_creds(self):
        if CREDS_FILE.exists():
            try:
                data = json.loads(CREDS_FILE.read_text())
                if data.get("device_id") == self.device_id:
                    self.token = data.get("token")
                    self.paired = data.get("paired", False)
                    self.config_version = data.get("config_version", 1)
            except Exception:
                pass

    def save_creds(self):
        CREDS_FILE.write_text(json.dumps({
            "device_id": self.device_id,
            "token": self.token,
            "paired": self.paired,
            "config_version": self.config_version
        }, indent=2))

    def auth_headers(self) -> dict:
        if not self.token:
            raise RuntimeError("Device token missing. Run bootstrap first.")
        return {
            "X-Device-ID": self.device_id,
            "X-Device-Token": self.token
        }

    def bootstrap(self, firmware="0.1.0") -> dict:
        """Register device with server using shared enrollment key."""
        url = f"{self.server_url}/api/device/bootstrap"
        headers = {
            "Content-Type": "application/json",
            "X-Enrollment-Key": self.enrollment_key
        }
        payload = {
            "device_id": self.device_id,
            "firmware": firmware
        }
        with httpx.Client(timeout=10) as client:
            res = client.post(url, json=payload, headers=headers)
            if res.status_code == 409:
                print(f"[Simulator] Device {self.device_id} already registered and paired.")
                self.paired = True
                self.save_creds()
                return {"paired": True}
            res.raise_for_status()
            data = res.json()
            self.token = data["token"]
            self.pair_code = data["pair_code"]
            self.paired = False
            self.save_creds()
            print(f"[Simulator] Bootstrap success!")
            print(f"  Device ID: {self.device_id}")
            print(f"  Pairing Code: {self.pair_code} (valid for 10 minutes)")
            return data

    def poll_status(self) -> dict:
        """Poll pairing status."""
        url = f"{self.server_url}/api/device/status"
        with httpx.Client(timeout=10) as client:
            res = client.get(url, headers=self.auth_headers())
            res.raise_for_status()
            data = res.json()
            self.paired = data.get("paired", False)
            if data.get("pair_code"):
                self.pair_code = data["pair_code"]
            self.save_creds()
            return data

    def heartbeat(self, free_heap=184512, wifi_rssi=-54) -> dict:
        """Send keepalive heartbeat and check for config_version updates."""
        url = f"{self.server_url}/api/device/heartbeat"
        payload = {"free_heap": free_heap, "wifi_rssi": wifi_rssi}
        with httpx.Client(timeout=10) as client:
            res = client.post(url, json=payload, headers=self.auth_headers())
            res.raise_for_status()
            data = res.json()
            server_version = data.get("config_version", 1)
            print(f"[Simulator] Heartbeat OK. Server UTC: {data.get('server_utc')}, config_version: {server_version}")
            if server_version > self.config_version:
                print(f"[Simulator] Detected config update (v{self.config_version} -> v{server_version}). Fetching config...")
                self.fetch_config()
            return data

    def fetch_config(self) -> dict:
        """Fetch updated configuration settings."""
        url = f"{self.server_url}/api/device/config"
        with httpx.Client(timeout=10) as client:
            res = client.get(url, headers=self.auth_headers())
            res.raise_for_status()
            data = res.json()
            self.config = data
            self.config_version = data.get("config_version", self.config_version)
            self.save_creds()
            print(f"[Simulator] Config updated successfully: {json.dumps(data, indent=2)}")
            return data

    def send_voice(self, wav_bytes: bytes = None, output_path: str = "simulator_reply.wav") -> bytes:
        """Upload push-to-talk WAV and save response WAV."""
        if wav_bytes is None:
            print("[Simulator] Generating 3-second 16 kHz test audio...")
            wav_bytes = generate_test_wav(duration_s=3, sample_rate=16000)
            
        url = f"{self.server_url}/api/device/voice"
        headers = {
            **self.auth_headers(),
            "Content-Type": "audio/wav"
        }
        print(f"[Simulator] Uploading {len(wav_bytes)} bytes WAV to {url}...")
        with httpx.Client(timeout=90) as client:
            res = client.post(url, content=wav_bytes, headers=headers)
            if res.status_code != 200:
                print(f"[Simulator] Voice error {res.status_code}: {res.text}")
                res.raise_for_status()
            reply_wav = res.content
            print(f"[Simulator] Received {len(reply_wav)} bytes response audio!")
            Path(output_path).write_bytes(reply_wav)
            print(f"[Simulator] Spoken reply saved to {output_path}")
            return reply_wav

    def claim_via_admin(self, admin_password: str, name: str = "Simulated ESP32") -> dict:
        """Admin helper to claim pairing code directly."""
        if not self.pair_code:
            raise RuntimeError("No active pairing code to claim.")
        url = f"{self.server_url}/api/admin/claim"
        with httpx.Client(timeout=10) as client:
            res = client.post(
                url,
                json={"code": self.pair_code, "name": name},
                auth=("admin", admin_password)
            )
            res.raise_for_status()
            data = res.json()
            self.paired = True
            self.save_creds()
            print(f"[Simulator] Claimed successfully by admin! Name: {name}")
            return data

    def ws_url(self) -> str:
        """Derive ws:// or wss:// URL from http server URL."""
        base = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        return f"{base}/ws/device?device_id={self.device_id}&token={self.token}"

    async def run_ws_voice_cycle(
        self,
        wav_input_path: Optional[str] = None,
        output_path: str = "simulator_ws_reply.wav",
        abort_during_speech: bool = False
    ) -> dict:
        """Run real-time WebSocket bidirectional streaming session."""
        import asyncio
        import websockets

        if not self.token:
            raise RuntimeError("Device token missing. Run bootstrap first.")

        url = self.ws_url()
        print(f"[Simulator-WS] Connecting to {url}...")

        t_conn_start = time.time()
        metrics = {
            "conn_setup_ms": 0,
            "stt_ms": 0,
            "llm_first_token_ms": 0,
            "tts_first_audio_ms": 0,
            "total_turnaround_ms": 0,
            "bytes_received": 0,
            "stt_text": "",
            "llm_text": ""
        }

        async with websockets.connect(url) as ws:
            metrics["conn_setup_ms"] = int((time.time() - t_conn_start) * 1000)
            print(f"[Simulator-WS] Connected in {metrics['conn_setup_ms']} ms.")

            # Send hello frame
            hello_msg = {
                "type": "hello",
                "firmware": "1.0.0",
                "audio": {"codec": "pcm16", "sample_rate": 16000, "channels": 1, "frame_ms": 60}
            }
            await ws.send(json.dumps(hello_msg))
            resp = await ws.recv()
            hello_ack = json.loads(resp)
            print(f"[Simulator-WS] Handshake established. Session ID: {hello_ack.get('session_id')}")

            # Send listen_start
            await ws.send(json.dumps({"type": "listen_start", "mode": "manual"}))
            print("[Simulator-WS] Sent listen_start. Streaming PCM16 audio frames...")

            # Prepare audio frames: 60 ms at 16 kHz = 960 samples = 1,920 bytes
            raw_pcm = None
            if wav_input_path and Path(wav_input_path).exists():
                wav_bytes = Path(wav_input_path).read_bytes()
                # Skip 44 byte RIFF header if present
                raw_pcm = wav_bytes[44:] if wav_bytes.startswith(b"RIFF") else wav_bytes
            else:
                wav_bytes = generate_test_wav(duration_s=2, sample_rate=16000, freq=440.0)
                raw_pcm = wav_bytes[44:]

            frame_size = 1920
            t_stream_start = time.time()
            for i in range(0, len(raw_pcm), frame_size):
                chunk = raw_pcm[i:i + frame_size]
                if len(chunk) < frame_size:
                    chunk = chunk + b"\x00" * (frame_size - len(chunk))
                await ws.send(chunk)
                await asyncio.sleep(0.015)  # Accelerated real-time upload

            print(f"[Simulator-WS] Streamed {len(raw_pcm)} bytes. Sending listen_stop...")
            t_listen_stop = time.time()
            await ws.send(json.dumps({"type": "listen_stop"}))

            # Receive events from server
            received_audio = bytearray()
            llm_tokens = []
            aborted = False

            while True:
                msg = await ws.recv()
                if isinstance(msg, bytes):
                    received_audio.extend(msg)
                    metrics["bytes_received"] += len(msg)
                    if metrics["tts_first_audio_ms"] == 0:
                        metrics["tts_first_audio_ms"] = int((time.time() - t_listen_stop) * 1000)

                    if abort_during_speech and len(received_audio) > 4000 and not aborted:
                        print("\n[Simulator-WS] Simulating user barge-in! Sending abort...")
                        await ws.send(json.dumps({"type": "abort", "reason": "user_interrupt"}))
                        aborted = True

                elif isinstance(msg, str):
                    event = json.loads(msg)
                    etype = event.get("type")

                    if etype == "stt":
                        metrics["stt_ms"] = int((time.time() - t_listen_stop) * 1000)
                        metrics["stt_text"] = event.get("text", "")
                        print(f"\n[Simulator-WS] STT Transcript ({metrics['stt_ms']} ms): '{metrics['stt_text']}'")

                    elif etype == "llm":
                        if metrics["llm_first_token_ms"] == 0:
                            metrics["llm_first_token_ms"] = int((time.time() - t_listen_stop) * 1000)
                        delta = event.get("delta", "")
                        llm_tokens.append(delta)
                        sys.stdout.write(delta)
                    elif etype == "display":
                        screen = event.get("screen", "clock")
                        data = event.get("data", {})
                        print(f"\n[Simulator-OLED] Display Frame: screen='{screen}', data={data}")

                    elif etype == "alert":
                        kind = event.get("kind", "timer")
                        label = event.get("label", "Timer")
                        text = event.get("text", "")
                        alert_id = event.get("id")
                        print(f"\n[Simulator-Alert] Alert Received: kind='{kind}', label='{label}', text='{text}'")
                        if alert_id:
                            await ws.send(json.dumps({"type": "alert_ack", "id": alert_id}))
                            print(f"[Simulator-Alert] Sent alert_ack for id: {alert_id}")

                    elif etype == "ota":
                        version = event.get("version")
                        url = event.get("url")
                        expected_hash = event.get("sha256")
                        size = event.get("size")
                        print(f"\n[Simulator-OTA] OTA Command: version='{version}', size={size} B, expected_hash={expected_hash}")
                        # Simulate binary download and SHA-256 verification
                        try:
                            download_url = f"{self.server_url.rstrip('/')}{url}"
                            print(f"[Simulator-OTA] Downloading from {download_url}...")
                            res = self.client.get(download_url)
                            if res.status_code == 200:
                                downloaded_hash = hashlib.sha256(res.content).hexdigest()
                                if downloaded_hash == expected_hash:
                                    print(f"[Simulator-OTA] SHA-256 VERIFIED: {downloaded_hash}. Simulated flash update SUCCESSFUL.")
                                else:
                                    print(f"[Simulator-OTA] SHA-256 MISMATCH! Expected {expected_hash}, got {downloaded_hash}")
                            else:
                                print(f"[Simulator-OTA] Download failed with HTTP {res.status_code}")
                        except Exception as ota_err:
                            print(f"[Simulator-OTA] Download error: {ota_err}")

                    elif etype == "tts_start":
                        print(f"\n[Simulator-WS] Receiving TTS audio stream...")

                    elif etype == "tts_stop":
                        metrics["total_turnaround_ms"] = int((time.time() - t_listen_stop) * 1000)
                        print(f"\n[Simulator-WS] TTS playback complete.")
                        break

                    elif etype == "abort_ack":
                        print("\n[Simulator-WS] Server acknowledged abort. Stream halted cleanly.")
                        break

                    elif etype == "error":
                        print(f"\n[Simulator-WS] Error received from server: {event.get('message')}")
                        break

            metrics["llm_text"] = "".join(llm_tokens)


            # Save received audio as playable WAV
            if received_audio:
                out_buf = io.BytesIO()
                with wave.open(out_buf, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(bytes(received_audio))
                Path(output_path).write_bytes(out_buf.getvalue())
                print(f"[Simulator-WS] Saved {len(received_audio)} audio bytes to {output_path}")

            return metrics

def main():
    parser = argparse.ArgumentParser(description="MyVoice OS ESP32 Device Simulator")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Server base URL")
    parser.add_argument("--enrollment-key", default=os.getenv("ENROLLMENT_KEY", "test-strong-enrollment-key-123456"), help="Shared enrollment key")
    parser.add_argument("--device-id", default="FA:1E:CA:0A:DE:F1", help="Device MAC address")
    parser.add_argument("--action", choices=["bootstrap", "status", "heartbeat", "config", "voice", "full-cycle", "ws-voice", "ws-cycle"], default="ws-cycle", help="Action to perform")
    parser.add_argument("--admin-password", default=os.getenv("ADMIN_PASSWORD", ""), help="Admin password for auto-claiming")
    parser.add_argument("--wav-in", help="Input WAV file for voice test")
    parser.add_argument("--wav-out", default="simulator_reply.wav", help="Output path for received WAV")
    parser.add_argument("--abort-test", action="store_true", help="Simulate button barge-in during speech playback")

    args = parser.parse_args()
    sim = ESP32Simulator(args.server, args.enrollment_key, args.device_id)

    if args.action == "bootstrap":
        sim.bootstrap()
    elif args.action == "status":
        status = sim.poll_status()
        print(json.dumps(status, indent=2))
    elif args.action == "heartbeat":
        hb = sim.heartbeat()
        print(json.dumps(hb, indent=2))
    elif args.action == "config":
        cfg = sim.fetch_config()
        print(json.dumps(cfg, indent=2))
    elif args.action == "voice":
        wav_data = Path(args.wav_in).read_bytes() if args.wav_in else None
        sim.send_voice(wav_data, args.wav_out)
    elif args.action == "ws-voice":
        import asyncio
        asyncio.run(sim.run_ws_voice_cycle(args.wav_in, args.wav_out, abort_during_speech=args.abort_test))
    elif args.action in ("full-cycle", "ws-cycle"):
        print("=== Step 1: Bootstrapping Device ===")
        b = sim.bootstrap()
        if not sim.paired and args.admin_password and sim.pair_code:
            print("\n=== Step 2: Auto-Claiming Device via Admin Credentials ===")
            sim.claim_via_admin(args.admin_password)
            
        print("\n=== Step 3: Checking Device Status ===")
        st = sim.poll_status()
        print(f"Paired: {st.get('paired')}, Name: {st.get('name')}")
        
        if sim.paired:
            print("\n=== Step 4: Sending Heartbeat ===")
            sim.heartbeat()
            print("\n=== Step 5: Fetching Initial Config ===")
            sim.fetch_config()
            
            if args.action == "ws-cycle":
                print("\n=== Step 6: Testing Real-Time WebSocket Streaming ===")
                import asyncio
                metrics = asyncio.run(sim.run_ws_voice_cycle(
                    args.wav_in,
                    args.wav_out,
                    abort_during_speech=args.abort_test
                ))
                print("\n================ LATENCY METRICS ================")
                print(f"WebSocket Setup Time:       {metrics['conn_setup_ms']} ms")
                print(f"STT Latency:                {metrics['stt_ms']} ms")
                print(f"LLM Time to First Token:    {metrics['llm_first_token_ms']} ms")
                print(f"TTS Time to First Audio:    {metrics['tts_first_audio_ms']} ms")
                print(f"Total Response Turnaround:  {metrics['total_turnaround_ms']} ms")
                print(f"Received Audio Bytes:       {metrics['bytes_received']} bytes")
                print("=================================================")
            else:
                print("\n=== Step 6: Testing Push-to-Talk HTTP Fallback ===")
                try:
                    sim.send_voice(output_path=args.wav_out)
                except Exception as e:
                    print(f"[Notice] Voice request completed with status: {e}")
        else:
            print("\n[Notice] Device is waiting for pairing. Enter pairing code in admin dashboard to pair.")

if __name__ == "__main__":
    main()
