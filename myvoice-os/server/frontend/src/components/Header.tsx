import React from 'react';
import {
  Bot,
  Volume2,
  BookOpen,
  Cpu,
  Timer,
  ShieldCheck,
  Languages,
  Sun,
  Moon,
  User,
  RefreshCw
} from 'lucide-react';

interface HeaderProps {
  onRefresh: () => void;
  onOpenPair: () => void;
  loading: boolean;
  activeTab: 'fleet' | 'playground' | 'providers' | 'tools' | 'timers' | 'ota' | 'conversations' | 'system';
  onSelectTab: (tab: 'fleet' | 'playground' | 'providers' | 'tools' | 'timers' | 'ota' | 'conversations' | 'system') => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onRefresh,
  loading,
  activeTab,
  onSelectTab,
  darkMode,
  onToggleDarkMode,
}) => {
  return (
    <header className="border-b border-slate-200/80 bg-white/95 dark:bg-slate-900/95 dark:border-slate-800 backdrop-blur-md sticky top-0 z-30 px-6 py-3 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Logo & Name */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onSelectTab('fleet')}>
          <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-950/60 border border-blue-200/80 dark:border-blue-800 flex items-center justify-center text-[#1677ff] shadow-xs">
            <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
              <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.38-1 1.72V7h2a5 5 0 0 1 5 5v1h1a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2h-1v1a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5v-1H3a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2h1v-1a5 5 0 0 1 5-5h2V5.72A2.002 2.002 0 0 1 12 2m-3 9a2 2 0 1 0 0 4 2 2 0 0 0 0-4m6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4m-3 5c-1.5 0-2.8.8-3.4 2h6.8c-.6-1.2-1.9-2-3.4-2z" />
            </svg>
          </div>
          <div>
            <h1 className="font-bold tracking-tight text-slate-900 dark:text-white text-base leading-none">
              Xiaozhi Console
            </h1>
            <p className="text-[10px] text-slate-400 mt-1 font-mono tracking-wide">
              MyVoice OS v1.0.0-rc1
            </p>
          </div>
        </div>

        {/* Center Navigation Pills matching Xiaozhi */}
        <nav className="hidden md:flex items-center space-x-1 bg-slate-100/80 dark:bg-slate-800/80 p-1 rounded-xl border border-slate-200/60 dark:border-slate-700/60">
          <button
            onClick={() => onSelectTab('fleet')}
            className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'fleet'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Bot className="h-4 w-4 text-[#1677ff]" />
            <span>Agents</span>
          </button>

          <button
            onClick={() => onSelectTab('playground')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'playground'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Volume2 className="h-4 w-4" />
            <span>Voice Clone</span>
          </button>

          <button
            onClick={() => onSelectTab('tools')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'tools' || activeTab === 'providers'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <BookOpen className="h-4 w-4" />
            <span>Knowledge Base (Beta)</span>
          </button>

          <button
            onClick={() => onSelectTab('ota')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'ota'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Cpu className="h-4 w-4" />
            <span>Firmware Builder</span>
          </button>

          <button
            onClick={() => onSelectTab('timers')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'timers'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Timer className="h-4 w-4" />
            <span>Timers</span>
          </button>

          <button
            onClick={() => onSelectTab('system')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'system'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <ShieldCheck className="h-4 w-4" />
            <span>Audit & Logs</span>
          </button>
        </nav>

        {/* Right utility actions */}
        <div className="flex items-center space-x-2">
          {/* Refresh fleet status */}
          <button
            onClick={onRefresh}
            disabled={loading}
            title="Refresh status"
            className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-[#1677ff]' : ''}`} />
          </button>

          {/* Language indicator */}
          <button
            title="Language"
            className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <Languages className="h-4 w-4" />
          </button>

          {/* Dark / Light Mode Toggle */}
          <button
            onClick={onToggleDarkMode}
            title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className="p-2 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {/* User Profile Avatar */}
          <div
            title="Admin User"
            className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-600 dark:text-slate-300 ml-1 cursor-pointer"
          >
            <User className="h-4 w-4" />
          </div>
        </div>
      </div>
    </header>
  );
};
