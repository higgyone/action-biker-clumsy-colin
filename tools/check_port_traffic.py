"""Headless check of the traffic in the pygame port (no window needed).

Usage: python tools/check_port_traffic.py      (run from the repo root)

1. The port starts with the level snapshot's 20 vehicles and generator seed.
2. After its first traffic update the port's table and seed equal two updates of the controls-menu table
   (the verified model, tools/traffic_sim.py): so the port follows the original's routine at $F1CC exactly.
3. Over 3,000 passes no vehicle's footprint ever sits on a tile a vehicle may not enter.
4. A vehicle overlapping the player costs one SLEEP point per pass.
"""
import os
import sys
import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import pygame                       # noqa: E402
from skoolkit.snapshot import Snapshot   # noqa: E402
import original   # noqa: E402  (tools/original.py: the snapshots, from ZEsarUX or made from your copy of the game)
from traffic import Traffic         # noqa: E402

pygame.init()
pygame.display.set_mode((64, 64))
import importlib.util                # noqa: E402
spec = importlib.util.spec_from_file_location("biker", os.path.join(ROOT, "port", "biker.py"))
biker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biker)

ok = True
w = biker.World()
level = bytes(Snapshot.get(original.snapshot("level")).ram(1))
menu = bytes(Snapshot.get(original.snapshot("menu")).ram(1))
lvl_tab = [list(level[0x758C - 0x4000 + 3 * i:0x758C - 0x4000 + 3 * i + 3]) for i in range(20)]
print("1. start table equals the level snapshot:", w.traffic.table == lvl_tab, " seed", w.traffic.seed,
      "(snapshot", level[0xF2B7 - 0x4000], ")")
ok &= w.traffic.table == lvl_tab and w.traffic.seed == level[0xF2B7 - 0x4000]

# 2. one port frame == two model updates from the menu table
mmap = np.frombuffer(menu[0x9858 - 0x4000:0x9858 - 0x4000 + 16384], dtype=np.uint8).reshape(128, 128)
ref = Traffic([list(menu[0x758C - 0x4000 + 3 * i:0x758C - 0x4000 + 3 * i + 3]) for i in range(20)], menu[0xF2B7 - 0x4000], mmap)
ref.update()
ref.update()
w.place(1, 1)                   # park the player out of the way of everything
w.tick(0)
same = w.traffic.table == ref.table and w.traffic.seed == ref.seed
print("2. the port's first update equals two model updates from the menu table:", same, "seed", w.traffic.seed)
ok &= same

# 3. 3000 passes, footprints stay on free tiles
def free(t):
    return t == 0 or t == 69 or t >= 190

bad = 0
turns = 0
last = [tuple(e[:1]) + tuple(e[2:]) for e in w.traffic.table]
for _ in range(3000):
    w.tick(0)
    for x, y, f in w.traffic.table:
        wd = 2 if f & 0x40 else 3
        for dy in range(2):
            for dx in range(wd):
                if not free(int(w.map[y + dy, x + dx])):
                    bad += 1
    turns += sum(1 for e, l in zip(w.traffic.table, last) if e[2] != l[1])
    last = [tuple(e[:1]) + tuple(e[2:]) for e in w.traffic.table]
    if w.over:
        break
print("3. blocked-tile footprints over 3000 passes:", bad, " heading changes seen:", turns)
ok &= bad == 0 and turns > 0

# 4. a crash costs SLEEP
w2 = biker.World()
vx, vy, _ = w2.traffic.table[0]
w2.place(vx, vy)
before = w2.sleep
w2.tick(0)
print("4. player on a vehicle: SLEEP", before, "->", w2.sleep)
ok &= w2.sleep == before - 1
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
