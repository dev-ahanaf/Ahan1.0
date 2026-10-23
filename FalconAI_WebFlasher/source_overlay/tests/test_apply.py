import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_falcon import (apply, board_json, generate_header, patch_cmake,
                          patch_kconfig, validate_url, PROFILES)

KCONFIG = '''menu "Xiaozhi Assistant"
choice BOARD_TYPE
    config BOARD_TYPE_BREAD_COMPACT_ESP32
        bool "ESP32"
endchoice
choice DISPLAY_OLED_TYPE
    depends on BOARD_TYPE_BREAD_COMPACT_ESP32 || BOARD_TYPE_HU_087
    config OLED_SSD1306_128X64
        bool "OLED"
endchoice
endmenu
'''
CMAKE = '''if(CONFIG_BOARD_TYPE_BREAD_COMPACT_WIFI)
    set(BOARD_DIR "bread-compact-wifi")
elseif(CONFIG_BOARD_TYPE_BREAD_COMPACT_ESP32)
    set(BOARD_DIR "bread-compact-esp32")
endif()
'''
HEADER = '''#ifndef _BOARD_CONFIG_H_
#define _BOARD_CONFIG_H_
''' + '\n'.join('#define %s GPIO_NUM_1' % k for k in PROFILES['myvoice']) + '\n#endif\n'

class Tests(unittest.TestCase):
    def test_kconfig_patch_idempotent(self):
        once = patch_kconfig(KCONFIG)
        self.assertEqual(patch_kconfig(once), once)
        self.assertIn('BOARD_TYPE_FALCON_AI_ESP32', once)
    def test_cmake_patch_idempotent(self):
        once = patch_cmake(CMAKE)
        self.assertEqual(patch_cmake(once), once)
    def test_header(self):
        res = generate_header(HEADER, 'myvoice')
        self.assertIn('#define DISPLAY_SDA_PIN GPIO_NUM_18', res)
        self.assertIn('#define AUDIO_I2S_MIC_GPIO_DIN GPIO_NUM_33', res)
        self.assertIn('#define TOUCH_BUTTON_GPIO GPIO_NUM_27', res)
        self.assertIn('#define ASR_BUTTON_GPIO GPIO_NUM_NC', res)
    def test_size_and_url(self):
        js = board_json('http://192.168.1.100:8002/xiaozhi/ota/', '4MB')
        opts = js['builds'][0]['sdkconfig_append']
        self.assertTrue(any('v2/4m.csv' in x for x in opts))
        with self.assertRaises(ValueError): validate_url('https://api.tenclass.net/xiaozhi/ota/')
        validate_url('http://192.168.1.100:8002/xiaozhi/ota/')
    def test_apply_preserves_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            board = root/'main'/'boards'/'bread-compact-esp32'
            board.mkdir(parents=True)
            (board/'config.h').write_text(HEADER)
            (board/'config.json').write_text('{"type":"bread-compact-esp32"}')
            (board/'my_board.cc').write_text('#define TAG "Original"\nclass Test {};\n')
            (root/'main'/'Kconfig.projbuild').write_text(KCONFIG)
            (root/'main'/'CMakeLists.txt').write_text(CMAKE)
            (root/'scripts').mkdir()
            (root/'scripts'/'build.py').write_text('# mock\n')
            url = 'http://192.168.1.100:8002/xiaozhi/ota/'
            msg = apply(root, 'myvoice', '4MB', url)
            target = root/'main'/'boards'/'falcon-ai-esp32'
            self.assertTrue(target.is_dir())
            self.assertEqual((board/'config.h').read_text(), HEADER)
            self.assertIn('FalconAI', (target/'my_board.cc').read_text())
            self.assertEqual(json.loads((target/'config.json').read_text())['type'], 'falcon-ai-esp32')
            self.assertIn('Backups:', '\n'.join(msg))
            with self.assertRaises(ValueError): apply(root, 'myvoice', '4MB', url)

if __name__ == '__main__':
    unittest.main()
