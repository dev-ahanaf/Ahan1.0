import React, { useState, useRef, useEffect } from 'react';
import { Device } from '../types';

interface VoicePlaygroundProps {
  devices: Device[];
}

export const VoicePlayground: React.FC<VoicePlaygroundProps> = ({ devices }) => {
  const [selectedDevice, setSelectedDevice] = useState<string>(devices[0]?.id || 'TEST:VOICE:WEB:CLIENT');
  const [sessionState, setSessionState] = useState<'DISCONNECTED' | 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING'>('DISCONNECTED');
  const [transcript, setTranscript] = useState('');
  const [llmOutput, setLlmOutput] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [metrics, setMetrics] = useState({
    stt_ms: 0,
    llm_first_token_ms: 0,
    tts_first_audio_ms: 0,
    total_ms: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef<boolean>(false);
  const listenStartTimeRef = useRef<number>(0);
  const listenStopReceivedRef = useRef<number>(0);

  useEffect(() => {
    return () => {
      disconnectWebSocket();
      stopMicrophone();
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  const getWsUrl = () => {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // For browser playground, we authenticate using temporary playground token or query params
    return `${proto}//${window.location.host}/ws/device?device_id=${encodeURIComponent(selectedDevice)}&token=playground-token`;
  };

  const connectWebSocket = () => {
    disconnectWebSocket();
    setErrorMsg(null);

    try {
      const url = getWsUrl();
      const ws = new WebSocket(url);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        setSessionState('IDLE');
        // Send hello frame
        ws.send(JSON.stringify({
          type: 'hello',
          device_id: selectedDevice,
          token: 'playground-token',
          firmware: 'web-playground-1.0.0',
          audio: { codec: 'pcm16', sample_rate: 16000, channels: 1, frame_ms: 60 }
        }));
      };

      ws.onmessage = async (evt) => {
        if (typeof evt.data === 'string') {
          const event = JSON.parse(evt.data);
          const etype = event.type;

          if (etype === 'hello_ack') {
            setSessionState('IDLE');
          } else if (etype === 'stt') {
            setTranscript(event.text || '');
            if (listenStopReceivedRef.current > 0) {
              setMetrics((prev) => ({ ...prev, stt_ms: Date.now() - listenStopReceivedRef.current }));
            }
          } else if (etype === 'llm') {
            if (metrics.llm_first_token_ms === 0 && listenStopReceivedRef.current > 0) {
              setMetrics((prev) => ({ ...prev, llm_first_token_ms: Date.now() - listenStopReceivedRef.current }));
            }
            if (!event.final) {
              setLlmOutput((prev) => prev + (event.delta || ''));
            }
          } else if (etype === 'tts_start') {
            setSessionState('SPEAKING');
            if (listenStopReceivedRef.current > 0) {
              setMetrics((prev) => ({ ...prev, tts_first_audio_ms: Date.now() - listenStopReceivedRef.current }));
            }
          } else if (etype === 'tts_stop') {
            if (listenStopReceivedRef.current > 0) {
              setMetrics((prev) => ({ ...prev, total_ms: Date.now() - listenStopReceivedRef.current }));
            }
            setTimeout(() => {
              if (sessionState === 'SPEAKING') setSessionState('IDLE');
            }, 500);
          } else if (etype === 'abort_ack') {
            setSessionState('IDLE');
            audioQueueRef.current = [];
            isPlayingRef.current = false;
          } else if (etype === 'error') {
            setErrorMsg(event.message || 'Server reported error');
            setSessionState('IDLE');
          }
        } else if (evt.data instanceof ArrayBuffer) {
          // Play returned binary PCM16 audio
          playPcm16Chunk(evt.data);
        }
      };

      ws.onerror = () => {
        setErrorMsg('WebSocket connection error. Ensure backend server is running and device credentials are valid.');
        setSessionState('DISCONNECTED');
      };

      ws.onclose = (evt) => {
        setSessionState('DISCONNECTED');
        if (evt.code === 4001) {
          setErrorMsg('Authentication failed (Code 4001). Register device first.');
        }
      };

      wsRef.current = ws;
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to open WebSocket connection');
    }
  };

  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setSessionState('DISCONNECTED');
  };

  const initAudio = () => {
    if (!audioContextRef.current) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      audioContextRef.current = new AudioCtx({ sampleRate: 16000 });
    }
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
  };

  const startMicrophone = async () => {
    try {
      initAudio();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      mediaStreamRef.current = stream;

      const ctx = audioContextRef.current!;
      const source = ctx.createMediaStreamSource(stream);
      // ScriptProcessor with 1024 buffer size (~64ms @ 16kHz)
      const processor = ctx.createScriptProcessor(1024, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        const inputData = e.inputBuffer.getChannelData(0);
        // Convert Float32 to Int16 PCM
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        wsRef.current.send(pcm16.buffer);
      };

      source.connect(processor);
      processor.connect(ctx.destination);
    } catch (err: any) {
      setErrorMsg(`Microphone permission error: ${err.message}`);
      setSessionState('IDLE');
    }
  };

  const stopMicrophone = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
  };

  const handleStartSpeaking = async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      await new Promise((r) => setTimeout(r, 400));
    }

    setTranscript('');
    setLlmOutput('');
    setMetrics({ stt_ms: 0, llm_first_token_ms: 0, tts_first_audio_ms: 0, total_ms: 0 });
    listenStartTimeRef.current = Date.now();
    listenStopReceivedRef.current = 0;

    setSessionState('LISTENING');
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'listen_start', mode: 'manual' }));
    }
    await startMicrophone();
  };

  const handleStopSpeaking = () => {
    stopMicrophone();
    listenStopReceivedRef.current = Date.now();
    setSessionState('THINKING');
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'listen_stop' }));
    }
  };

  const handleBargeIn = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'abort', reason: 'user_interrupt' }));
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setSessionState('IDLE');
  };

  const playPcm16Chunk = (arrayBuffer: ArrayBuffer) => {
    try {
      initAudio();
      const ctx = audioContextRef.current!;
      const int16 = new Int16Array(arrayBuffer);
      const audioBuffer = ctx.createBuffer(1, int16.length, 16000);
      const channelData = audioBuffer.getChannelData(0);

      for (let i = 0; i < int16.length; i++) {
        channelData[i] = int16[i] / 32768.0;
      }

      audioQueueRef.current.push(audioBuffer);
      if (!isPlayingRef.current) {
        drainAudioQueue();
      }
    } catch (err) {
      console.error('Audio chunk decode failed', err);
    }
  };

  const drainAudioQueue = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }

    isPlayingRef.current = true;
    const ctx = audioContextRef.current!;
    const nextBuffer = audioQueueRef.current.shift()!;
    const source = ctx.createBufferSource();
    source.buffer = nextBuffer;
    source.connect(ctx.destination);
    source.onended = () => {
      drainAudioQueue();
    };
    source.start();
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-6 shadow-xs space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] border border-blue-200/80 dark:border-blue-800">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
              </svg>
            </span>
            Real-Time Voice Playground
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Test full-duplex speech recognition, streaming AI response, and neural speech synthesis directly from your web browser.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedDevice}
            onChange={(e) => setSelectedDevice(e.target.value)}
            className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-1.5 text-xs text-slate-800 dark:text-white"
          >
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.id.slice(-5)})
              </option>
            ))}
            {devices.length === 0 && <option value="TEST:VOICE:WEB:CLIENT">Virtual Device</option>}
          </select>

          <button
            onClick={sessionState === 'DISCONNECTED' ? connectWebSocket : disconnectWebSocket}
            className={`text-xs px-3.5 py-1.5 rounded-xl font-medium transition shadow-xs ${
              sessionState === 'DISCONNECTED'
                ? 'bg-[#1677ff] hover:bg-blue-600 text-white'
                : 'bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'
            }`}
          >
            {sessionState === 'DISCONNECTED' ? 'Connect WS' : 'Disconnect'}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300 text-xs flex justify-between items-center">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="font-bold px-2 py-0.5 hover:bg-rose-100 dark:hover:bg-rose-500/20 rounded">✕</button>
        </div>
      )}

      {/* Main interaction deck */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left card: Voice Controller */}
        <div className="bg-slate-50/70 dark:bg-slate-950/60 p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 flex flex-col items-center justify-center text-center">
          <div className="mb-4">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                sessionState === 'LISTENING'
                  ? 'bg-blue-50 text-[#1677ff] border border-blue-200 animate-pulse'
                  : sessionState === 'THINKING'
                  ? 'bg-amber-50 text-amber-600 border border-amber-200'
                  : sessionState === 'SPEAKING'
                  ? 'bg-purple-50 text-purple-600 border border-purple-200 animate-pulse'
                  : sessionState === 'IDLE'
                  ? 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                  : 'bg-slate-100 text-slate-500 border border-slate-200'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${sessionState === 'IDLE' ? 'bg-emerald-500' : sessionState === 'DISCONNECTED' ? 'bg-slate-400' : 'bg-[#1677ff]'}`}></span>
              {sessionState}
            </span>
          </div>

          <button
            onMouseDown={handleStartSpeaking}
            onMouseUp={handleStopSpeaking}
            onTouchStart={handleStartSpeaking}
            onTouchEnd={handleStopSpeaking}
            disabled={sessionState === 'DISCONNECTED'}
            className={`w-28 h-28 rounded-full flex flex-col items-center justify-center font-bold text-white shadow-lg transition transform active:scale-95 select-none ${
              sessionState === 'LISTENING'
                ? 'bg-rose-600 ring-8 ring-rose-600/30 scale-105'
                : 'bg-[#1677ff] hover:bg-blue-600 shadow-blue-500/20'
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            <svg className="w-8 h-8 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
            </svg>
            <span className="text-xs uppercase">{sessionState === 'LISTENING' ? 'Release' : 'Hold to Talk'}</span>
          </button>

          <p className="text-[11px] text-slate-400 mt-4 max-w-xs">
            Press and hold to stream 16kHz PCM audio over WebSocket. Release to synthesize response.
          </p>

          {sessionState === 'SPEAKING' && (
            <button
              onClick={handleBargeIn}
              className="mt-4 px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-600 text-xs font-semibold transition"
            >
              Barge-In (Interrupt AI)
            </button>
          )}
        </div>

        {/* Right card: Live Transcript & Streaming Output */}
        <div className="col-span-2 bg-slate-50/70 dark:bg-slate-950/60 p-5 rounded-2xl border border-slate-200/80 dark:border-slate-800 flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">User Speech (STT)</span>
              {metrics.stt_ms > 0 && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-[#1677ff] border border-blue-200">
                  Latency: {metrics.stt_ms}ms
                </span>
              )}
            </div>
            <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm text-slate-800 dark:text-slate-200 min-h-[56px] italic">
              {transcript || <span className="text-slate-400 not-italic">Hold button and speak in English or Bangla...</span>}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">AI Voice Response (LLM + TTS)</span>
              {metrics.llm_first_token_ms > 0 && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-50 text-purple-600 border border-purple-200">
                  TTFT: {metrics.llm_first_token_ms}ms | Total: {metrics.total_ms || '...'}ms
                </span>
              )}
            </div>
            <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-sm text-slate-900 dark:text-slate-100 min-h-[110px] leading-relaxed">
              {llmOutput || <span className="text-slate-400">AI response text and synthesized audio will appear here in real time...</span>}
            </div>
          </div>

          {/* Latency Benchmarks bar */}
          <div className="pt-3 border-t border-slate-200/80 dark:border-slate-800/80 grid grid-cols-4 gap-2 text-center text-[10px]">
            <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-slate-400">STT Time</div>
              <div className="text-slate-900 dark:text-white font-mono font-bold mt-0.5">{metrics.stt_ms ? `${metrics.stt_ms}ms` : '--'}</div>
            </div>
            <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-slate-400">LLM TTFT</div>
              <div className="text-slate-900 dark:text-white font-mono font-bold mt-0.5">{metrics.llm_first_token_ms ? `${metrics.llm_first_token_ms}ms` : '--'}</div>
            </div>
            <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-slate-400">TTS First Audio</div>
              <div className="text-slate-900 dark:text-white font-mono font-bold mt-0.5">{metrics.tts_first_audio_ms ? `${metrics.tts_first_audio_ms}ms` : '--'}</div>
            </div>
            <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
              <div className="text-slate-400">Total Response</div>
              <div className="text-[#1677ff] font-mono font-bold mt-0.5">{metrics.total_ms ? `${metrics.total_ms}ms` : '--'}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
