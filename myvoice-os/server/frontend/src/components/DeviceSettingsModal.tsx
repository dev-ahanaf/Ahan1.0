import React, { useState, useEffect } from 'react';
import { Device, DeviceSettingsPayload, AIAgent } from '../types';
import { X, Sliders, Volume2, Mic, Sun, MapPin, ShieldAlert, KeyRound, Save, AlertCircle, Bot } from 'lucide-react';
import { saveSettings, rotateDeviceToken, revokeDevice, getAgents } from '../api';

interface DeviceSettingsModalProps {
  device: Device;
  onClose: () => void;
  onSaved: () => void;
}

export const DeviceSettingsModal: React.FC<DeviceSettingsModalProps> = ({ device, onClose, onSaved }) => {
  const [agentsList, setAgentsList] = useState<AIAgent[]>([]);
  const [formData, setFormData] = useState<DeviceSettingsPayload>({
    name: device.name,
    city: device.city,
    latitude: device.latitude,
    longitude: device.longitude,
    timezone: device.timezone,
    language: device.language || 'en',
    oled_brightness: device.oled_brightness ?? 128,
    idle_display_mode: device.idle_display_mode || 'clock',
    clock_format: device.clock_format || '24h',
    speaker_volume: device.speaker_volume ?? 80,
    mic_gain: device.mic_gain ?? 50,
    wake_mode: device.wake_mode || 'button',
    weather_enabled: device.weather_enabled ?? true,
    search_enabled: device.search_enabled ?? true,
    timers_enabled: device.timers_enabled ?? true,
    system_prompt: device.system_prompt || '',
    assistant_name: device.assistant_name || 'Falcon AI',
    personality: device.personality || 'helpful, concise voice assistant',
    history_length: device.history_length ?? 6,
    asr_provider: device.asr_provider || '',
    llm_provider: device.llm_provider || '',
    llm_model: device.llm_model || '',
    tts_provider: device.tts_provider || '',
    tts_voice: device.tts_voice || '',
    vad_mode: device.vad_mode || 'manual',
    agent_id: device.agent_id || null,
  });

  useEffect(() => {
    getAgents().then(res => setAgentsList(res.agents || [])).catch(() => {});
  }, []);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenNotice, setTokenNotice] = useState<string | null>(null);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await saveSettings(device.id, formData);
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save settings');
    } finally {
      setLoading(false);
    }
  };

  const handleRotateToken = async () => {
    if (!confirm('Rotate device authentication token? Current hardware will disconnect until updated with the new token.')) return;
    try {
      const res = await rotateDeviceToken(device.id);
      setTokenNotice(`New Token: ${res.new_token}`);
      onSaved();
    } catch (err: any) {
      setError(err.message || 'Token rotation failed');
    }
  };

  const handleRevoke = async () => {
    if (!confirm(`Are you sure you want to revoke credentials for "${device.name}"? The device will immediately be marked offline.`)) return;
    try {
      await revokeDevice(device.id);
      onSaved();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Revocation failed');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fade-in overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl p-6 my-8">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center space-x-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] border border-blue-200/80 dark:border-blue-800 flex items-center justify-center shadow-xs">
            <Sliders className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Configure Agent: {device.name}</h2>
            <p className="text-xs text-slate-500 font-mono">ID: {device.id} · Active Config v{device.config_version}</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-xs flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {tokenNotice && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-mono break-all">
            {tokenNotice}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Identity & Location */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#1677ff] flex items-center space-x-1.5">
              <MapPin className="h-3.5 w-3.5" />
              <span>Identity & Geolocation</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Agent Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">IANA Timezone</label>
                <input
                  type="text"
                  value={formData.timezone}
                  onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                  required
                  className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white font-mono"
                  placeholder="Asia/Dhaka"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Weather City</label>
                <input
                  type="text"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  required
                  className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.latitude}
                    onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) || 0 })}
                    required
                    className="w-full px-2.5 py-1.5 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    value={formData.longitude}
                    onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) || 0 })}
                    required
                    className="w-full px-2.5 py-1.5 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white font-mono"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Audio Controls */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#1677ff] flex items-center space-x-1.5">
              <Volume2 className="h-3.5 w-3.5" />
              <span>Audio Levels</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200/80 dark:border-slate-800">
              <div>
                <div className="flex justify-between text-xs text-slate-700 dark:text-slate-300 mb-1.5">
                  <span className="flex items-center space-x-1">
                    <Volume2 className="h-3 w-3 text-[#1677ff]" />
                    <span>Speaker Volume</span>
                  </span>
                  <span className="font-mono text-[#1677ff] font-semibold">{formData.speaker_volume}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={formData.speaker_volume}
                  onChange={(e) => setFormData({ ...formData, speaker_volume: parseInt(e.target.value, 10) })}
                  className="w-full accent-[#1677ff]"
                />
              </div>
              <div>
                <div className="flex justify-between text-xs text-slate-700 dark:text-slate-300 mb-1.5">
                  <span className="flex items-center space-x-1">
                    <Mic className="h-3 w-3 text-emerald-500" />
                    <span>Microphone Gain</span>
                  </span>
                  <span className="font-mono text-emerald-500 font-semibold">{formData.mic_gain}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={formData.mic_gain}
                  onChange={(e) => setFormData({ ...formData, mic_gain: parseInt(e.target.value, 10) })}
                  className="w-full accent-emerald-500"
                />
              </div>
            </div>
          </div>

          {/* Display & Clock */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#1677ff] flex items-center space-x-1.5">
              <Sun className="h-3.5 w-3.5" />
              <span>OLED Display & Clock</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">OLED Brightness ({formData.oled_brightness})</label>
                <input
                  type="range"
                  min="0"
                  max="255"
                  value={formData.oled_brightness}
                  onChange={(e) => setFormData({ ...formData, oled_brightness: parseInt(e.target.value, 10) })}
                  className="w-full accent-[#1677ff] mt-2"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Idle Screen Mode</label>
                <select
                  value={formData.idle_display_mode}
                  onChange={(e) => setFormData({ ...formData, idle_display_mode: e.target.value as any })}
                  className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                >
                  <option value="clock">Clock & Date</option>
                  <option value="weather">Local Weather</option>
                  <option value="blank">Blank (Screen off)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Clock Format</label>
                <select
                  value={formData.clock_format}
                  onChange={(e) => setFormData({ ...formData, clock_format: e.target.value as any })}
                  className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                >
                  <option value="24h">24-Hour (14:30)</option>
                  <option value="12h">12-Hour (02:30 PM)</option>
                </select>
              </div>
            </div>
          </div>

          {/* AI Persona & Voice Overrides */}
          <div className="space-y-3 border-t border-slate-200 dark:border-slate-800 pt-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#1677ff] flex items-center space-x-1.5">
              <Bot className="h-3.5 w-3.5" />
              <span>Assigned AI Persona & Voice Agent</span>
            </h3>

            {/* Agent Selector */}
            <div className="bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200/60 dark:border-blue-900/40 p-3 rounded-xl space-y-1">
              <label className="block text-xs font-bold text-slate-800 dark:text-slate-200">
                Choose Falcon AI Agent Persona
              </label>
              <select
                value={formData.agent_id || ''}
                onChange={(e) => {
                  const selectedId = e.target.value || null;
                  if (selectedId) {
                    const found = agentsList.find(a => a.id === selectedId);
                    if (found) {
                      setFormData({
                        ...formData,
                        agent_id: found.id,
                        assistant_name: found.name,
                        personality: found.personality,
                        language: found.language,
                        system_prompt: found.system_prompt || '',
                        llm_provider: found.model_provider,
                        llm_model: found.model_name,
                        tts_provider: found.tts_provider,
                        tts_voice: found.tts_voice
                      });
                      return;
                    }
                  }
                  setFormData({ ...formData, agent_id: null });
                }}
                className="w-full px-3 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white font-medium"
              >
                <option value="">(Custom / Unassigned)</option>
                {agentsList.map(a => (
                  <option key={a.id} value={a.id}>
                    {a.avatar} {a.name} ({a.language === 'bn' ? 'Bengali' : 'English'} • {a.model_name})
                  </option>
                ))}
              </select>
              <p className="text-[10px] text-slate-400">
                Assigning an agent automatically applies its custom system instructions, model, and neural speech voice.
              </p>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Assistant Name</label>

                <input
                  type="text"
                  value={formData.assistant_name || ''}
                  onChange={(e) => setFormData({ ...formData, assistant_name: e.target.value })}
                  placeholder="e.g. MyVoice or XiaoZhi"
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">VAD Mode</label>
                <select
                  value={formData.vad_mode || 'manual'}
                  onChange={(e) => setFormData({ ...formData, vad_mode: e.target.value as any })}
                  className="w-full px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                >
                  <option value="manual">Manual Push-To-Talk (Button Release)</option>
                  <option value="vad">Automatic Silence VAD (Hands-Free)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">Role / Persona Description</label>
              <input
                type="text"
                value={formData.personality || ''}
                onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
                placeholder="e.g. helpful, witty companion"
                className="w-full px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] text-slate-500 mb-1">ASR Provider</label>
                <select
                  value={formData.asr_provider || ''}
                  onChange={(e) => setFormData({ ...formData, asr_provider: e.target.value || null })}
                  className="w-full px-2 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                >
                  <option value="">Default (Global)</option>
                  <option value="openai">OpenAI Whisper</option>
                  <option value="faster-whisper">Faster-Whisper</option>
                  <option value="mock">Mock ASR</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-slate-500 mb-1">Model</label>
                <select
                  value={formData.llm_provider || ''}
                  onChange={(e) => setFormData({ ...formData, llm_provider: e.target.value || null })}
                  className="w-full px-2 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                >
                  <option value="">Default (Xiaozhi Lite)</option>
                  <option value="openai">OpenAI (GPT-4.1 Mini)</option>
                  <option value="gemini">Google Gemini 1.5</option>
                  <option value="ollama">Ollama (Local LLM)</option>
                  <option value="mock">Mock LLM</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-slate-500 mb-1">Voice (TTS)</label>
                <select
                  value={formData.tts_voice || ''}
                  onChange={(e) => setFormData({ ...formData, tts_voice: e.target.value || null })}
                  className="w-full px-2 py-1.5 text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white"
                >
                  <option value="">Skye (en-US)</option>
                  <option value="en-US-JennyNeural">Jenny (en-US)</option>
                  <option value="en-US-GuyNeural">Guy (en-US)</option>
                  <option value="bn-BD-PradeepNeural">Pradeep (bn-BD)</option>
                  <option value="bn-BD-NabanitaNeural">Nabanita (bn-BD)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="border-t border-slate-200 dark:border-slate-800 pt-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center space-x-2 w-full sm:w-auto">
              <button
                type="button"
                onClick={handleRotateToken}
                className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 transition"
              >
                <KeyRound className="h-3.5 w-3.5" />
                <span>Rotate Token</span>
              </button>
              <button
                type="button"
                onClick={handleRevoke}
                className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 transition"
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                <span>Revoke</span>
              </button>
            </div>

            <div className="flex items-center space-x-3 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center space-x-2 px-5 py-2 text-sm font-semibold rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white shadow-xs disabled:opacity-50 transition"
              >
                <Save className="h-4 w-4" />
                <span>{loading ? 'Saving...' : 'Save Settings'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
