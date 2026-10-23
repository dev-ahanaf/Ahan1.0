import React, { useState } from 'react';
import { Device } from '../types';
import { rebootDevice, resetWifiDevice, revokeDevice } from '../api';
import {
  SlidersHorizontal,
  History,
  Smartphone,
  MoreHorizontal,
  User,
  Cpu,
  Clock,
  RotateCw,
  WifiOff,
  Trash2,
  CheckCircle2
} from 'lucide-react';

interface DeviceCardProps {
  device: Device;
  onOpenSettings: (device: Device) => void;
  onOpenHistory?: (device: Device) => void;
}

export const DeviceCard: React.FC<DeviceCardProps> = ({ device, onOpenSettings, onOpenHistory }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [showDeviceInfo, setShowDeviceInfo] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const isOnline = device.online && device.paired && !device.revoked;
  const isUnlinked = !device.paired;

  // Determine avatar background color from device name initial
  const initial = (device.name || 'A').charAt(0).toUpperCase();

  const handleAction = async (action: 'reboot' | 'reset-wifi' | 'revoke') => {
    setMenuOpen(false);
    try {
      if (action === 'reboot') {
        if (!confirm(`Reboot device ${device.name}?`)) return;
        await rebootDevice(device.id);
        setActionNotice('Reboot signal sent');
      } else if (action === 'reset-wifi') {
        if (!confirm(`Clear Wi-Fi credentials on ${device.name}? It will return to setup mode.`)) return;
        await resetWifiDevice(device.id);
        setActionNotice('Wi-Fi reset sent');
      } else if (action === 'revoke') {
        if (!confirm(`Revoke device ${device.name}? Its token will be invalidated.`)) return;
        await revokeDevice(device.id);
        setActionNotice('Device revoked');
      }
      setTimeout(() => setActionNotice(null), 3500);
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    }
  };

  return (
    <div className="relative bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 rounded-2xl p-5 shadow-xs hover:shadow-md transition duration-200 flex flex-col justify-between">
      {/* Top Row: Avatar, Name, Status Badge, and More Actions Menu */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3 min-w-0">
            {/* Rounded avatar matching XiaoZhi */}
            <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 border border-emerald-200/80 dark:border-emerald-800 flex items-center justify-center font-bold text-lg shrink-0">
              {initial}
            </div>

            <div className="flex items-center space-x-2 min-w-0">
              <h3 className="font-bold text-slate-800 dark:text-white text-base truncate">
                {device.name}
              </h3>

              {/* Status pill badge matching XiaoZhi */}
              {device.revoked ? (
                <span className="px-2 py-0.5 text-[11px] font-medium rounded-full bg-rose-50 text-rose-600 border border-rose-200 shrink-0">
                  Revoked
                </span>
              ) : isUnlinked ? (
                <span className="px-2.5 py-0.5 text-[11px] font-medium rounded-full bg-amber-50 text-amber-600 border border-amber-200/80 shrink-0">
                  Unlinked
                </span>
              ) : isOnline ? (
                <span className="px-2.5 py-0.5 text-[11px] font-medium rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200/80 flex items-center space-x-1 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Online</span>
                </span>
              ) : (
                <span className="px-2.5 py-0.5 text-[11px] font-medium rounded-full bg-slate-100 text-slate-500 border border-slate-200 shrink-0">
                  Offline
                </span>
              )}
            </div>
          </div>

          {/* Three Dots Menu Button */}
          <div className="relative shrink-0">
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              title="Device options"
            >
              <MoreHorizontal className="h-5 w-5" />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-8 z-20 w-44 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg p-1 text-xs space-y-0.5">
                <button
                  onClick={() => handleAction('reboot')}
                  className="w-full text-left px-3 py-2 rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center space-x-2"
                >
                  <RotateCw className="h-3.5 w-3.5 text-amber-500" />
                  <span>Remote Reboot</span>
                </button>
                <button
                  onClick={() => handleAction('reset-wifi')}
                  className="w-full text-left px-3 py-2 rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center space-x-2"
                >
                  <WifiOff className="h-3.5 w-3.5 text-rose-500" />
                  <span>Clear Wi-Fi Setup</span>
                </button>
                <button
                  onClick={() => handleAction('revoke')}
                  className="w-full text-left px-3 py-2 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 flex items-center space-x-2"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  <span>Revoke Device</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Action feedback banner */}
        {actionNotice && (
          <div className="mb-3 px-3 py-1.5 rounded-lg bg-blue-50 text-[#1677ff] text-xs font-medium flex items-center space-x-1.5">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>{actionNotice}</span>
          </div>
        )}

        {/* Middle Info Box: Role, Model, Last Conversation */}
        <div className="bg-[#f8fafc] dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 rounded-xl p-3 my-3 grid grid-cols-3 divide-x divide-slate-200/70 dark:divide-slate-700/60 text-xs">
          {/* Role / Voice */}
          <div className="pr-2">
            <div className="text-slate-400 dark:text-slate-400 text-[10px] font-medium flex items-center space-x-1 mb-1">
              <User className="h-3 w-3" />
              <span>Role</span>
            </div>
            <p className="font-semibold text-slate-800 dark:text-slate-100 truncate text-[11px]" title={device.tts_voice || 'Skye (en-US)'}>
              {device.tts_voice ? device.tts_voice.split('-').slice(-2).join('-') : 'Skye (en-US)'}
            </p>
          </div>

          {/* Model */}
          <div className="px-2">
            <div className="text-slate-400 dark:text-slate-400 text-[10px] font-medium flex items-center space-x-1 mb-1">
              <Cpu className="h-3 w-3" />
              <span>Model</span>
            </div>
            <p className="font-semibold text-slate-800 dark:text-slate-100 truncate text-[11px]" title={device.llm_model || 'Xiaozhi Lite'}>
              {device.llm_model || 'Xiaozhi Lite'}
            </p>
          </div>

          {/* Last conversation */}
          <div className="pl-2">
            <div className="text-slate-400 dark:text-slate-400 text-[10px] font-medium flex items-center space-x-1 mb-1">
              <Clock className="h-3 w-3" />
              <span>Last conver...</span>
            </div>
            <p className="font-semibold text-slate-800 dark:text-slate-100 truncate text-[11px]">
              {device.last_seen ? 'Active' : 'None'}
            </p>
          </div>
        </div>

        {/* Optional Expanded Hardware Details Box */}
        {showDeviceInfo && (
          <div className="p-3 mb-3 bg-blue-50/60 dark:bg-slate-800/80 rounded-xl border border-blue-100 dark:border-slate-700 text-xs space-y-1 text-slate-600 dark:text-slate-300">
            <div className="flex justify-between font-mono text-[11px]">
              <span className="text-slate-400">MAC / ID:</span>
              <span className="font-semibold">{device.id}</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">City / TZ:</span>
              <span>{device.city} ({device.timezone})</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Firmware:</span>
              <span className="font-mono">v{device.firmware} (Config v{device.config_version})</span>
            </div>
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Speaker Volume:</span>
              <span>{device.speaker_volume ?? 80}%</span>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Row Action Buttons: Configure, History, Devices (1) */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
        <button
          onClick={() => onOpenSettings(device)}
          className="flex items-center justify-center space-x-1.5 py-1.5 px-2 rounded-lg border border-slate-200/80 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium transition shadow-2xs"
        >
          <SlidersHorizontal className="h-3.5 w-3.5 text-slate-500" />
          <span>Configure</span>
        </button>

        <button
          onClick={() => onOpenHistory ? onOpenHistory(device) : null}
          className="flex items-center justify-center space-x-1.5 py-1.5 px-2 rounded-lg border border-slate-200/80 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium transition shadow-2xs"
        >
          <History className="h-3.5 w-3.5 text-slate-500" />
          <span>History</span>
        </button>

        <button
          onClick={() => setShowDeviceInfo(!showDeviceInfo)}
          className={`flex items-center justify-center space-x-1.5 py-1.5 px-2 rounded-lg border transition shadow-2xs text-xs font-medium ${
            showDeviceInfo
              ? 'border-blue-400 bg-blue-50 text-[#1677ff]'
              : 'border-slate-200/80 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200'
          }`}
        >
          <Smartphone className="h-3.5 w-3.5 text-slate-500" />
          <span>Devices ({device.paired ? '1' : '0'})</span>
        </button>
      </div>
    </div>
  );
};
