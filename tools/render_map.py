"""Render the whole 128x128 level map from a gameplay snapshot.

Usage: python tools/render_map.py SNAPSHOT OUT.png [--colour] [--attr-snapshot SNAP] [--blocks SHEET.png]

Map at $9858 (128 x 128 ids, row-major). Id 0 = blank.
  ids 1..19  : 6x6-char buildings. Graphic = 36 consecutive 8-byte chars at $80B8 + 288*id, row-major.
               Every map region of that id is exactly a 6x6 rectangle, anchored at its top-left.
               Colours = 36 attribute bytes at $77E5 + 36*id (6 rows of 6), one per char cell.
  ids 32..201: single 8x8 chars at $79E0 + 8*id. Colour = one attribute byte at $770A + id.

--colour           draw buildings and tiles in their Spectrum colours
--attr-snapshot S  read the building colour blocks from snapshot S instead of SNAPSHOT. Some copies of
                   the tape load with those of buildings 4-8 zeroed (black on black); the .tzx and the
                   .z80 copies have the complete set.
--blocks SHEET     also write a sheet showing the 19 building graphics (coloured with --colour)
"""
import sys
import numpy as np
from PIL import Image
from skoolkit.snapshot import Snapshot

MAP, TILE, BLK, ATTR, TATTR = 0x9858, 0x79E0, 0x80B8, 0x77E5, 0x770A


def option(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


ram = bytes(Snapshot.get(sys.argv[1]).ram(1))
attr_ram = bytes(Snapshot.get(option("--attr-snapshot")).ram(1)) if option("--attr-snapshot") else ram
colour = "--colour" in sys.argv
m = np.frombuffer(ram[MAP - 0x4000:MAP - 0x4000 + 16384], dtype=np.uint8).reshape(128, 128)


def rgb(index, bright):
    level = 255 if bright else 205
    return (level if index & 2 else 0, level if index & 4 else 0, level if index & 1 else 0)


def char(addr, attr=0x07):
    """8x8 RGB image of the char at addr, coloured by a Spectrum attribute byte."""
    bright = bool(attr & 0x40)
    ink, paper = rgb(attr & 7, bright), rgb((attr >> 3) & 7, bright)
    out = np.zeros((8, 8, 3), dtype=np.uint8)
    for y in range(8):
        b = ram[addr + y - 0x4000]
        for x in range(8):
            out[y, x] = ink if b & (0x80 >> x) else paper
    return out


def tile_attribute(t):
    return attr_ram[TATTR + t - 0x4000] if colour else 0x07


def attribute(building, k):
    return attr_ram[ATTR + 36 * building + k - 0x4000] if colour else 0x07


img = np.zeros((1024, 1024, 3), dtype=np.uint8)
seen = np.zeros((128, 128), dtype=bool)
for y in range(128):
    for x in range(128):
        t = int(m[y, x])
        if t == 0 or seen[y, x]:
            continue
        if 1 <= t <= 19:
            stack, cells = [(y, x)], []
            seen[y, x] = True
            while stack:                       # flood-fill the connected region of this id
                cy, cx = stack.pop()
                cells.append((cy, cx))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < 128 and 0 <= nx < 128 and not seen[ny, nx] and m[ny, nx] == t:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            oy, ox = min(c[0] for c in cells), min(c[1] for c in cells)
            for cy, cx in cells:
                k = ((cy - oy) % 6) * 6 + ((cx - ox) % 6)
                img[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = char(BLK + 288 * t + 8 * k, attribute(t, k))
        else:
            img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = char(TILE + 8 * t, tile_attribute(t))
Image.fromarray(img).save(sys.argv[2])
print("wrote", sys.argv[2])

if option("--blocks"):
    sheet = np.full((4 * 54, 5 * 54, 3), 90, dtype=np.uint8)
    for t in range(1, 20):
        r, c = divmod(t - 1, 5)
        for k in range(36):
            kr, kc = divmod(k, 6)
            y0, x0 = r * 54 + kr * 8, c * 54 + kc * 8
            sheet[y0:y0 + 8, x0:x0 + 8] = char(BLK + 288 * t + 8 * k, attribute(t, k))
    Image.fromarray(sheet).resize((sheet.shape[1] * 3, sheet.shape[0] * 3), Image.NEAREST).save(option("--blocks"))
    print("wrote", option("--blocks"))
