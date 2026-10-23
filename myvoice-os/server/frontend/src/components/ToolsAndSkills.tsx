import React, { useState, useEffect } from 'react';
import { getTools, testTool } from '../api';
import { Wrench, Play, CheckCircle2, AlertCircle, Clock, CloudSun, Search, Timer, Bell, Sliders } from 'lucide-react';

const TOOL_ICONS: Record<string, React.ReactNode> = {
  get_current_time: <Clock className="h-5 w-5 text-sky-400" />,
  get_weather: <CloudSun className="h-5 w-5 text-amber-400" />,
  web_search: <Search className="h-5 w-5 text-emerald-400" />,
  manage_timer: <Timer className="h-5 w-5 text-indigo-400" />,
  manage_alarm: <Bell className="h-5 w-5 text-rose-400" />,
  device_settings: <Sliders className="h-5 w-5 text-purple-400" />,
};

export const ToolsAndSkills: React.FC = () => {
  const [tools, setTools] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState<string>('get_current_time');
  const [argsJson, setArgsJson] = useState<string>('{}');
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTools()
      .then(res => {
        setTools(res.tools);
        if (res.tools.length > 0) {
          setSelectedTool(res.tools[0].name);
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSelectTool = (name: string) => {
    setSelectedTool(name);
    setTestResult(null);
    if (name === 'get_weather') {
      setArgsJson('{\n  "city": "Dhaka"\n}');
    } else if (name === 'manage_timer') {
      setArgsJson('{\n  "action": "set",\n  "duration_seconds": 120,\n  "label": "Tea"\n}');
    } else if (name === 'manage_alarm') {
      setArgsJson('{\n  "action": "create",\n  "time_str": "07:30",\n  "label": "Morning"\n}');
    } else if (name === 'web_search') {
      setArgsJson('{\n  "query": "ESP32 latest firmware news"\n}');
    } else if (name === 'device_settings') {
      setArgsJson('{\n  "action": "set_volume",\n  "volume": 85\n}');
    } else {
      setArgsJson('{}');
    }
  };

  const handleRunTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const parsedArgs = JSON.parse(argsJson);
      const res = await testTool(selectedTool, parsedArgs);
      setTestResult(res);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400">
        <Wrench className="h-8 w-8 animate-spin mx-auto mb-2 text-indigo-400" />
        <p>Loading AI tools and skills...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <Wrench className="h-6 w-6 text-[#1677ff]" />
          <span>AI Tools and Skills Engine</span>
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Modular function calling tools executed safely with allowlisted parameters, timeout shielding, and per-device permissions.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tool Cards Column */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 px-1">Registered Tools</h3>
          {tools.map(tool => (
            <div
              key={tool.name}
              onClick={() => handleSelectTool(tool.name)}
              className={`p-4 rounded-xl border transition cursor-pointer flex items-start space-x-3.5 shadow-2xs ${
                selectedTool === tool.name
                  ? 'bg-blue-50 dark:bg-blue-950/40 border-[#1677ff] ring-1 ring-[#1677ff]/30'
                  : 'bg-white dark:bg-slate-900/60 border-slate-200/90 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800/80 shrink-0">
                {TOOL_ICONS[tool.name] || <Wrench className="h-5 w-5 text-slate-400" />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-200">{tool.name}</h4>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                    {tool.timeout_seconds}s
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">{tool.description}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Interactive Testing Playground */}
        <div className="lg:col-span-2 space-y-4 bg-white dark:bg-slate-900/60 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800/80 shadow-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 flex items-center space-x-2">
              <Play className="h-4 w-4 text-[#1677ff]" />
              <span>Interactive Tool Tester: <span className="font-mono text-[#1677ff]">{selectedTool}</span></span>
            </h3>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">JSON Arguments:</label>
            <textarea
              rows={4}
              value={argsJson}
              onChange={e => setArgsJson(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3 font-mono text-xs text-slate-800 dark:text-slate-200 focus:outline-hidden focus:border-[#1677ff]"
            />
          </div>

          <button
            onClick={handleRunTest}
            disabled={testing}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition"
          >
            <Play className="h-3.5 w-3.5" />
            <span>{testing ? 'Executing Tool...' : 'Run Tool Test'}</span>
          </button>

          {testResult && (
            <div className="mt-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {testResult.success ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-rose-500" />
                  )}
                  <span className={`text-xs font-semibold ${testResult.success ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                    {testResult.success ? 'Tool Executed Successfully' : 'Tool Execution Failed'}
                  </span>
                </div>
              </div>

              {testResult.voice_summary && (
                <div>
                  <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Synthesized Voice Summary:</span>
                  <p className="text-sm text-slate-800 dark:text-slate-200 bg-white dark:bg-slate-900/80 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800/80 mt-1">
                    "{testResult.voice_summary}"
                  </p>
                </div>
              )}

              {testResult.display_data && (
                <div>
                  <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">OLED Display Payload:</span>
                  <pre className="text-xs font-mono text-blue-600 dark:text-sky-300 bg-white dark:bg-slate-900/80 p-2 rounded-lg border border-slate-200 dark:border-slate-800/80 mt-1 overflow-x-auto">
                    {JSON.stringify(testResult.display_data, null, 2)}
                  </pre>
                </div>
              )}

              <div>
                <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">Returned Data:</span>
                <pre className="text-xs font-mono text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900/80 p-2 rounded-lg border border-slate-200 dark:border-slate-800/80 mt-1 overflow-x-auto">
                  {JSON.stringify(testResult.data || testResult.error, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
