"""Tile-id test: do map ids index 8-byte chars in the scenery area?
Votes for (map window, base) pairs that reproduce the on-screen play area.
Usage: python tools/tile_test.py SNAPSHOT.z80
"""
import sys, collections
import numpy as np
from skoolkit.snapshot import Snapshot

ram = bytes(Snapshot.get(sys.argv[1]).ram(1))
mem = lambda a: ram[a - 0x4000]
MAP, W = 0x9858, 128
m = np.frombuffer(ram[MAP - 0x4000:MAP - 0x4000 + W * W], dtype=np.uint8).reshape(W, W)

def cell(cx, cy):
    out = []
    for r in range(8):
        y = cy * 8 + r
        a = 0x4000 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + cx
        out.append(mem(a))
    return bytes(out)

# index every 8-byte window in the art area
LO, HI = 0x5B00, 0x9800
idx = collections.defaultdict(list)
for a in range(LO, HI - 8):
    idx[ram[a - 0x4000:a - 0x4000 + 8]].append(a)

PX, PY = 20, 18          # guessed play area in chars (HUD is on the right)
cells = {}
for cy in range(PY):
    for cx in range(PX):
        c = cell(cx, cy)
        if c != bytes(8) and c in idx:
            cells[(cx, cy)] = idx[c]
print("play-area cells:", PX * PY, " non-blank with a match in art area:", len(cells))
print("distinct cell patterns:", len(set(cell(cx, cy) for cy in range(PY) for cx in range(PX))))

votes = collections.Counter()
for wy in range(W - PY + 1):
    for wx in range(W - PX + 1):
        per = collections.Counter()
        for (cx, cy), addrs in cells.items():
            t = int(m[wy + cy, wx + cx])
            for b in {a - 8 * t for a in addrs}:
                per[b] += 1
        if per:
            b, n = per.most_common(1)[0]
            votes[(wy, wx, b)] = n
for (wy, wx, b), n in votes.most_common(8):
    print(f"window x={wx} y={wy} base=${b & 0xFFFF:04X}  matching cells={n}/{len(cells)}")
