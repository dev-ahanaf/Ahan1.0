import React, { useState } from 'react';
import { Device } from '../types';
import { Terminal, Send, Sparkles, MessageSquare } from 'lucide-react';
import { askAssistant } from '../api';

interface CommandLabProps {
  devices: Device[];
}

export const CommandLab: React.FC<CommandLabProps> = ({ devices }) => {
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);

  const pairedDevices = devices.filter(d => d.paired);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setAnswer(null);
    try {
      const res = await askAssistant(prompt, selectedDevice || null);
      setAnswer(res.answer);
    } catch (err: any) {
      setAnswer(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickPrompt = (text: string) => {
    setPrompt(text);
  };

  return (
    <div className="p-6 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200/90 dark:border-slate-800/80 shadow-xs">
      <div className="flex items-center space-x-3 mb-4">
        <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-500/10 text-[#1677ff] border border-blue-200/80 dark:border-blue-500/20">
          <Terminal className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-white">Assistant Command Lab</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Test voice commands, weather skills, and web queries without hardware</p>
        </div>
      </div>

      <form onSubmit={handleRun} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-1">
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Context Target
            </label>
            <select
              value={selectedDevice}
              onChange={(e) => setSelectedDevice(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-white focus:outline-hidden focus:border-[#1677ff]"
            >
              <option value="">Default Location (Dhaka)</option>
              {pairedDevices.map(d => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.city})
                </option>
              ))}
            </select>
          </div>

          <div className="sm:col-span-2">
            <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Test Prompt
            </label>
            <div className="relative">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="What time is it? / What's the weather? / Search for James Webb..."
                required
                className="w-full pl-3.5 pr-24 py-2 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-white placeholder-slate-400 focus:outline-hidden focus:border-[#1677ff]"
              />
              <button
                type="submit"
                disabled={loading || !prompt.trim()}
                className="absolute right-1.5 top-1.5 bottom-1.5 px-3 rounded-lg bg-[#1677ff] hover:bg-blue-600 text-white text-xs font-semibold flex items-center space-x-1.5 disabled:opacity-50 transition"
              >
                <Send className="h-3 w-3" />
                <span>{loading ? 'Running...' : 'Send'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Quick Suggestion Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs text-slate-400 flex items-center space-x-1">
            <Sparkles className="h-3 w-3 text-[#1677ff]" />
            <span>Try:</span>
          </span>
          {[
            "What time is it?",
            "What's the weather today?",
            "Search for Mars rover updates",
            "আজকের আবহাওয়া কেমন?"
          ].map((quick, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleQuickPrompt(quick)}
              className="px-2.5 py-1 text-xs rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800/60 dark:hover:bg-slate-700/80 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700/50 transition"
            >
              {quick}
            </button>
          ))}
        </div>
      </form>

      {/* Answer Output Container */}
      {answer && (
        <div className="mt-4 p-4 rounded-xl bg-blue-50/60 dark:bg-slate-950/80 border border-blue-200 dark:border-blue-500/30 text-sm text-slate-800 dark:text-slate-200 flex items-start space-x-3 animate-fade-in">
          <MessageSquare className="h-4 w-4 text-[#1677ff] mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="text-xs font-semibold text-[#1677ff] uppercase tracking-wider mb-1">Assistant Response</p>
            <p className="leading-relaxed">{answer}</p>
          </div>
        </div>
      )}
    </div>
  );
};
