import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from publish_firmware import check_merged_image, publish, merge_idf_build


def fake_header(path, size=1024*1024):
    # TEST FIXTURE ONLY. Never ship mock firmware as a flashable image.
    payload = bytearray(b'\xff' * size)
    payload[0x1000:0x1004] = bytes([0xe9, 0x04, 0x02, 0x20])
    path.write_bytes(payload)

class PublisherTests(unittest.TestCase):
    def test_source_zip_not_flashable(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'firmware.zip'; p.write_bytes(b'PK\x03\x04fake')
            with self.assertRaises(ValueError):
                check_merged_image(p,'4MB')
    def test_application_only_image_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'app.bin'; p.write_bytes(b'\xe9'+b'\xff'*(0x4000-1))
            with self.assertRaises(ValueError):
                check_merged_image(p,'4MB')
    def test_create_manifest_release_bin(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); firmware=root/'real_build_merged.bin'; fake_header(firmware)
            release=publish(firmware,root/'site'/'firmware',version='0.1.0',flash_size='4MB',profile='myvoice')
            manifest=json.loads((root/'site'/'firmware'/'manifest.json').read_text())
            self.assertEqual(manifest['builds'][0]['parts'],[{'path':'falcon-ai-esp32.bin','offset':0}])
            self.assertEqual(release['size_bytes'],1024*1024)
            self.assertTrue(release['sha256'])
            self.assertTrue((root/'site'/'firmware'/'falcon-ai-esp32.bin').is_file())
    def test_reject_oversize_wrong_profile(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'big.bin'; fake_header(p,4*1024*1024+1)
            with self.assertRaises(ValueError): check_merged_image(p,'4MB')
            with self.assertRaises(ValueError): publish(p,Path(t)/'site',version='0.1.0',flash_size='8MB',profile='unknown')
    def test_missing_idf_build_fail(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError): merge_idf_build(Path(t),Path(t)/'merged.bin','4MB')

if __name__ == '__main__':
    unittest.main()
