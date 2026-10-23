'use strict';
(() => {
  const $ = (id) => document.getElementById(id);
  const info = $('firmware-details');
  const badge = $('firmware-badge');
  const blocked = $('blocked-container');
  const ready = $('ready-container');
  const ack = $('confirm-wiring');
  const gated = $('action-gated');
  const live = $('action-live');
  const install = $('esp-install');
  const download = $('download-firmware');

  function mark(text, state) {
    badge.textContent = state === 'ready' ? 'AVAILABLE' : state === 'missing' ? 'NOT PUBLISHED' : 'CHECKING';
    badge.className = `state-badge ${state}`;
    info.textContent = text;
  }
  function explain(message) {
    blocked.hidden = false;
    blocked.textContent = message;
    ready.hidden = true;
    download.hidden = true;
    mark('No verified image available', 'missing');
  }
  function updateConsent() {
    const checked = ack.checked;
    gated.hidden = checked;
    live.hidden = !checked;
  }
  function safeFirmwarePath(path) {
    // Relative filename only; the firmware files must be hosted on the same origin.
    return typeof path === 'string' && /^[-_a-zA-Z0-9.]+\.bin$/.test(path) && path !== '..';
  }
  async function checkFirmware() {
    if (location.protocol === 'file:') {
      explain('Open this website on HTTPS (or http://localhost for testing), not directly as an HTML file.');
      return;
    }
    if (!window.isSecureContext || !('serial' in navigator)) {
      explain('Use a desktop Chrome or Microsoft Edge browser on HTTPS (localhost also works). USB serial is unavailable in this browser/context.');
      return;
    }
    try {
      const url = new URL('./firmware/manifest.json', document.baseURI);
      const response = await fetch(url, {cache: 'no-store'});
      if (!response.ok) throw new Error('No published manifest found');
      const manifest = await response.json();
      const build = manifest.builds?.find((entry) => entry.chipFamily === 'ESP32');
      if (!build || !Array.isArray(build.parts) || build.parts.length !== 1 ||
          build.parts[0].offset !== 0 || !safeFirmwarePath(build.parts[0].path)) {
        throw new Error('Invalid ESP32 merged-firmware manifest');
      }
      const path = new URL('./firmware/' + build.parts[0].path, document.baseURI);
      const head = await fetch(path, {method:'HEAD', cache:'no-store'});
      if (!head.ok) throw new Error('Firmware .bin is missing');
      const releaseResponse = await fetch(new URL('./firmware/release.json', document.baseURI), {cache:'no-store'});
      if (!releaseResponse.ok) throw new Error('Release metadata is missing');
      const release = await releaseResponse.json();
      const bytes = Number(head.headers.get('Content-Length'));
      if (release.chip !== 'ESP32' || release.profile !== 'myvoice' && release.profile !== 'xiaozhi' ||
          typeof release.version !== 'string' || release.version !== manifest.version ||
          release.image !== build.parts[0].path ||
          !Number.isSafeInteger(release.size_bytes) || release.size_bytes <= 4096 ||
          (bytes && bytes !== release.size_bytes)) {
        throw new Error('Firmware metadata mismatch');
      }
      $('firmware-name').textContent = manifest.name || 'Falcon AI ESP32';
      $('board-profile').textContent = release.profile === 'myvoice' ? 'MyVoice' : 'XiaoZhi';
      if (release.profile === 'xiaozhi') {
        $('mic-pins').textContent = 'INMP441 / GPIO 26, 25, 32';
        $('speaker-pins').textContent = 'MAX98357A / GPIO 14, 27, 33';
        $('oled-pins').textContent = 'SSD1306 / SDA 4, SCL 15';
        $('button-pin').textContent = 'GPIO 5 (touch input)';
      }
      mark(`v${manifest.version} · ${release.flash_size} · ${release.profile} profile · ${(release.size_bytes/1048576).toFixed(2)} MiB`, 'ready');
      blocked.hidden = true;
      ready.hidden = false;
      ack.checked = false;
      ack.addEventListener('change', updateConsent);
      install.manifest = url.toString();
      updateConsent();
      download.href = path.toString();
      download.hidden = false;
    } catch (error) {
      explain('The firmware has not been published yet. Site owner: build Falcon AI first, then run tools/publish_firmware.py to create firmware/manifest.json and firmware/*.bin. (' + (error.message || 'Unknown error') + ')');
    }
  }
  checkFirmware();
})();
