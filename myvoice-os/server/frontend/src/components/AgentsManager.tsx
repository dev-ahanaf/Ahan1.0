import React, { useState, useEffect } from 'react';
import { AIAgent, AgentCreatePayload, Device } from '../types';
import { getAgents, createAgent, updateAgent, deleteAgent, testAgent } from '../api';
import {
  Plus,
  Play,
  Settings,
  Trash2,
  Cpu,
  Volume2,
  Radio,
  Send,
  Loader2,
  AlertCircle
} from 'lucide-react';


interface AgentsManagerProps {
  devices: Device[];
  onRefreshDevices: () => void;
}

export const AgentsManager: React.FC<AgentsManagerProps> = ({ devices, onRefreshDevices }) => {
  const [agents, setAgents] = useState<AIAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<AIAgent | null>(null);
  const [testingAgent, setTestingAgent] = useState<AIAgent | null>(null);

  // Test Drawer state
  const [testPrompt, setTestPrompt] = useState('Hello! Who are you and what can you help me with?');
  const [testResponse, setTestResponse] = useState<string | null>(null);
  const [testLatency, setTestLatency] = useState<number | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  // Form state
  const defaultForm: AgentCreatePayload = {
    name: '',
    avatar: '🦅',
    description: '',
    personality: 'helpful, concise voice assistant',
    system_prompt: 'You are Falcon AI, an intelligent, concise voice assistant. Keep answers under 50 words.',
    language: 'en',
    model_provider: 'gemini',
    model_name: 'gemini-1.5-flash',
    tts_provider: 'edge-tts',
    tts_voice: 'en-US-AriaNeural',
    response_style: 'concise',
    temperature: 0.7,
    tools_enabled: 'clock,weather,search,timer,alarm,device_settings'
  };

  const [formData, setFormData] = useState<AgentCreatePayload>(defaultForm);
  const [saving, setSaving] = useState(false);

  const loadAgents = async () => {
    try {
      setLoading(true);
      const res = await getAgents();
      setAgents(res.agents);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch AI agents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const openCreateModal = () => {
    setFormData(defaultForm);
    setEditingAgent(null);
    setIsCreateOpen(true);
  };

  const openEditModal = (agent: AIAgent) => {
    setEditingAgent(agent);
    setFormData({
      name: agent.name,
      avatar: agent.avatar || '🦅',
      description: agent.description || '',
      personality: agent.personality,
      system_prompt: agent.system_prompt || '',
      language: agent.language,
      model_provider: agent.model_provider,
      model_name: agent.model_name,
      tts_provider: agent.tts_provider,
      tts_voice: agent.tts_voice,
      response_style: agent.response_style,
      temperature: agent.temperature,
      tools_enabled: agent.tools_enabled
    });
    setIsCreateOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      if (editingAgent) {
        await updateAgent(editingAgent.id, formData);
      } else {
        await createAgent(formData);
      }
      setIsCreateOpen(false);
      await loadAgents();
      onRefreshDevices();
    } catch (err: any) {
      alert(err.message || 'Failed to save agent');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (agent: AIAgent) => {
    if (!confirm(`Are you sure you want to delete "${agent.name}"? Devices assigned to this agent will revert to default settings.`)) {
      return;
    }
    try {
      await deleteAgent(agent.id);
      await loadAgents();
      onRefreshDevices();
    } catch (err: any) {
      alert(err.message || 'Failed to delete agent');
    }
  };

  const runAgentTest = async (promptText = testPrompt) => {
    if (!testingAgent) return;
    try {
      setTestLoading(true);
      setTestResponse(null);
      setTestLatency(null);
      const res = await testAgent(testingAgent.id, promptText);
      if (res.ok) {
        setTestResponse(res.response || 'No response returned.');
        setTestLatency(res.latency_ms || 0);
      } else {
        setTestResponse(`Error: ${res.error || 'Test failed'}`);
      }
    } catch (err: any) {
      setTestResponse(`Error: ${err.message || 'Test failed'}`);
    } finally {
      setTestLoading(false);
    }
  };

  return (

    <div className="space-y-6">
      {/* Header bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-2xs">
        <div className="flex items-center space-x-3.5">
          <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/60 border border-blue-200/80 dark:border-blue-800 flex items-center justify-center text-[#1677ff] shadow-xs text-2xl">
            🦅
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white leading-tight">AI Agent Studio</h2>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                Falcon AI
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium mt-0.5">
              Create, customize, and deploy multilingual AI voice personas across your ESP32 hardware fleet
            </p>
          </div>
        </div>

        <button
          onClick={openCreateModal}
          className="inline-flex items-center justify-center space-x-2 bg-[#1677ff] hover:bg-blue-600 text-white px-4 py-2.5 rounded-xl font-semibold text-xs transition shadow-sm hover:shadow-md cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Create AI Agent</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Agents Grid */}
      {loading ? (
        <div className="py-16 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#1677ff]" />
          <p className="text-xs font-medium">Loading Falcon AI Agents...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {agents.map((agent) => {
            const assignedDevices = devices.filter((d) => d.agent_id === agent.id);
            return (
              <div
                key={agent.id}
                className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-5 shadow-2xs hover:shadow-md transition-all flex flex-col justify-between"
              >
                <div>
                  {/* Top Bar with Avatar, Name, Language */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-2xl shadow-2xs">
                        {agent.avatar || '🦅'}
                      </div>
                      <div>
                        <h3 className="font-bold text-slate-900 dark:text-white text-base leading-snug">
                          {agent.name}
                        </h3>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700">
                            {agent.language === 'bn' ? '🇧🇩 Bengali' : '🇺🇸 English'}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                            {agent.model_provider}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => openEditModal(agent)}
                        className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
                        title="Edit Agent"
                      >
                        <Settings className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(agent)}
                        className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition"
                        title="Delete Agent"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Description & Personality */}
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 line-clamp-2">
                    {agent.description || agent.personality}
                  </p>

                  {/* Badges Info */}
                  <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 flex items-center space-x-1.5">
                        <Cpu className="w-3.5 h-3.5" />
                        <span>AI Model</span>
                      </span>
                      <span className="font-mono font-medium text-slate-700 dark:text-slate-200 text-[11px]">
                        {agent.model_name}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 flex items-center space-x-1.5">
                        <Volume2 className="w-3.5 h-3.5" />
                        <span>Voice</span>
                      </span>
                      <span className="font-mono text-slate-700 dark:text-slate-200 text-[11px] truncate max-w-[150px]">
                        {agent.tts_voice}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-400 flex items-center space-x-1.5">
                        <Radio className="w-3.5 h-3.5" />
                        <span>Assigned Devices</span>
                      </span>
                      <span className="font-semibold text-blue-600 dark:text-blue-400 text-xs">
                        {assignedDevices.length} device{assignedDevices.length === 1 ? '' : 's'}
                      </span>
                    </div>
                  </div>

                  {/* Assigned Hardware Chips */}
                  {assignedDevices.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {assignedDevices.map((d) => (
                        <span
                          key={d.id}
                          className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono"
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              d.online ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                            }`}
                          />
                          <span>{d.name || d.id}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Card Actions */}
                <div className="mt-5 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center space-x-2">
                  <button
                    onClick={() => {
                      setTestingAgent(agent);
                      setTestResponse(null);
                      setTestLatency(null);
                      if (agent.language === 'bn') {
                        setTestPrompt('আপনি কে? ফ্যালকন এআই কি কি করতে পারে?');
                      } else {
                        setTestPrompt('Hello Falcon! Tell me what capabilities you have.');
                      }
                    }}
                    className="flex-1 inline-flex items-center justify-center space-x-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 py-2 rounded-xl text-xs font-semibold transition"
                  >
                    <Play className="w-3.5 h-3.5 text-blue-500 fill-blue-500" />
                    <span>Test Prompt</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create / Edit Agent Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl max-w-xl w-full p-6 shadow-2xl space-y-5 my-8">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
              <div className="flex items-center space-x-3">
                <span className="text-3xl">{formData.avatar || '🦅'}</span>
                <div>
                  <h3 className="font-bold text-lg text-slate-900 dark:text-white">
                    {editingAgent ? 'Edit AI Agent' : 'Create New Falcon Agent'}
                  </h3>
                  <p className="text-xs text-slate-400">Configure persona, model provider, and speech settings</p>
                </div>
              </div>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="sm:col-span-2 space-y-1">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Agent Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Falcon Assistant, Falcon Bengali"
                    className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1677ff]"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Avatar Emoji</label>
                  <input
                    type="text"
                    value={formData.avatar}
                    onChange={(e) => setFormData({ ...formData, avatar: e.target.value })}
                    className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-white text-center text-lg"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Short description of this persona's purpose"
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1677ff]"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Primary Language</label>
                  <select
                    value={formData.language}
                    onChange={(e) => {
                      const lang = e.target.value;
                      setFormData({
                        ...formData,
                        language: lang,
                        tts_voice: lang === 'bn' ? 'bn-BD-NabanitaNeural' : 'en-US-AriaNeural'
                      });
                    }}
                    className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-white"
                  >
                    <option value="en">🇺🇸 English</option>
                    <option value="bn">🇧🇩 Bengali (বাংলা)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">AI Model Provider</label>
                  <select
                    value={formData.model_provider}
                    onChange={(e) => {
                      const prov = e.target.value;
                      let mName = 'gemini-1.5-flash';
                      if (prov === 'openai') mName = 'gpt-4o-mini';
                      if (prov === 'ollama') mName = 'llama3.2';
                      setFormData({ ...formData, model_provider: prov, model_name: mName });
                    }}
                    className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-white"
                  >
                    <option value="gemini">Google Gemini</option>
                    <option value="openai">OpenAI</option>
                    <option value="ollama">Local Ollama</option>
                    <option value="openai-compatible">OpenAI Compatible API</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Model Name</label>
                  <input
                    type="text"
                    value={formData.model_name}
                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                    className="w-full px-3.5 py-2 text-xs font-mono rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-white"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">TTS Voice</label>
                  <select
                    value={formData.tts_voice}
                    onChange={(e) => setFormData({ ...formData, tts_voice: e.target.value })}
                    className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-white"
                  >
                    <optgroup label="Bengali Voices">
                      <option value="bn-BD-NabanitaNeural">bn-BD-NabanitaNeural (Female)</option>
                      <option value="bn-BD-PradeepNeural">bn-BD-PradeepNeural (Male)</option>
                    </optgroup>
                    <optgroup label="English Voices">
                      <option value="en-US-AriaNeural">en-US-AriaNeural (Female)</option>
                      <option value="en-US-GuyNeural">en-US-GuyNeural (Male)</option>
                      <option value="en-US-JennyNeural">en-US-JennyNeural (Female)</option>
                    </optgroup>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300">System Prompt</label>
                <textarea
                  rows={3}
                  value={formData.system_prompt}
                  onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                  placeholder="Instructions guiding this agent's tone, knowledge, and restrictions"
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1677ff]"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100 dark:border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center space-x-1.5 bg-[#1677ff] hover:bg-blue-600 text-white px-5 py-2 rounded-xl text-xs font-semibold shadow-sm transition disabled:opacity-50"
                >
                  {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>{editingAgent ? 'Update Agent' : 'Create Agent'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Test Agent Drawer / Modal */}
      {testingAgent && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">{testingAgent.avatar || '🦅'}</span>
                <div>
                  <h3 className="font-bold text-base text-slate-900 dark:text-white">
                    Testing: {testingAgent.name}
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono">
                    {testingAgent.model_name} • {testingAgent.language === 'bn' ? 'Bengali' : 'English'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setTestingAgent(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-base font-bold"
              >
                ✕
              </button>
            </div>

            {/* Quick Test Chips */}
            <div className="flex flex-wrap gap-1.5">
              {(testingAgent.language === 'bn'
                ? ['আজকের আবহাওয়া কেমন?', 'কয়টা বাজে?', 'তুমি কি কাজ করতে পারো?', 'একটি মজার কৌতুক বলো']
                : ["What's the weather today?", 'What time is it?', 'Tell me a brief joke', 'What can you do?']
              ).map((chip) => (
                <button
                  key={chip}
                  onClick={() => {
                    setTestPrompt(chip);
                    runAgentTest(chip);
                  }}
                  className="px-2.5 py-1 rounded-lg text-[11px] bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-600 text-slate-600 dark:text-slate-300 transition"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Prompt Input */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Spoken Query / Prompt</label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && runAgentTest()}
                  className="flex-1 px-3.5 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#1677ff]"
                />
                <button
                  onClick={() => runAgentTest()}
                  disabled={testLoading}
                  className="px-4 py-2 bg-[#1677ff] hover:bg-blue-600 text-white rounded-xl text-xs font-semibold inline-flex items-center space-x-1 disabled:opacity-50 transition"
                >
                  {testLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>Test</span>
                </button>
              </div>
            </div>

            {/* Output Box */}
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/80 dark:border-slate-800 min-h-[100px] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium mb-1.5">
                  <span>Synthesized Assistant Answer:</span>
                  {testLatency !== null && (
                    <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                      ⚡ {testLatency} ms
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed">
                  {testLoading ? (
                    <span className="text-slate-400 italic">Thinking and synthesizing response...</span>
                  ) : (
                    testResponse || <span className="text-slate-400 italic">Click 'Test' or select a query chip above</span>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
