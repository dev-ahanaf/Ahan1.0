import React, { useState } from 'react';
import { X, KeyRound, CheckCircle2, AlertCircle } from 'lucide-react';
import { claimDevice } from '../api';

import { Device } from '../types';

interface PairModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPaired: () => void;
  devices?: Device[];
}

export const PairModal: React.FC<PairModalProps> = ({ isOpen, onClose, onPaired, devices = [] }) => {
  const [code, setCode] = useState('');
  const [name, setName] = useState('My Voice Assistant');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const pendingDevices = devices.filter((d) => !d.paired && d.pair_code);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setError('Please enter a valid 6-digit numeric pairing code.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await claimDevice(code, name);
      onPaired();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to claim device');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fade-in">
      <div className="relative w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-xl p-6">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center space-x-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-[#1677ff] border border-blue-200/80 dark:border-blue-800 flex items-center justify-center shadow-xs">
            <KeyRound className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Add Device</h2>
            <p className="text-xs text-slate-500">Claim your ESP32 device identity</p>
          </div>
        </div>

        {/* Auto-detected pending hardware */}
        {pendingDevices.length > 0 && (
          <div className="mb-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200 text-xs space-y-2">
            <p className="font-semibold flex items-center space-x-1.5">
              <span>⚡ Active Unpaired ESP32 Found:</span>
            </p>
            {pendingDevices.map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between bg-white dark:bg-slate-900 p-2 rounded-lg border border-amber-200 dark:border-amber-800"
              >
                <span className="font-mono text-[11px]">
                  {d.id} · Code: <strong className="text-amber-600 dark:text-amber-400 text-sm">{d.pair_code}</strong>
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setCode(d.pair_code || '');
                    setName(d.name || 'Falcon AI ESP32');
                  }}
                  className="px-2.5 py-1 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-md text-[11px] transition cursor-pointer"
                >
                  Use Code
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="mb-5 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700/60 text-xs text-slate-600 dark:text-slate-300 space-y-1.5">
          <p className="font-semibold text-slate-800 dark:text-slate-200">How to get your 6-digit code:</p>
          <ol className="list-decimal list-inside space-y-1 text-slate-500 dark:text-slate-400">
            <li>Power on the ESP32 and join Wi-Fi via captive portal.</li>
            <li>Read the 6-digit code shown on the OLED or Serial Monitor.</li>
            <li>Enter the code below within 10 minutes.</li>
          </ol>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-600 text-xs flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
              6-Digit Pairing Code
            </label>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder="000000"
              required
              className="w-full text-center text-2xl tracking-[0.4em] font-mono py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:border-[#1677ff] focus:ring-1 focus:ring-[#1677ff]"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
              Agent / Device Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Ahan or Living Room"
              required
              maxLength={50}
              className="w-full px-3.5 py-2 text-sm bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 focus:outline-hidden focus:border-[#1677ff] focus:ring-1 focus:ring-[#1677ff]"
            />
          </div>

          <div className="flex items-center space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 text-sm font-medium rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="flex-1 flex items-center justify-center space-x-2 py-2.5 text-sm font-semibold rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white shadow-xs disabled:opacity-50 transition"
            >
              <CheckCircle2 className="h-4 w-4" />
              <span>{loading ? 'Pairing...' : 'Add Device'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
