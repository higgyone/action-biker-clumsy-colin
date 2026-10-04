"""Draw every full-screen (6912-byte) block of a .tap file as a PNG.

Usage: python tools/tap_screens.py GAME.tap OUT_PREFIX     # writes OUT_PREFIX_1.png, OUT_PREFIX_2.png, ...
"""
import sys
import numpy as np
from PIL import Image


def rgb(index, bright):
    level = 255 if bright else 205
    return (level if index & 2 else 0, level if index & 4 else 0, level if index & 1 else 0)


def draw(scr):
    img = np.zeros((192, 256, 3), dtype=np.uint8)
    for cy in range(24):
        for cx in range(32):
            attr = scr[6144 + cy * 32 + cx]
            bright = bool(attr & 0x40)
            ink, paper = rgb(attr & 7, bright), rgb((attr >> 3) & 7, bright)
            for r in range(8):
                y = cy * 8 + r
                byte = scr[((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + cx]
                for x in range(8):
                    img[y, cx * 8 + x] = ink if byte & (0x80 >> x) else paper
    return img


data = open(sys.argv[1], "rb").read()
pos, found = 0, 0
while pos < len(data):
    length = data[pos] | data[pos + 1] << 8
    block = data[pos + 2:pos + 2 + length]
    pos += 2 + length
    if len(block) == 6914 and block[0] == 255:       # flag byte + 6912 data + parity
        found += 1
        out = f"{sys.argv[2]}_{found}.png"
        Image.fromarray(draw(block[1:6913])).resize((768, 576), Image.NEAREST).save(out)
        print("wrote", out)
