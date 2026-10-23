#!/usr/bin/env python3
"""Add a separate Falcon AI board to an existing xiaozhi-esp32 checkout.

No remote network activity, no git reset, no flashing, no deletion of originals.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

BOARD = 'falcon-ai-esp32'
MACRO = 'BOARD_TYPE_FALCON_AI_ESP32'
BASE = 'bread-compact-esp32'

PROFILES = {
    'myvoice': {
        'AUDIO_I2S_MIC_GPIO_WS': 25, 'AUDIO_I2S_MIC_GPIO_SCK': 26,
        'AUDIO_I2S_MIC_GPIO_DIN': 33, 'AUDIO_I2S_SPK_GPIO_DOUT': 22,
        'AUDIO_I2S_SPK_GPIO_BCLK': 14, 'AUDIO_I2S_SPK_GPIO_LRCK': 13,
        'DISPLAY_SDA_PIN': 18, 'DISPLAY_SCL_PIN': 19,
        'BOOT_BUTTON_GPIO': 0, 'TOUCH_BUTTON_GPIO': 27,
        'ASR_BUTTON_GPIO': None, 'LAMP_GPIO': 23,
    },
    # Matches the user's SKR diagram and upstream bread-compact board.
    'xiaozhi': {
        'AUDIO_I2S_MIC_GPIO_WS': 25, 'AUDIO_I2S_MIC_GPIO_SCK': 26,
        'AUDIO_I2S_MIC_GPIO_DIN': 32, 'AUDIO_I2S_SPK_GPIO_DOUT': 33,
        'AUDIO_I2S_SPK_GPIO_BCLK': 14, 'AUDIO_I2S_SPK_GPIO_LRCK': 27,
        'DISPLAY_SDA_PIN': 4, 'DISPLAY_SCL_PIN': 15,
        'BOOT_BUTTON_GPIO': 0, 'TOUCH_BUTTON_GPIO': 5,
        'ASR_BUTTON_GPIO': 19, 'LAMP_GPIO': 18,
    },
}


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('OTA URL must be a valid http(s) endpoint without user credentials')
    if any(ch in url for ch in '\n\r\"\\'):
        raise ValueError('OTA URL contains unsupported characters')
    if not parsed.path.endswith('/'):
        raise ValueError('OTA URL must end with / (example /xiaozhi/ota/)')
    if 'tenclass.net' in parsed.netloc or 'xiaozhi.me' in parsed.netloc:
        raise ValueError('Use YOUR self-hosted OTA endpoint, not the official XiaoZhi cloud')


def set_define(content: str, key: str, value: int | None) -> str:
    pattern = re.compile(r'(?m)^(\s*#define\s+' + re.escape(key) + r'\s+)([^\r\n]+)$')
    repl_val = 'GPIO_NUM_NC' if value is None else 'GPIO_NUM_' + str(value)
    new, count = pattern.subn(lambda m: m.group(1) + repl_val, content)
    if count != 1:
        raise ValueError(f'Unsupported upstream config.h: expected one #define {key}, found {count}')
    return new


def generate_header(source: str, profile: str) -> str:
    result = source
    # Only GPIO fields are touched; preserve codec rates, display format and upstream structure.
    for name, value in PROFILES[profile].items():
        result = set_define(result, name, value)
    return '// Falcon AI personal board configuration; profile: ' + profile + '\n' + result


def patch_kconfig(content: str) -> str:
    if f'config {MACRO}' not in content:
        anchor = '    config BOARD_TYPE_BREAD_COMPACT_ESP32\n'
        if content.count(anchor) != 1:
            raise ValueError('Kconfig board selector changed; manual adaptation required')
        entry = f'    config {MACRO}\n        bool "Falcon AI - Personal ESP32 DevKit"\n        depends on IDF_TARGET_ESP32\n'
        content = content.replace(anchor, entry + anchor, 1)
    a = content.find('choice DISPLAY_OLED_TYPE')
    b = content.find('endchoice', a)
    if a < 0 or b < 0:
        raise ValueError('Cannot find OLED choice in upstream Kconfig')
    section = content[a:b]
    if MACRO not in section:
        if 'BOARD_TYPE_BREAD_COMPACT_ESP32' not in section:
            raise ValueError('Cannot find bread-compact OLED dependency')
        section = section.replace('BOARD_TYPE_BREAD_COMPACT_ESP32',
                                  f'BOARD_TYPE_BREAD_COMPACT_ESP32 || {MACRO}', 1)
        content = content[:a] + section + content[b:]
    return content


def patch_cmake(content: str) -> str:
    if f'CONFIG_{MACRO}' not in content:
        anchor = 'elseif(CONFIG_BOARD_TYPE_BREAD_COMPACT_ESP32)'
        if content.count(anchor) != 1:
            raise ValueError('CMake board selector changed; manual adaptation required')
        block = (f'elseif(CONFIG_{MACRO})\n'
                 f'    set(BOARD_DIR "{BOARD}")\n'
                 '    set(BUILTIN_TEXT_FONT font_noto_sans_basic_14_1)\n'
                 '    set(BUILTIN_ICON_FONT font_material_symbols_14_1)\n')
        content = content.replace(anchor, block + anchor, 1)
    return content


def update_board_sources(folder: Path) -> None:
    """Customize non-critical boot logs; avoid changing upstream audio protocol."""
    for filepath in folder.rglob('*.cc'):
        source = filepath.read_text(encoding='utf-8')
        source = re.sub(r'(?m)^(#define\s+TAG\s+)"[^"]+"',
                        r'\g<1>"FalconAI"', source, count=1)
        if 'InitializeButtons();' in source and 'Falcon AI personalized firmware' not in source:
            source = source.replace('InitializeButtons();',
                  'InitializeButtons();\n        ESP_LOGI(TAG, "Falcon AI personalized firmware - ESP32");', 1)
        # Lamp is not installed on this user's hardware. Avoid driving a pin by default.
        # Retain upstream method structure; safely comment out only the optional lamp instance.
        source = re.sub(r'(?m)^(\s*)static\s+LampController\s+\w+\s*\([^;]*\);',
                        r'\1// Falcon AI: optional lamp output disabled (not wired).', source)
        filepath.write_text(source, encoding='utf-8')


def board_json(url: str, flash: str) -> dict:
    options = [
        'CONFIG_OLED_SSD1306_128X64=y',
        f'CONFIG_OTA_URL="{url}"',
        f'CONFIG_ESPTOOLPY_FLASHSIZE_{flash}=y',
    ]
    if flash != '16MB':
        options.append(f'CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions/v2/{flash.lower().replace("mb", "m")}.csv"')
    return {'type': BOARD, 'target': 'esp32', 'builds': [{
        'name': BOARD, 'sdkconfig_append': options
    }]}


def is_target_repo(root: Path) -> None:
    files = [root/'main'/'Kconfig.projbuild', root/'main'/'CMakeLists.txt',
             root/'main'/'boards'/BASE/'config.h', root/'main'/'boards'/BASE/'config.json',
             root/'scripts'/'build.py']
    absent = [str(f) for f in files if not f.is_file()]
    if absent:
        raise ValueError('This does not look like a compatible xiaozhi-esp32 checkout. Missing:\n' + '\n'.join(absent))


def apply(repo: Path, profile: str, flash: str, url: str, dry_run: bool = False) -> list[str]:
    repo = repo.resolve()
    is_target_repo(repo)
    validate_url(url)
    original = repo/'main'/'boards'/BASE
    target = repo/'main'/'boards'/BOARD
    kconfig = repo/'main'/'Kconfig.projbuild'
    cmake = repo/'main'/'CMakeLists.txt'
    new_kconfig = patch_kconfig(kconfig.read_text(encoding='utf-8'))
    new_cmake = patch_cmake(cmake.read_text(encoding='utf-8'))
    new_header = generate_header((original/'config.h').read_text(encoding='utf-8'), profile)
    config = json.dumps(board_json(url, flash), indent=2, ensure_ascii=False) + '\n'
    summary = [f'Repository: {repo}', f'Board: {BOARD}', f'GPIO: {profile}',
               f'Flash size: {flash}', f'OTA URL: {url}']
    if target.exists():
        raise ValueError(f'{target} already exists. It was NOT overwritten. Inspect it manually.')
    if dry_run:
        return ['DRY RUN: no files changed'] + summary

    # Back up shared upstream files before touching them. Never reset git history.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = repo/'.falcon-backups'/stamp
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(kconfig, backup/'Kconfig.projbuild')
    shutil.copy2(cmake, backup/'CMakeLists.txt')
    shutil.copytree(original, target)
    try:
        (target/'config.h').write_text(new_header, encoding='utf-8')
        shutil.copy2(target/'README.md', target/'UPSTREAM_README.md') if (target/'README.md').is_file() else None
        (target/'README.md').write_text(
            '# Falcon AI Personal Board\n\nESP32 DevKit + INMP441 + MAX98357A + SSD1306 128x64.\n'
            f'GPIO profile: **{profile}**. OTA endpoint is your own server.\n'
            'Original bread-compact board is not modified. See the overlay ZIP README.\n', encoding='utf-8')
        (target/'config.json').write_text(config, encoding='utf-8')
        update_board_sources(target)
        kconfig.write_text(new_kconfig, encoding='utf-8')
        cmake.write_text(new_cmake, encoding='utf-8')
    except Exception:
        # Restore only the two files that this operation may have modified.
        shutil.copy2(backup/'Kconfig.projbuild', kconfig)
        shutil.copy2(backup/'CMakeLists.txt', cmake)
        # The custom directory is retained for inspection, rather than silently destroyed.
        raise
    return summary + [f'Backups: {backup}', 'Only newly copied board plus Kconfig/CMake were modified.']


def main() -> None:
    parser = argparse.ArgumentParser(description='Add personal Falcon AI board to existing XiaoZhi firmware repo')
    parser.add_argument('--repo', type=Path, required=True, help='Path to your cloned xiaozhi-esp32 directory')
    parser.add_argument('--ota-url', required=True, help='Own server OTA endpoint, e.g. http://192.168.1.100:8002/xiaozhi/ota/')
    parser.add_argument('--profile', choices=tuple(PROFILES), default='xiaozhi')
    parser.add_argument('--flash-size', choices=('4MB', '8MB', '16MB'), default='4MB')
    parser.add_argument('--dry-run', action='store_true')
    a = parser.parse_args()
    try:
        for line in apply(a.repo, a.profile, a.flash_size, a.ota_url, a.dry_run):
            print(line)
    except (ValueError, OSError) as exc:
        print('Falcon AI setup stopped safely: ' + str(exc), file=sys.stderr)
        sys.exit(2)

if __name__ == '__main__':
    main()
