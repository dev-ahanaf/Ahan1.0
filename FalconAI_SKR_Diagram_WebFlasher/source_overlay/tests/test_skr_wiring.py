import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from apply_falcon import PROFILES

class SkRDiagram(unittest.TestCase):
    def test_pin_map(self):
        p=PROFILES['xiaozhi']
        for key, value in {
            'AUDIO_I2S_MIC_GPIO_SCK':26,
            'AUDIO_I2S_MIC_GPIO_WS':25,
            'AUDIO_I2S_MIC_GPIO_DIN':32,
            'AUDIO_I2S_SPK_GPIO_DOUT':33,
            'AUDIO_I2S_SPK_GPIO_BCLK':14,
            'AUDIO_I2S_SPK_GPIO_LRCK':27,
            'DISPLAY_SDA_PIN':4,
            'DISPLAY_SCL_PIN':15,
            'BOOT_BUTTON_GPIO':0,
            'LAMP_GPIO':18}.items():
            self.assertEqual(p[key], value)

if __name__ == '__main__': unittest.main()
