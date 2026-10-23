import React, { useState, useEffect } from 'react';
import { getOTAReleases, uploadFirmware, deployFirmware, getDevices } from '../api';
import { FirmwareReleaseItem, Device } from '../types';
import { HardDriveDownload, Upload, CheckCircle2, AlertCircle, ShieldCheck, Send } from 'lucide-react';

export const OTAUpdates: React.FC = () => {
  const [releases, setReleases] = useState<FirmwareReleaseItem[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);



  // Upload Form State
  const [file, setFile] = useState<File | null>(null);
  const [version, setVersion] = useState('1.1.0');
  const [releaseNotes, setReleaseNotes] = useState('');
  const [uploading, setUploading] = useState(false);

  // Deploy Form State
  const [deployVersion, setDeployVersion] = useState('');
  const [deployTarget, setDeployTarget] = useState('ALL');
  const [deploying, setDeploying] = useState(false);

  const loadData = async () => {
    try {
      const [rRes, dRes] = await Promise.all([getOTAReleases(), getDevices()]);
      setReleases(rRes.releases);
      setDevices(dRes.devices);
      if (rRes.releases.length > 0 && !deployVersion) {
        setDeployVersion(rRes.releases[0].version);
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
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select an ESP32 firmware .bin file');
      return;
    }
    setUploading(true);
    setError(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('version', version);
    formData.append('target_hardware', 'esp32dev');
    if (releaseNotes) {
      formData.append('release_notes', releaseNotes);
    }

    try {
      const res = await uploadFirmware(formData);
      setSuccessMsg(`Firmware ${version} uploaded successfully (SHA-256: ${res.release.sha256.substring(0, 12)}...)`);
      setFile(null);
      setVersion('1.2.0');
      setReleaseNotes('');
      loadData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDeploy = async () => {
    if (!deployVersion) return;
    setDeploying(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await deployFirmware(deployVersion, deployTarget);
      setSuccessMsg(`Dispatched OTA update command for ${deployVersion} to ${res.results.length} device(s)`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDeploying(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Loading firmware catalog...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <HardDriveDownload className="h-6 w-6 text-[#1677ff]" />
          <span>OTA Firmware Updates & Builder</span>
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Distribute authenticated over-the-air firmware updates with cryptographic SHA-256 integrity verification.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300 text-sm flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-sm flex items-center space-x-2">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload New Firmware Card */}
        <div className="lg:col-span-1 bg-white dark:bg-slate-900/60 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 space-y-4 shadow-xs">
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center space-x-2">
            <Upload className="h-4 w-4 text-[#1677ff]" />
            <span>Upload New Firmware</span>
          </h3>

          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Firmware Binary (.bin):</label>
              <input
                type="file"
                accept=".bin"
                onChange={e => setFile(e.target.files ? e.target.files[0] : null)}
                className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-[#1677ff] file:text-white hover:file:bg-blue-600 cursor-pointer"
              />
              <p className="text-[10px] text-slate-400 mt-1">Must be an ESP32 application image (magic byte 0xE9, max 2 MB).</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Version String:</label>
              <input
                type="text"
                value={version}
                onChange={e => setVersion(e.target.value)}
                placeholder="e.g. 1.1.0"
                required
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-hidden focus:border-[#1677ff]"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Release Notes:</label>
              <textarea
                rows={2}
                value={releaseNotes}
                onChange={e => setReleaseNotes(e.target.value)}
                placeholder="Key improvements or bug fixes"
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-hidden focus:border-[#1677ff]"
              />
            </div>

            <button
              type="submit"
              disabled={uploading || !file}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-[#1677ff] hover:bg-blue-600 text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition"
            >
              <Upload className="h-3.5 w-3.5" />
              <span>{uploading ? 'Verifying & Storing...' : 'Upload Firmware'}</span>
            </button>
          </form>
        </div>

        {/* Deploy & Releases Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Targeted Rollout Card */}
          <div className="bg-white dark:bg-slate-900/60 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800 space-y-4 shadow-xs">
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center space-x-2">
              <Send className="h-4 w-4 text-emerald-500" />
              <span>Initiate OTA Deployment</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Select Firmware Release:</label>
                <select
                  value={deployVersion}
                  onChange={e => setDeployVersion(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-hidden focus:border-[#1677ff]"
                >
                  {releases.map(r => (
                    <option key={r.id} value={r.version}>v{r.version} ({Math.round(r.file_size / 1024)} KB)</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Target Device:</label>
                <select
                  value={deployTarget}
                  onChange={e => setDeployTarget(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-hidden focus:border-[#1677ff]"
                >
                  <option value="ALL">All Online Paired Devices ({devices.length})</option>
                  {devices.map(d => (
                    <option key={d.id} value={d.id}>{d.name} ({d.id})</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={handleDeploy}
              disabled={deploying || releases.length === 0}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition"
            >
              <Send className="h-3.5 w-3.5" />
              <span>{deploying ? 'Broadcasting OTA Frame...' : 'Deploy Update to Target'}</span>
            </button>
          </div>

          {/* Firmware Catalog Table */}
          <div className="bg-white dark:bg-slate-900/40 p-6 rounded-2xl border border-slate-200/90 dark:border-slate-800/80 space-y-4 shadow-xs">
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center space-x-2">
              <ShieldCheck className="h-4 w-4 text-[#1677ff]" />
              <span>Firmware Catalog ({releases.length})</span>
            </h3>

            {releases.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-6">No firmware releases uploaded yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                    <tr>
                      <th className="py-2.5 font-semibold">Version</th>
                      <th className="py-2.5 font-semibold">Target</th>
                      <th className="py-2.5 font-semibold">Size</th>
                      <th className="py-2.5 font-semibold">SHA-256 Hash</th>
                      <th className="py-2.5 font-semibold">Uploaded</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                    {releases.map(r => (
                      <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                        <td className="py-3 font-semibold text-slate-800 dark:text-slate-200">v{r.version}</td>
                        <td className="py-3 text-slate-400">{r.target_hardware}</td>
                        <td className="py-3 text-slate-300 font-mono">{Math.round(r.file_size / 1024)} KB</td>
                        <td className="py-3 font-mono text-[11px] text-slate-400" title={r.sha256}>
                          {r.sha256.substring(0, 16)}...
                        </td>
                        <td className="py-3 text-slate-500 text-[11px]">
                          {new Date(r.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
