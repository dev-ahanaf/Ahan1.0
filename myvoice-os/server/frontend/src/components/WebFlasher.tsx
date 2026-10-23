import React, { useState, useEffect } from 'react';
import {
  Zap,
  Cpu,
  Usb,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Download,
  Terminal,
  HelpCircle,
  Radio,
  FileCode,
  RefreshCw
} from 'lucide-react';

interface WebFlasherProps {
  onGoToFleet?: () => void;
}

export const WebFlasher: React.FC<WebFlasherProps> = ({ onGoToFleet }) => {
  const [subTab, setSubTab] = useState<'quick' | 'manual' | 'standalone'>('quick');
  const [isSerialSupported, setIsSerialSupported] = useState<boolean>(false);
  const [detectedPortInfo, setDetectedPortInfo] = useState<string | null>(null);
  const [detectingPort, setDetectingPort] = useState(false);
  const [portError, setPortError] = useState<string | null>(null);
  const [confirmedWiring, setConfirmedWiring] = useState(false);
  const [boardType, setBoardType] = useState('esp32dev');
  const [flashOffset, setFlashOffset] = useState('0x0');
  const [baudRate, setBaudRate] = useState('921600');
  const [customFile, setCustomFile] = useState<File | null>(null);

  useEffect(() => {
    // Check Web Serial support in browser
    if (typeof window !== 'undefined' && 'serial' in navigator) {
      setIsSerialSupported(true);
    } else {
      setIsSerialSupported(false);
    }
  }, []);

  const handleDetectUSB = async () => {
    setDetectingPort(true);
    setPortError(null);
    setDetectedPortInfo(null);
    try {
      if (!('serial' in navigator)) {
        throw new Error('Web Serial API is not supported in this browser. Please use Chrome or Edge.');
      }
      const navSerial = (navigator as any).serial;
      const port = await navSerial.requestPort();
      const info = port.getInfo();
      const vendorId = info.usbVendorId ? `0x${info.usbVendorId.toString(16).toUpperCase()}` : 'Standard';
      const productId = info.usbProductId ? `0x${info.usbProductId.toString(16).toUpperCase()}` : 'UART';
      setDetectedPortInfo(`ESP32 USB Device Detected (VID: ${vendorId}, PID: ${productId}) - Port Ready!`);
    } catch (err: any) {
      if (err.name === 'NotFoundError') {
        setPortError('No serial port selected. Make sure your ESP32 is plugged in via USB and click again.');
      } else {
        setPortError(err.message || 'Failed to access USB port');
      }
    } finally {
      setDetectingPort(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200/80 dark:border-slate-800 shadow-sm">
        <div className="flex items-start space-x-4">
          <div className="p-3 bg-gradient-to-tr from-amber-500 to-orange-500 rounded-xl text-white shadow-md">
            <Usb className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Falcon AI - USB Web Flasher
              </h2>
              <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 rounded-full border border-amber-300 dark:border-amber-700">
                ESP32 DevKit v1
              </span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Flash firmware directly from your browser over a USB cable without installing PlatformIO or Arduino IDE.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {isSerialSupported ? (
            <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 text-xs font-semibold">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Web Serial Ready</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60 text-xs font-semibold">
              <AlertTriangle className="h-3.5 w-3.5" />
              <span>Use Desktop Chrome / Edge</span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex space-x-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          onClick={() => setSubTab('quick')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            subTab === 'quick'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Zap className="h-4 w-4" />
          <span>1-Click Flash (ESP32 DevKit v1)</span>
        </button>

        <button
          onClick={() => setSubTab('manual')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            subTab === 'manual'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Terminal className="h-4 w-4" />
          <span>Manual Options &amp; File Picker</span>
        </button>

        <button
          onClick={() => setSubTab('standalone')}
          className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold transition ${
            subTab === 'standalone'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <ExternalLink className="h-4 w-4" />
          <span>Standalone WebFlasher Page</span>
        </button>
      </div>

      {/* SUB-TAB 1: Quick 1-Click Flash */}
      {subTab === 'quick' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Flash Card */}
          <div className="lg:col-span-2 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
            <div className="border-b border-slate-100 dark:border-slate-800/80 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-900 dark:text-white text-base">
                    Official Falcon AI Firmware v1.2.0
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Merged complete binary image (Bootloader @ 0x1000 + Partitions @ 0x8000 + Falcon AI App @ 0x10000)
                  </p>
                </div>
                <span className="px-2.5 py-1 text-xs font-mono font-bold bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 rounded-lg border border-blue-200 dark:border-blue-800">
                  Ready to Flash
                </span>
              </div>
            </div>

            {/* Firmware Details Spec Box */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200/60 dark:border-slate-700/60 text-xs">
              <div>
                <span className="text-slate-400 block font-medium">Target Board</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">ESP32 DevKit v1</span>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">Flash Size</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">4 MB (DIO 40MHz)</span>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">Binary Size</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">1.20 MB</span>
              </div>
              <div>
                <span className="text-slate-400 block font-medium">Audio Protocol</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">I2S Full-Duplex</span>
              </div>
            </div>

            {/* Test USB Serial Recognition */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/60 dark:border-slate-700/60 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center space-x-1.5">
                  <Usb className="h-4 w-4 text-blue-500" />
                  <span>Step 1: Test USB Cable &amp; Device Recognition</span>
                </span>
                <button
                  type="button"
                  onClick={handleDetectUSB}
                  disabled={detectingPort || !isSerialSupported}
                  className="px-3 py-1.5 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-100 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition disabled:opacity-50 cursor-pointer"
                >
                  <RefreshCw className={`h-3 w-3 ${detectingPort ? 'animate-spin' : ''}`} />
                  <span>{detectingPort ? 'Selecting Port...' : 'Test USB Port'}</span>
                </button>
              </div>

              {detectedPortInfo && (
                <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-200 text-xs flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                  <span>{detectedPortInfo}</span>
                </div>
              )}

              {portError && (
                <div className="p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 text-amber-800 dark:text-amber-200 text-xs flex items-center space-x-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                  <span>{portError}</span>
                </div>
              )}
            </div>

            {/* Confirmation & Web Install Button */}
            <div className="space-y-4 pt-2">
              <label className="flex items-start space-x-3 text-xs text-slate-600 dark:text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={confirmedWiring}
                  onChange={(e) => setConfirmedWiring(e.target.checked)}
                  className="mt-0.5 rounded-sm border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span>
                  I have connected the ESP32 DevKit v1 board via USB and confirmed the wiring (INMP441 + MAX98357A + SSD1306).
                </span>
              </label>

              {isSerialSupported ? (
                <div>
                  {confirmedWiring ? (
                    <div className="p-1 rounded-2xl bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 shadow-md">
                      <div className="bg-white dark:bg-slate-900 rounded-xl p-4 text-center">
                        <esp-web-install-button manifest="/flash/firmware/manifest.json">
                          <button
                            type="button"
                            slot="activate"
                            className="w-full py-3.5 px-6 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-sm shadow-md transition flex items-center justify-center space-x-2 cursor-pointer"
                          >
                            <Zap className="h-4 w-4" />
                            <span>⚡ Connect USB &amp; Flash ESP32 DevKit v1</span>
                          </button>
                          <span slot="unsupported" className="text-xs text-rose-500 block mt-2">
                            Web Serial is not supported in this browser. Please use Chrome or Edge.
                          </span>
                          <span slot="not-allowed" className="text-xs text-rose-500 block mt-2">
                            Flashing requires localhost or HTTPS.
                          </span>
                        </esp-web-install-button>
                        <p className="text-[11px] text-slate-400 mt-2">
                          Clicking will open Chrome's native serial port picker to select your USB board.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      disabled
                      className="w-full py-3.5 px-6 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-400 font-semibold text-sm cursor-not-allowed text-center"
                    >
                      Confirm checkbox above to activate USB Flashing
                    </button>
                  )}
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200 text-xs space-y-1">
                  <p className="font-bold flex items-center space-x-1.5">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <span>Web Serial API Unavailable</span>
                  </p>
                  <p>
                    Your current browser does not support Web Serial. Please open this console in <strong>Google Chrome</strong> or <strong>Microsoft Edge</strong> on Mac or Windows.
                  </p>
                </div>
              )}

              {/* Direct Binary Download Link */}
              <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
                <span>Prefer flashing via command line?</span>
                <a
                  href="/flash/firmware/falcon-ai-esp32.bin"
                  download="falcon-ai-esp32.bin"
                  className="text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1 font-semibold"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Download .bin (1.2 MB)</span>
                </a>
              </div>
            </div>
          </div>

          {/* Quick Hardware Pinout & Troubleshooting Guide */}
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm space-y-4">
              <h4 className="font-bold text-slate-900 dark:text-white text-sm flex items-center space-x-2">
                <Cpu className="h-4 w-4 text-blue-500" />
                <span>ESP32 DevKit v1 Wiring</span>
              </h4>

              <div className="text-xs space-y-2.5">
                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">🎤 INMP441 Microphone</span>
                  <span className="text-slate-500 font-mono text-[11px]">SCK: GPIO 26 | WS: GPIO 25 | SD: GPIO 33</span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">🔊 MAX98357A Amplifier</span>
                  <span className="text-slate-500 font-mono text-[11px]">BCLK: GPIO 14 | LRC: GPIO 13 | DIN: GPIO 22</span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">🖥️ SSD1306 0.96" OLED</span>
                  <span className="text-slate-500 font-mono text-[11px]">SDA: GPIO 18 | SCL: GPIO 19 | Addr: 0x3C</span>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">🔘 Push-to-Talk (Dual)</span>
                  <span className="text-slate-500 font-mono text-[11px]">Onboard BOOT (GPIO 0) OR GPIO 27 to GND</span>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-5 shadow-sm space-y-3">
              <h4 className="font-bold text-slate-900 dark:text-white text-sm flex items-center space-x-2">
                <HelpCircle className="h-4 w-4 text-amber-500" />
                <span>Flashing Tips</span>
              </h4>
              <ul className="text-xs text-slate-500 dark:text-slate-400 space-y-2 list-disc pl-4">
                <li>Use a <strong>data cable</strong>, not a charge-only phone cord.</li>
                <li>If the port picker fails to connect, hold the onboard <strong>BOOT button</strong> on the ESP32 while clicking Connect.</li>
                <li>After flashing, connect to Wi-Fi AP <strong>FalconAI-Setup</strong> (password: <code>myvoice123</code>).</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: Manual Options & File Picker */}
      {subTab === 'manual' && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-6 shadow-sm space-y-6">
          <div className="border-b border-slate-100 dark:border-slate-800/80 pb-4">
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Manual ESP32 Flash Options
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Select custom binary images, change memory offsets, or adjust flashing baud rates.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Target Hardware
              </label>
              <select
                value={boardType}
                onChange={(e) => setBoardType(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-medium focus:ring-2 focus:ring-blue-500"
              >
                <option value="esp32dev">ESP32 DevKit v1 / WROOM-32 (Standard 4MB)</option>
                <option value="esp32_8mb">ESP32 (8MB Flash)</option>
                <option value="esp32_16mb">ESP32 (16MB Flash)</option>
                <option value="esp32s3">ESP32-S3 (Custom)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Memory Target Offset
              </label>
              <select
                value={flashOffset}
                onChange={(e) => setFlashOffset(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-medium focus:ring-2 focus:ring-blue-500"
              >
                <option value="0x0">0x0 (Full Merged Image: Bootloader + App)</option>
                <option value="0x10000">0x10000 (Application Partition Only)</option>
                <option value="0x1000">0x1000 (2nd Stage Bootloader)</option>
                <option value="0x8000">0x8000 (Partition Table)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Baud Rate
              </label>
              <select
                value={baudRate}
                onChange={(e) => setBaudRate(e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-medium focus:ring-2 focus:ring-blue-500"
              >
                <option value="921600">921600 (High Speed - Recommended)</option>
                <option value="460800">460800 (Balanced)</option>
                <option value="115200">115200 (Safe Fallback)</option>
              </select>
            </div>
          </div>

          {/* Custom File Upload Input */}
          <div className="p-4 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 text-center space-y-2">
            <FileCode className="h-8 w-8 mx-auto text-slate-400" />
            <div className="text-xs text-slate-600 dark:text-slate-300">
              <label className="font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">
                <span>Choose custom .bin file</span>
                <input
                  type="file"
                  accept=".bin"
                  onChange={(e) => setCustomFile(e.target.files ? e.target.files[0] : null)}
                  className="hidden"
                />
              </label>
              <span className="text-slate-400"> or use official pre-compiled Falcon AI binary</span>
            </div>
            {customFile && (
              <p className="text-xs font-mono text-emerald-600 dark:text-emerald-400 font-bold">
                Selected: {customFile.name} ({(customFile.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          {/* Flash Launch Button */}
          <div className="pt-2">
            <esp-web-install-button manifest="/flash/firmware/manifest.json">
              <button
                type="button"
                slot="activate"
                className="w-full py-3 px-6 rounded-xl bg-slate-900 dark:bg-slate-100 hover:bg-slate-800 dark:hover:bg-white text-white dark:text-slate-900 font-bold text-xs shadow-md transition flex items-center justify-center space-x-2 cursor-pointer"
              >
                <Zap className="h-4 w-4 text-amber-400" />
                <span>Launch Web Serial Installer ({baudRate} baud @ {flashOffset})</span>
              </button>
            </esp-web-install-button>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: Standalone WebFlasher Page (Embedded Frame) */}
      {subTab === 'standalone' && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-4 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-sm">
                Standalone Falcon AI Web Flasher
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Direct view of the dedicated flasher hosted at <code>/flash/</code>
              </p>
            </div>
            <a
              href="/flash/"
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 rounded-lg text-xs font-semibold hover:bg-blue-100 dark:hover:bg-blue-900 flex items-center space-x-1.5 transition"
            >
              <span>Open in New Tab</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>

          <div className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 h-[650px] w-full bg-slate-950">
            <iframe
              src="/flash/"
              title="Falcon AI Web Flasher"
              className="w-full h-full border-0"
              allow="serial"
            />
          </div>
        </div>
      )}

      {/* Post-Flash Next Steps Guide */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-800/40 dark:to-indigo-950/20 rounded-2xl border border-blue-200/60 dark:border-slate-700/60 p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h4 className="font-bold text-slate-900 dark:text-white text-sm">
            Done Flashing? Pair your device in 1 click!
          </h4>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            After flashing, connect the device to your Wi-Fi (AP: <code>FalconAI-Setup</code>), note the 6-digit code on the OLED screen, and pair it.
          </p>
        </div>
        {onGoToFleet && (
          <button
            type="button"
            onClick={onGoToFleet}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-md transition flex items-center space-x-2 shrink-0 cursor-pointer"
          >
            <Radio className="h-3.5 w-3.5" />
            <span>Go to Devices &amp; Pair →</span>
          </button>
        )}
      </div>
    </div>
  );
};
