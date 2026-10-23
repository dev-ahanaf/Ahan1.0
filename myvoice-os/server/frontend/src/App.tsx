import React, { useState, useEffect, useCallback } from 'react';
import { Device } from './types';
import { getDevices } from './api';
import { Header } from './components/Header';
import { StatsOverview } from './components/StatsOverview';
import { DeviceCard } from './components/DeviceCard';
import { PairModal } from './components/PairModal';
import { DeviceSettingsModal } from './components/DeviceSettingsModal';
import { CommandLab } from './components/CommandLab';
import { AIProviderSettings } from './components/AIProviderSettings';
import { ConversationViewer } from './components/ConversationViewer';
import { VoicePlayground } from './components/VoicePlayground';
import { LiveDeviceMonitor } from './components/LiveDeviceMonitor';
import { ToolsAndSkills } from './components/ToolsAndSkills';
import { TimersAndAlarms } from './components/TimersAndAlarms';
import { OTAUpdates } from './components/OTAUpdates';
import { SystemSettings } from './components/SystemSettings';
import { AgentsManager } from './components/AgentsManager';
import { WebFlasher } from './components/WebFlasher';
import {
  Search,
  ChevronDown,
  AlertCircle,
  Activity,
  Radio,
  ChevronRight,
  Zap
} from 'lucide-react';

export const App: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPairOpen, setIsPairOpen] = useState(false);
  const [activeSettingsDevice, setActiveSettingsDevice] = useState<Device | null>(null);
  const [activeTab, setActiveTab] = useState<
    'fleet' | 'agents' | 'flasher' | 'playground' | 'providers' | 'tools' | 'timers' | 'ota' | 'conversations' | 'system'
  >('fleet');

  const [searchQuery, setSearchQuery] = useState('');
  const [darkMode, setDarkMode] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const loadDevices = useCallback(async () => {
    try {
      const res = await getDevices();
      setDevices(res.devices);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch fleet state');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDevices();
    const interval = setInterval(loadDevices, 15000);
    return () => clearInterval(interval);
  }, [loadDevices]);

  const filteredDevices = devices.filter((d) =>
    (d.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.id || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.llm_model || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#f8fafc] dark:bg-slate-950 text-slate-800 dark:text-slate-100 flex flex-col transition-colors">
      <Header
        onRefresh={loadDevices}
        onOpenPair={() => setIsPairOpen(true)}
        loading={loading}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        darkMode={darkMode}
        onToggleDarkMode={() => setDarkMode(!darkMode)}
      />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        {/* Error Banner */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300 text-sm flex items-center space-x-3 shadow-2xs">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <div>
              <p className="font-semibold">Failed to communicate with MyVoice OS Server</p>
              <p className="text-xs text-rose-500 dark:text-rose-400 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Tab 1: Agents (Fleet View matching Xiaozhi Console) */}
        {activeTab === 'fleet' && (
          <div className="space-y-6">
            {/* Subheader Card matching xiaozhi.me/console/agents */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-4 sm:p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-2xs">
              {/* Left: Robot icon and Agent count */}
              <div className="flex items-center space-x-3.5">
                <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/60 border border-blue-200/80 dark:border-blue-800 flex items-center justify-center text-[#1677ff] shadow-xs">
                  <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
                    <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.38-1 1.72V7h2a5 5 0 0 1 5 5v1h1a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-1v1a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5v-1H3a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2h1v-1a5 5 0 0 1 5-5h2V5.72A2.002 2.002 0 0 1 12 2m-3 9a2 2 0 1 0 0 4 2 2 0 0 0 0-4m6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4m-3 5c-1.5 0-2.8.8-3.4 2h6.8c-.6-1.2-1.9-2-3.4-2z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white leading-tight">Agents</h2>
                  <p className="text-xs text-slate-400 font-medium mt-0.5">
                    {filteredDevices.length} agents
                  </p>
                </div>
              </div>

              {/* Right: Search Bar and Add Device Button */}
              <div className="flex items-center space-x-3 w-full md:w-auto">
                <div className="relative flex-1 md:w-80">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search agents or devices"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 placeholder-slate-400 text-xs focus:outline-hidden focus:border-[#1677ff] focus:ring-2 focus:ring-[#1677ff]/20 transition"
                  />
                </div>

                <button
                  onClick={() => setActiveTab('flasher')}
                  className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-medium text-xs shadow-xs hover:shadow transition shrink-0 cursor-pointer"
                  title="Flash ESP32 over USB Web Serial"
                >
                  <Zap className="h-3.5 w-3.5" />
                  <span>Flash USB</span>
                </button>

                <button
                  onClick={() => setIsPairOpen(true)}
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white font-medium text-xs shadow-xs hover:shadow transition shrink-0 cursor-pointer"
                >
                  <span>+ Add Device</span>
                  <ChevronDown className="h-3.5 w-3.5 opacity-80" />
                </button>
              </div>
            </div>

            {/* Agent Cards Grid */}
            {loading && !devices.length ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {[1, 2, 3].map((n) => (
                  <div
                    key={n}
                    className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 animate-pulse h-52 shadow-2xs"
                  />
                ))}
              </div>
            ) : filteredDevices.length === 0 ? (
              <div className="p-12 text-center rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-900/50 space-y-3">
                <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] mx-auto flex items-center justify-center border border-blue-200/80 dark:border-blue-800">
                  <Radio className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-800 dark:text-white">
                    {searchQuery ? 'No matching agents' : 'No agents paired yet'}
                  </h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                    {searchQuery
                      ? 'Try another search term or clear the filter.'
                      : 'Power on your ESP32 device, join Wi-Fi via captive portal, and click "+ Add Device" above.'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredDevices.map((device) => (
                  <DeviceCard
                    key={device.id}
                    device={device}
                    onOpenSettings={(dev) => setActiveSettingsDevice(dev)}
                    onOpenHistory={() => setActiveTab('conversations')}
                  />
                ))}
              </div>
            )}

            {/* Collapsible Diagnostics & Interactive Lab Drawer */}
            <div className="pt-4 border-t border-slate-200/80 dark:border-slate-800">
              <button
                onClick={() => setShowDiagnostics(!showDiagnostics)}
                className="w-full flex items-center justify-between p-3.5 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition text-xs font-semibold text-slate-700 dark:text-slate-300 shadow-2xs"
              >
                <div className="flex items-center space-x-2.5">
                  <Activity className="h-4 w-4 text-[#1677ff]" />
                  <span>Hardware Telemetry, Live WebSocket Monitor & Command Lab</span>
                </div>
                <div className="flex items-center space-x-1.5 text-slate-400">
                  <span>{showDiagnostics ? 'Hide Diagnostics' : 'Show Diagnostics'}</span>
                  <ChevronRight className={`h-4 w-4 transition-transform ${showDiagnostics ? 'rotate-90' : ''}`} />
                </div>
              </button>

              {showDiagnostics && (
                <div className="mt-5 space-y-6 animate-fade-in">
                  <StatsOverview devices={devices} />

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                      <LiveDeviceMonitor />
                    </div>
                    <div>
                      <CommandLab devices={devices} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: AI Agents Studio */}
        {activeTab === 'agents' && (
          <div className="space-y-4">
            <AgentsManager devices={devices} onRefreshDevices={loadDevices} />
          </div>
        )}

        {/* Tab: USB Web Flasher (ESP32 DevKit v1) */}
        {activeTab === 'flasher' && (
          <div className="space-y-4">
            <WebFlasher onGoToFleet={() => setActiveTab('fleet')} />
          </div>
        )}

        {/* Tab 2: Voice Clone / Voice Playground */}
        {activeTab === 'playground' && (
          <div className="space-y-4">
            <VoicePlayground devices={devices} />
          </div>
        )}

        {/* Tab 3: AI Provider Settings */}
        {activeTab === 'providers' && (
          <div className="space-y-4">
            <AIProviderSettings />
          </div>
        )}

        {/* Tab 4: Knowledge Base (Beta) / Tools & Skills */}
        {activeTab === 'tools' && (
          <div className="space-y-6">
            <ToolsAndSkills />
            <AIProviderSettings />
          </div>
        )}

        {/* Tab 5: Timers & Alarms */}
        {activeTab === 'timers' && (
          <div className="space-y-4">
            <TimersAndAlarms />
          </div>
        )}

        {/* Tab 6: Firmware Builder / OTA Updates */}
        {activeTab === 'ota' && (
          <div className="space-y-4">
            <OTAUpdates />
          </div>
        )}

        {/* Tab 7: Conversations History */}
        {activeTab === 'conversations' && (
          <div className="space-y-4">
            <ConversationViewer />
          </div>
        )}

        {/* Tab 8: Audit & System Settings */}
        {activeTab === 'system' && (
          <div className="space-y-4">
            <SystemSettings />
          </div>
        )}
      </main>

      {/* Falcon AI Ecosystem Footer */}
      <footer className="mt-auto border-t border-slate-200/80 dark:border-slate-800/80 bg-white/70 dark:bg-slate-900/60 py-6 px-6 text-center text-[11px] text-slate-400 space-y-1">
        <p className="font-semibold text-slate-600 dark:text-slate-300">
          🦅 Falcon AI Platform • Complete Self-Hosted ESP32 AI Voice Assistant Ecosystem v1.2
        </p>
        <p>
          Bilingual Bengali & English Speech Pipeline • Fully Independent Infrastructure • OpenAI / Gemini / Ollama / Edge-TTS
        </p>
      </footer>


      {/* Modals */}
      <PairModal
        isOpen={isPairOpen}
        onClose={() => setIsPairOpen(false)}
        onPaired={loadDevices}
      />

      {activeSettingsDevice && (
        <DeviceSettingsModal
          device={activeSettingsDevice}
          onClose={() => setActiveSettingsDevice(null)}
          onSaved={loadDevices}
        />
      )}
    </div>
  );
};

export default App;
