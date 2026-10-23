import React, { useState, useEffect } from 'react';
import { getAuditLogs } from '../api';
import { AuditLogItem } from '../types';
import { Shield, ShieldAlert, Server, Terminal, Lock } from 'lucide-react';

export const SystemSettings: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAuditLogs()
      .then(res => setLogs(res.audit_logs))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Loading audit logs and system status...</div>;
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300 text-xs">
          {error}
        </div>
      )}

      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <Shield className="h-6 w-6 text-[#1677ff]" />
          <span>System Settings and Security Audit</span>
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Review backend security boundaries, cryptographic authorization policies, and immutable administrative audit logs.
        </p>
      </div>

      {/* Security Health Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200/90 dark:border-slate-800 shadow-2xs flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Authentication</span>
            <p className="text-sm font-bold text-slate-900 dark:text-slate-200">Asymmetric Token Hash</p>
            <p className="text-[10px] text-emerald-600 dark:text-emerald-400">SHA-256 + Constant-Time Verify</p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200/90 dark:border-slate-800 shadow-2xs flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-blue-50 dark:bg-blue-500/10 text-[#1677ff] border border-blue-200 dark:border-blue-500/20">
            <Server className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Environment</span>
            <p className="text-sm font-bold text-slate-900 dark:text-slate-200">MyVoice OS v1.0.0-rc1</p>
            <p className="text-[10px] text-[#1677ff]">Background Scheduler Active</p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-slate-900/60 border border-slate-200/90 dark:border-slate-800 shadow-2xs flex items-center space-x-3">
          <div className="p-2.5 rounded-lg bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-200 dark:border-sky-500/20">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] text-slate-500 dark:text-slate-400 uppercase font-semibold">Firmware Target</span>
            <p className="text-sm font-bold text-slate-900 dark:text-slate-200">ESP32-WROOM-32</p>
            <p className="text-[10px] text-sky-600 dark:text-sky-400">320 KB SRAM / No PSRAM Req.</p>
          </div>
        </div>
      </div>

      {/* Audit Log Card */}
      <div className="bg-white dark:bg-slate-900/40 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800/80 shadow-xs space-y-4">
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center space-x-2">
          <ShieldAlert className="h-4 w-4 text-amber-500" />
          <span>Administrative Action Audit Log ({logs.length})</span>
        </h3>

        {logs.length === 0 ? (
          <p className="text-xs text-slate-400 text-center py-6">No administrative actions logged yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                <tr>
                  <th className="py-2.5 font-semibold">Timestamp</th>
                  <th className="py-2.5 font-semibold">User</th>
                  <th className="py-2.5 font-semibold">Action</th>
                  <th className="py-2.5 font-semibold">Target</th>
                  <th className="py-2.5 font-semibold">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                {logs.map(log => (
                  <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <td className="py-3 text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 font-semibold text-slate-800 dark:text-slate-300">{log.user}</td>
                    <td className="py-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 dark:bg-blue-500/10 text-[#1677ff] border border-blue-200 dark:border-blue-500/20">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-slate-700 dark:text-slate-300">{log.target || 'N/A'}</td>
                    <td className="py-3 font-mono text-[11px] text-slate-500 dark:text-slate-400 max-w-xs truncate" title={log.details}>
                      {log.details || 'None'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
