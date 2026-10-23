import React from 'react';
import { Device } from '../types';
import { Server, Radio, HardDrive, WifiOff } from 'lucide-react';

interface StatsOverviewProps {
  devices: Device[];
}

export const StatsOverview: React.FC<StatsOverviewProps> = ({ devices }) => {
  const total = devices.length;
  const paired = devices.filter(d => d.paired).length;
  const online = devices.filter(d => d.online && d.paired).length;
  const offline = paired - online;

  const stats = [
    { label: 'REGISTERED DEVICES', value: total, icon: Server, color: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/20' },
    { label: 'PAIRED ASSISTANTS', value: paired, icon: HardDrive, color: 'text-sky-400', bg: 'bg-sky-500/10', border: 'border-sky-500/20' },
    { label: 'ONLINE NOW (2 MIN)', value: online, icon: Radio, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
    { label: 'OFFLINE / STANDBY', value: offline, icon: WifiOff, color: 'text-slate-400', bg: 'bg-slate-500/10', border: 'border-slate-500/20' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map((s, idx) => {
        const Icon = s.icon;
        return (
          <div key={idx} className="p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200/90 dark:border-slate-800 shadow-2xs flex items-center space-x-3.5">
            <div className={`p-2.5 rounded-lg ${s.bg} ${s.color}`}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[11px] font-semibold tracking-wider text-slate-500 dark:text-slate-400">{s.label}</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">{s.value}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
