import React, { useState, useEffect } from 'react';
import { getTimers, deleteTimer, getAlarms, createAlarm, deleteAlarm, getDevices } from '../api';
import { TimerItem, AlarmItem, Device } from '../types';
import { Timer, Bell, Trash2, Plus, AlertCircle } from 'lucide-react';

export const TimersAndAlarms: React.FC = () => {
  const [timers, setTimers] = useState<TimerItem[]>([]);
  const [alarms, setAlarms] = useState<AlarmItem[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Alarm Form State
  const [newAlarmTime, setNewAlarmTime] = useState('08:00');
  const [newAlarmLabel, setNewAlarmLabel] = useState('Alarm');
  const [selectedDevice, setSelectedDevice] = useState('');
  const [isCreatingAlarm, setIsCreatingAlarm] = useState(false);

  const loadData = async () => {
    try {
      const [tRes, aRes, dRes] = await Promise.all([getTimers(), getAlarms(), getDevices()]);
      setTimers(tRes.timers);
      setAlarms(aRes.alarms);
      setDevices(dRes.devices);
      if (dRes.devices.length > 0 && !selectedDevice) {
        setSelectedDevice(dRes.devices[0].id);
      }
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleCancelTimer = async (id: string) => {
    try {
      await deleteTimer(id);
      setTimers(prev => prev.filter(t => t.id !== id));
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCancelAlarm = async (id: string) => {
    try {
      await deleteAlarm(id);
      setAlarms(prev => prev.filter(a => a.id !== id));
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCreateAlarm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDevice) return;
    try {
      await createAlarm({
        device_id: selectedDevice,
        time_str: newAlarmTime,
        label: newAlarmLabel,
      });
      setIsCreatingAlarm(false);
      loadData();
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Loading timers and alarms...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
            <Timer className="h-6 w-6 text-[#1677ff]" />
            <span>Timers and Alarms</span>
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real-time server-scheduled countdown timers and alarms with spoken alerts and OLED popups.
          </p>
        </div>
        <button
          onClick={() => setIsCreatingAlarm(true)}
          className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white text-xs font-semibold shadow-xs transition"
        >
          <Plus className="h-4 w-4" />
          <span>New Alarm</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Create Alarm Modal */}
      {isCreatingAlarm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-xl">
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
              <Bell className="h-5 w-5 text-[#1677ff]" />
              <span>Create Device Alarm</span>
            </h3>

            <form onSubmit={handleCreateAlarm} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Target Device:</label>
                <select
                  value={selectedDevice}
                  onChange={e => setSelectedDevice(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-hidden focus:border-[#1677ff]"
                >
                  {devices.map(d => (
                    <option key={d.id} value={d.id}>{d.name} ({d.id})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Time (24-hour HH:MM):</label>
                <input
                  type="time"
                  value={newAlarmTime}
                  onChange={e => setNewAlarmTime(e.target.value)}
                  required
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-hidden focus:border-[#1677ff]"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Label:</label>
                <input
                  type="text"
                  value={newAlarmLabel}
                  onChange={e => setNewAlarmLabel(e.target.value)}
                  placeholder="e.g. Morning Wakeup"
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-hidden focus:border-[#1677ff]"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreatingAlarm(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white text-xs font-semibold shadow-xs"
                >
                  Save Alarm
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Active Timers */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-300 flex items-center space-x-2">
            <Timer className="h-4 w-4 text-[#1677ff]" />
            <span>Active Countdown Timers ({timers.filter(t => t.status === 'active').length})</span>
          </h3>

          <div className="space-y-3">
            {timers.filter(t => t.status === 'active').length === 0 ? (
              <div className="p-8 text-center bg-white dark:bg-slate-900/30 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 text-slate-400 text-xs">
                No active timers running. Say "Set a timer for 2 minutes" to create one.
              </div>
            ) : (
              timers.filter(t => t.status === 'active').map(timer => {
                const expires = new Date(timer.expires_at).getTime();
                const now = Date.now();
                const diffSec = Math.max(0, Math.floor((expires - now) / 1000));
                const mins = Math.floor(diffSec / 60);
                const secs = diffSec % 60;

                return (
                  <div key={timer.id} className="p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200/90 dark:border-slate-800 shadow-2xs flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-200">{timer.label}</h4>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Device: <span className="font-mono text-slate-700 dark:text-slate-300">{timer.device_id}</span></p>
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <span className="text-lg font-mono font-bold text-[#1677ff]">
                          {mins}:{secs.toString().padStart(2, '0')}
                        </span>
                        <span className="block text-[10px] text-slate-400">remaining</span>
                      </div>
                      <button
                        onClick={() => handleCancelTimer(timer.id)}
                        className="p-2 text-slate-400 hover:text-rose-500 transition"
                        title="Cancel Timer"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Scheduled Alarms */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-300 flex items-center space-x-2">
            <Bell className="h-4 w-4 text-rose-500" />
            <span>Scheduled Alarms ({alarms.filter(a => a.status === 'active').length})</span>
          </h3>

          <div className="space-y-3">
            {alarms.filter(a => a.status === 'active').length === 0 ? (
              <div className="p-8 text-center bg-white dark:bg-slate-900/30 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 text-slate-400 text-xs">
                No active alarms configured. Say "Set an alarm for 7 AM" to create one.
              </div>
            ) : (
              alarms.filter(a => a.status === 'active').map(alarm => (
                <div key={alarm.id} className="p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200/90 dark:border-slate-800 shadow-2xs flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-200">{alarm.label}</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      Timezone: <span className="text-slate-700 dark:text-slate-300">{alarm.timezone}</span>
                    </p>
                  </div>

                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <span className="text-lg font-mono font-bold text-rose-500">
                        {alarm.time_str}
                      </span>
                      <span className="block text-[10px] text-slate-400">Daily Alarm</span>
                    </div>
                    <button
                      onClick={() => handleCancelAlarm(alarm.id)}
                      className="p-2 text-slate-400 hover:text-rose-500 transition"
                      title="Cancel Alarm"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
