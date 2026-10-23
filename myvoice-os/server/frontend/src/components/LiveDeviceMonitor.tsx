import React, { useState, useEffect } from 'react';
import { getActiveSessions } from '../api';
import { LiveSession } from '../types';

export const LiveDeviceMonitor: React.FC = () => {
  const [sessions, setSessions] = useState<LiveSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
    const interval = setInterval(loadSessions, 2500);
    return () => clearInterval(interval);
  }, []);

  const loadSessions = async () => {
    try {
      const res = await getActiveSessions();
      setSessions(res.sessions);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStateBadge = (state: string) => {
    switch (state) {
      case 'LISTENING':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30 flex items-center gap-1.5 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-blue-400"></span>
            LISTENING
          </span>
        );
      case 'THINKING':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-spin"></span>
            THINKING
          </span>
        );
      case 'SPEAKING':
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1.5 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-purple-400"></span>
            SPEAKING
          </span>
        );
      case 'IDLE':
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            IDLE
          </span>
        );
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800 mb-6">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-800/60">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </span>
            Live Device State Monitor
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time active WebSocket sessions, state transitions, and memory diagnostics.
          </p>
        </div>
        <div className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono">
          {sessions.length} Connected
        </div>
      </div>

      {loading && (
        <div className="text-center py-8 text-xs text-slate-400">Loading active WebSocket sessions...</div>
      )}

      {!loading && sessions.length === 0 && (
        <div className="text-center py-8 px-4 rounded-xl border border-dashed border-slate-200 dark:border-slate-800 text-slate-400 text-xs">
          No microcontrollers or browser clients currently connected over WebSocket.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sessions.map((s) => {
          const uptimeSec = Math.floor(Date.now() / 1000 - s.connected_at);
          return (
            <div
              key={s.session_id}
              className="p-5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between space-y-4"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm font-bold text-white font-mono">{s.device_id}</div>
                  <div className="text-[10px] text-slate-500 font-mono mt-0.5">Session: {s.session_id.slice(0, 18)}...</div>
                </div>
                {getStateBadge(s.state)}
              </div>

              <div className="grid grid-cols-3 gap-2 text-center text-[10px] bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                <div>
                  <div className="text-slate-500">Uptime</div>
                  <div className="text-slate-200 font-mono font-medium mt-0.5">{uptimeSec}s</div>
                </div>
                <div>
                  <div className="text-slate-500">Dropped Frames</div>
                  <div className={`font-mono font-medium mt-0.5 ${s.dropped_frames > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                    {s.dropped_frames}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">Last Turn</div>
                  <div className="text-indigo-400 font-mono font-medium mt-0.5">
                    {s.last_metrics?.total_turnaround_ms ? `${s.last_metrics.total_turnaround_ms}ms` : '--'}
                  </div>
                </div>
              </div>

              {s.last_metrics && (
                <div className="text-[10px] text-slate-400 flex items-center justify-between border-t border-slate-800/60 pt-2 font-mono">
                  <span>STT: {s.last_metrics.stt_latency_ms || 0}ms</span>
                  <span>TTFT: {s.last_metrics.llm_first_token_ms || 0}ms</span>
                  <span>TTS: {s.last_metrics.tts_first_audio_ms || 0}ms</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
