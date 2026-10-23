#!/usr/bin/env python3
"""Publish a separately built, *merged* ESP32 firmware image to a static Web Flasher.

This tool DOES NOT compile ESP-IDF source code. It validates an image and creates
web assets for ESP Web Tools. Never publish private credentials inside a firmware.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

FLASH_SIZES = {'4MB': 4 * 1024 * 1024, '8MB': 8 * 1024 * 1024,
               '16MB': 16 * 1024 * 1024}


def check_merged_image(path: Path, flash_size: str) -> tuple[int, str]:
    if not path.is_file() or path.suffix.lower() != '.bin':
        raise ValueError(f'Expected a real compiled merged .bin file: {path}')
    size = path.stat().st_size
    if size < 0x1100:
        raise ValueError('Image too small to contain ESP32 bootloader at 0x1000')
    if size > FLASH_SIZES[flash_size]:
        raise ValueError(f'Image too large for {flash_size} flash: {size} bytes')
    with path.open('rb') as f:
        f.seek(0x1000)
        header = f.read(4)
    if len(header) != 4 or header[0] != 0xE9 or not (1 <= header[1] <= 16) or header[2] > 3:
        raise ValueError('Missing valid ESP32 bootloader image header at 0x1000. '
                         'Do not use application-only .bin here. Merge all ESP-IDF partitions first.')
    digest = hashlib.sha256()
    with path.open('rb') as f:
        while buf := f.read(1024 * 1024):
            digest.update(buf)
    return size, digest.hexdigest()


def merge_idf_build(build_dir: Path, out: Path, flash_size: str) -> None:
    """Use ESP-IDF's generated flashing offsets, never hardcode app/partition offsets."""
    conf_file = build_dir / 'flasher_args.json'
    if not conf_file.is_file():
        raise ValueError(f'Missing {conf_file} - first build your actual firmware with idf.py build')
    cfg = json.loads(conf_file.read_text(encoding='utf-8'))
    flash_files = cfg.get('flash_files')
    if not isinstance(flash_files, dict) or len(flash_files) < 2:
        raise ValueError('No usable flash_files map in flasher_args.json')
    command = [sys.executable, '-m', 'esptool', '--chip', 'esp32', 'merge-bin',
               '-o', str(out), '--flash-mode', 'dio', '--flash-freq', '40m',
               '--flash-size', flash_size]
    locations: list[tuple[int, Path]] = []
    for address, relative in flash_files.items():
        offset = int(address, 0)
        binary = (build_dir / relative).resolve()
        if not binary.is_file():
            raise ValueError(f'Build output listed in flasher_args.json not found: {binary}')
        if offset < 0 or offset + binary.stat().st_size > FLASH_SIZES[flash_size]:
            raise ValueError(f'Flash area out of range: 0x{offset:x} {binary.name}')
        locations.append((offset, binary))
    locations.sort()
    for i in range(len(locations)-1):
        offset, path = locations[i]
        if offset + path.stat().st_size > locations[i+1][0]:
            raise ValueError(f'Flash parts overlap at 0x{offset:x}')
    for offset, binary in locations:
        command.extend([hex(offset), str(binary)])
    try:
        subprocess.run(command, check=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        raise RuntimeError('Could not merge using esptool. Install with: python -m pip install esptool') from exc


def publish(image: Path, out_dir: Path, *, version: str, flash_size: str,
            profile: str, board: str = 'ESP32 DevKit / WROOM-32') -> dict:
    if not version or len(version) > 64 or any(ch not in '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-_' for ch in version):
        raise ValueError('Invalid version (use letters, numbers, dots, dashes or underscores)')
    if flash_size not in FLASH_SIZES:
        raise ValueError('flash-size must be 4MB, 8MB or 16MB')
    if profile not in ('myvoice','xiaozhi'):
        raise ValueError('Unknown GPIO profile')
    size, digest = check_merged_image(image, flash_size)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = 'falcon-ai-esp32.bin'
    destination = out_dir / filename
    # Store binary before creating manifest; frontend never offers an unpublished image.
    if image.resolve() != destination.resolve():
        temp_binary = out_dir / (filename + '.uploading')
        shutil.copyfile(image, temp_binary)
        temp_binary.replace(destination)
    manifest = {
        'name': 'Falcon AI Personal ESP32',
        'version': version,
        'new_install_prompt_erase': True,
        'builds': [{
            'chipFamily': 'ESP32',
            'improv': False,
            'parts': [{'path': filename, 'offset': 0}]
        }]
    }
    release = {
        'chip': 'ESP32',
        'board': board,
        'profile': profile,
        'flash_size': flash_size,
        'image': filename,
        'version': version,
        'size_bytes': size,
        'sha256': digest,
        'published_utc': datetime.now(timezone.utc).isoformat()
    }
    for name, content in [('release.json', release),('manifest.json', manifest)]:
        target = out_dir / name
        tmp = out_dir / (name + '.uploading')
        tmp.write_text(json.dumps(content, indent=2) + '\n', encoding='utf-8')
        tmp.replace(target)
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--merged', type=Path, help='Compiled merged-binary.bin from your firmware build')
    group.add_argument('--idf-build', type=Path, help='ESP-IDF build/ directory containing flasher_args.json')
    parser.add_argument('--version', required=True, help='Published firmware version, e.g. 0.1.0')
    parser.add_argument('--flash-size', choices=FLASH_SIZES, required=True)
    parser.add_argument('--profile', choices=['myvoice','xiaozhi'], required=True)
    parser.add_argument('--site-dir', type=Path, default=Path(__file__).resolve().parents[1] / 'site')
    args = parser.parse_args()
    try:
        if args.idf_build:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / 'merged-binary.bin'
                merge_idf_build(args.idf_build.resolve(), path, args.flash_size)
                result = publish(path, args.site_dir / 'firmware', version=args.version,
                                 flash_size=args.flash_size, profile=args.profile)
        else:
            result = publish(args.merged.resolve(), args.site_dir / 'firmware',
                             version=args.version, flash_size=args.flash_size, profile=args.profile)
        print(f'Published {result["image"]} for {result["chip"]}, {result["flash_size"]}, GPIO profile: {result["profile"]}')
        print(f'SHA256: {result["sha256"]}')
        print(f'Website directory: {(args.site_dir).resolve()}')
        print('Deploy this site directory to an HTTPS domain, then test USB flashing on real hardware.')
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
