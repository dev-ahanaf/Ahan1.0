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
  RefreshCw,
  Radio,
  Usb
} from 'lucide-react';


interface HeaderProps {
  onRefresh: () => void;
  onOpenPair: () => void;
  loading: boolean;
  activeTab: 'fleet' | 'agents' | 'flasher' | 'playground' | 'providers' | 'tools' | 'timers' | 'ota' | 'conversations' | 'system';
  onSelectTab: (tab: 'fleet' | 'agents' | 'flasher' | 'playground' | 'providers' | 'tools' | 'timers' | 'ota' | 'conversations' | 'system') => void;
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
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 border border-blue-400/40 flex items-center justify-center text-white shadow-md text-xl">
            🦅
          </div>
          <div>
            <h1 className="font-extrabold tracking-tight text-slate-900 dark:text-white text-base leading-none">
              Falcon AI Console
            </h1>
            <p className="text-[10px] text-blue-600 dark:text-blue-400 mt-1 font-mono tracking-wide font-semibold">
              Ecosystem v1.2.0 • Self-Hosted
            </p>
          </div>
        </div>

        {/* Center Navigation Tabs */}
        <nav className="hidden lg:flex items-center space-x-1 bg-slate-100/80 dark:bg-slate-800/80 p-1 rounded-xl border border-slate-200/60 dark:border-slate-700/60">
          <button
            onClick={() => onSelectTab('fleet')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'fleet'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Radio className="h-3.5 w-3.5 text-[#1677ff]" />
            <span>Devices</span>
          </button>

          <button
            onClick={() => onSelectTab('flasher')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'flasher'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-bold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Usb className="h-3.5 w-3.5 text-amber-500" />
            <span>Web Flasher</span>
          </button>

          <button
            onClick={() => onSelectTab('agents')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'agents'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Bot className="h-3.5 w-3.5 text-indigo-500" />
            <span>AI Agents</span>
          </button>

          <button
            onClick={() => onSelectTab('playground')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'playground'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Volume2 className="h-3.5 w-3.5 text-amber-500" />
            <span>Voice Studio</span>
          </button>

          <button
            onClick={() => onSelectTab('providers')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'providers'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Cpu className="h-3.5 w-3.5 text-purple-500" />
            <span>AI Models</span>
          </button>

          <button
            onClick={() => onSelectTab('conversations')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'conversations'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <BookOpen className="h-3.5 w-3.5 text-emerald-500" />
            <span>Conversations</span>
          </button>

          <button
            onClick={() => onSelectTab('tools')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'tools'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span>Tools & IoT</span>
          </button>

          <button
            onClick={() => onSelectTab('ota')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'ota'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span>Firmware & OTA</span>
          </button>

          <button
            onClick={() => onSelectTab('timers')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              activeTab === 'timers'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs font-semibold'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Timer className="h-3.5 w-3.5 text-rose-500" />
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
            <ShieldCheck className="h-3.5 w-3.5 text-cyan-500" />
            <span>Admin</span>
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
