"""Draw the loading screens of the tape as PNGs.

Usage: python tools/tap_screens.py GAME.tap OUT_PREFIX     # writes OUT_PREFIX_1.png, OUT_PREFIX_2.png, OUT_PREFIX_3.png
       (GAME can be a .tap, a .tzx or a .zip of one; with no GAME the usual places are searched, as tools/extract_assets.py does)

The loader shows three screens, in this order: the cover (the first 6912 bytes of the tape's 7020-byte block: the last 108 bytes are the loader's own
code), the KP Skips advert and the title (blocks of exactly 6912 bytes). tools/extract_assets.py writes the same three as assets/screen_cover.bin,
screen_ad.bin and screen_title.bin.
"""
import os
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


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import original   # noqa: E402

path = sys.argv[1] if len(sys.argv) > 2 else original.find()
prefix = sys.argv[-1]
name, data = original.unzip(path)
found = 0
for block in original.tape_blocks(name, data):
    if block[0] == 255 and len(block) in (6914, 7022):         # flag byte + 6912 (+ 108 of loader code) + parity
        found += 1
        out = f"{prefix}_{found}.png"
        Image.fromarray(draw(block[1:6913])).resize((768, 576), Image.NEAREST).save(out)
        print("wrote", out)
