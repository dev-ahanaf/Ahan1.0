import React, { useState, useEffect } from 'react';
import { getAIProviders, saveAIProviders, testAIProvider } from '../api';
import { AIProvidersConfig } from '../types';

export const AIProviderSettings: React.FC = () => {
  const [config, setConfig] = useState<AIProvidersConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [asrProvider, setAsrProvider] = useState('openai');
  const [llmProvider, setLlmProvider] = useState('openai');
  const [llmModel, setLlmModel] = useState('gpt-4o-mini');
  const [ttsProvider, setTtsProvider] = useState('edge-tts');
  const [ttsVoice, setTtsVoice] = useState('en-US-AriaNeural');
  const [openaiKey, setOpenaiKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [compatUrl, setCompatUrl] = useState('http://localhost:8000/v1');
  const [compatKey, setCompatKey] = useState('');

  // Test states
  const [testStatus, setTestStatus] = useState<Record<string, { loading: boolean; ok?: boolean; error?: string }>>({});

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getAIProviders();
      setConfig(res);
      setAsrProvider(res.defaults.default_asr_provider);
      setLlmProvider(res.defaults.default_llm_provider);
      setLlmModel(res.defaults.default_llm_model);
      setTtsProvider(res.defaults.default_tts_provider);
      setTtsVoice(res.defaults.default_tts_voice);
      setOllamaUrl(res.defaults.ollama_base_url);
      setCompatUrl(res.defaults.openai_compatible_base_url);
    } catch (err: any) {
      setError(err.message || 'Failed to load AI providers');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);
      setSaveSuccess(false);

      const payload: Record<string, string> = {
        default_asr_provider: asrProvider,
        default_llm_provider: llmProvider,
        default_llm_model: llmModel,
        default_tts_provider: ttsProvider,
        default_tts_voice: ttsVoice,
        ollama_base_url: ollamaUrl,
        openai_compatible_base_url: compatUrl,
      };

      if (openaiKey.trim()) payload.openai_api_key = openaiKey.trim();
      if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim();
      if (compatKey.trim()) payload.openai_compatible_api_key = compatKey.trim();

      await saveAIProviders(payload);
      setSaveSuccess(true);
      setOpenaiKey('');
      setGeminiKey('');
      setCompatKey('');
      await loadProviders();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update AI settings');
    } finally {
      setSaving(false);
    }
  };

  const runTest = async (type: 'asr' | 'llm' | 'tts', name: string) => {
    const key = `${type}-${name}`;
    setTestStatus((prev) => ({ ...prev, [key]: { loading: true } }));
    try {
      const options: Record<string, any> = {};
      if (type === 'llm') options.model = llmModel;
      if (type === 'tts') options.voice = ttsVoice;
      if (name === 'ollama') options.base_url = ollamaUrl;
      if (name === 'openai-compatible') options.base_url = compatUrl;

      const res = await testAIProvider(type, name, options);
      setTestStatus((prev) => ({
        ...prev,
        [key]: { loading: false, ok: res.ok, error: res.error },
      }));
    } catch (err: any) {
      setTestStatus((prev) => ({
        ...prev,
        [key]: { loading: false, ok: false, error: err.message },
      }));
    }
  };

  if (loading) {
    return (
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-6 text-center text-slate-400">
        <div className="animate-spin w-8 h-8 border-2 border-[#1677ff] border-t-transparent rounded-full mx-auto mb-3"></div>
        Loading AI provider configurations...
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-6 shadow-xs">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-100 dark:border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <span className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] border border-blue-200/80 dark:border-blue-800">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </span>
            AI Engine & Provider Settings
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Configure hot-swappable AI backends for speech recognition, LLM reasoning, and neural voice synthesis.
          </p>
        </div>
        <button
          onClick={loadProviders}
          className="text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition"
        >
          Refresh Status
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs font-bold px-2 py-1 hover:bg-rose-500/20 rounded">Dismiss</button>
        </div>
      )}

      {saveSuccess && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm">
          Settings successfully saved! Changes are now active for the next conversation turn.
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Section 1: Speech-to-Text (ASR) */}
        <div className="bg-slate-50 dark:bg-slate-950/50 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80">
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">1. Automated Speech Recognition (ASR)</label>
            <button
              type="button"
              onClick={() => runTest('asr', asrProvider)}
              disabled={testStatus[`asr-${asrProvider}`]?.loading}
              className="text-xs font-medium px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/60 transition"
            >
              {testStatus[`asr-${asrProvider}`]?.loading ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Provider Backend</span>
              <select
                value={asrProvider}
                onChange={(e) => setAsrProvider(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-hidden focus:border-[#1677ff]"
              >
                {config?.available_asr.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">API Key Status</span>
              <div className="text-xs text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2.5 flex items-center justify-between">
                <span>{config?.defaults.has_openai_key ? `Configured (${config.defaults.openai_api_key_masked})` : 'Not Set'}</span>
                <span className={`w-2 h-2 rounded-full ${config?.defaults.has_openai_key ? 'bg-emerald-500' : 'bg-amber-400'}`}></span>
              </div>
            </div>
          </div>
          {testStatus[`asr-${asrProvider}`]?.ok !== undefined && (
            <div className={`mt-2 text-xs p-2 rounded-lg ${testStatus[`asr-${asrProvider}`]?.ok ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' : 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'}`}>
              {testStatus[`asr-${asrProvider}`]?.ok ? 'ASR endpoint is online and responsive.' : `Test failed: ${testStatus[`asr-${asrProvider}`]?.error}`}
            </div>
          )}
        </div>

        {/* Section 2: Large Language Model (LLM) */}
        <div className="bg-slate-50 dark:bg-slate-950/50 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80">
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">2. Large Language Model (LLM)</label>
            <button
              type="button"
              onClick={() => runTest('llm', llmProvider)}
              disabled={testStatus[`llm-${llmProvider}`]?.loading}
              className="text-xs font-medium px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/60 transition"
            >
              {testStatus[`llm-${llmProvider}`]?.loading ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Provider Backend</span>
              <select
                value={llmProvider}
                onChange={(e) => {
                  setLlmProvider(e.target.value);
                  const p = config?.available_llm.find((x) => x.id === e.target.value);
                  if (p?.models && p.models.length > 0) {
                    setLlmModel(p.models[0]);
                  }
                }}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-hidden focus:border-[#1677ff]"
              >
                {config?.available_llm.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Model Selection</span>
              <input
                type="text"
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                placeholder="e.g. gpt-4o-mini or llama3.2"
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-hidden focus:border-[#1677ff]"
              />
            </div>
          </div>

          {llmProvider === 'ollama' && (
            <div className="mt-3">
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Ollama Base URL</span>
              <input
                type="text"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-800 dark:text-white"
              />
            </div>
          )}

          {llmProvider === 'openai-compatible' && (
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Compatible Base URL</span>
                <input
                  type="text"
                  value={compatUrl}
                  onChange={(e) => setCompatUrl(e.target.value)}
                  className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-800 dark:text-white"
                />
              </div>
              <div>
                <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Custom API Key (Write-Only)</span>
                <input
                  type="password"
                  value={compatKey}
                  onChange={(e) => setCompatKey(e.target.value)}
                  placeholder="Leave blank to keep existing key"
                  className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-800 dark:text-white"
                />
              </div>
            </div>
          )}

          {testStatus[`llm-${llmProvider}`]?.ok !== undefined && (
            <div className={`mt-2 text-xs p-2 rounded-lg ${testStatus[`llm-${llmProvider}`]?.ok ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' : 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'}`}>
              {testStatus[`llm-${llmProvider}`]?.ok ? 'LLM endpoint verified.' : `Test failed: ${testStatus[`llm-${llmProvider}`]?.error}`}
            </div>
          )}
        </div>

        {/* Section 3: Text-to-Speech (TTS) */}
        <div className="bg-slate-50 dark:bg-slate-950/50 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80">
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">3. Text-to-Speech (TTS)</label>
            <button
              type="button"
              onClick={() => runTest('tts', ttsProvider)}
              disabled={testStatus[`tts-${ttsProvider}`]?.loading}
              className="text-xs font-medium px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/60 transition"
            >
              {testStatus[`tts-${ttsProvider}`]?.loading ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Provider Backend</span>
              <select
                value={ttsProvider}
                onChange={(e) => {
                  setTtsProvider(e.target.value);
                  const p = config?.available_tts.find((x) => x.id === e.target.value);
                  if (p?.voices && p.voices.length > 0) {
                    setTtsVoice(p.voices[0]);
                  }
                }}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-hidden focus:border-[#1677ff]"
              >
                {config?.available_tts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Voice / Speaker</span>
              <input
                type="text"
                value={ttsVoice}
                onChange={(e) => setTtsVoice(e.target.value)}
                placeholder="e.g. en-US-AriaNeural or bn-BD-NabanitaNeural"
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-hidden focus:border-[#1677ff]"
              />
            </div>
          </div>
          {testStatus[`tts-${ttsProvider}`]?.ok !== undefined && (
            <div className={`mt-2 text-xs p-2 rounded-lg ${testStatus[`tts-${ttsProvider}`]?.ok ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' : 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'}`}>
              {testStatus[`tts-${ttsProvider}`]?.ok ? 'TTS synthesizer online.' : `Test failed: ${testStatus[`tts-${ttsProvider}`]?.error}`}
            </div>
          )}
        </div>

        {/* Section 4: Secret API Keys */}
        <div className="bg-slate-50 dark:bg-slate-950/50 p-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80">
          <label className="text-sm font-semibold text-slate-800 dark:text-slate-200 block mb-3">4. Protected API Keys (Stored Securely)</label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Update OpenAI API Key</span>
              <input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder={config?.defaults.has_openai_key ? '•••••••••••••••• (Leave blank to keep)' : 'Enter OpenAI key'}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-hidden focus:border-[#1677ff]"
              />
            </div>
            <div>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Update Google Gemini API Key</span>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder={config?.defaults.has_gemini_key ? '•••••••••••••••• (Leave blank to keep)' : 'Enter Gemini key'}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-white focus:outline-hidden focus:border-[#1677ff]"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2.5 rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white font-medium shadow-xs hover:shadow transition disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save AI Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
};
