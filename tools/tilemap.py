"""Render a region of a Spectrum snapshot as a sheet of 8x8 tiles (1 bit per pixel).

Usage: python tools/tilemap.py SNAPSHOT OUT.png [start_hex] [end_hex] [cols_per_block] [blocks]
Tiles are read 8 consecutive bytes each, laid out 32 per row; long regions wrap into side-by-side blocks.
Each tile's address is gridded so you can map a shape back to a memory address.
"""
import sys
from PIL import Image
from skoolkit.snapshot import Snapshot

snap, out = sys.argv[1], sys.argv[2]
start = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x5B00
end = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x10000
TILES_PER_ROW = 32
ram = Snapshot.get(snap).ram(1)  # 48K starting at 0x4000 (index 0 == 0x4000)
mem = lambda a: ram[a - 0x4000]

n_tiles = (end - start) // 8
rows = (n_tiles + TILES_PER_ROW - 1) // TILES_PER_ROW
ROWS_PER_BLOCK = 64
blocks = (rows + ROWS_PER_BLOCK - 1) // ROWS_PER_BLOCK
GAP = 8
W = blocks * (TILES_PER_ROW * 8 + GAP)
H = ROWS_PER_BLOCK * 8
img = Image.new("L", (W, H), 128)
px = img.load()
for t in range(n_tiles):
    row, col = divmod(t, TILES_PER_ROW)
    blk, row = divmod(row, ROWS_PER_BLOCK)
    x0 = blk * (TILES_PER_ROW * 8 + GAP) + col * 8
    y0 = row * 8
    for y in range(8):
        b = mem(start + t * 8 + y)
        for x in range(8):
            px[x0 + x, y0 + y] = 255 if b & (0x80 >> x) else 0
img = img.resize((W * 2, H * 2), Image.NEAREST)
img.save(out)
print(f"{start:04X}-{end:04X}: {n_tiles} tiles, {blocks} blocks; block N starts at {start:04X} + N*{ROWS_PER_BLOCK*TILES_PER_ROW*8:X}")
