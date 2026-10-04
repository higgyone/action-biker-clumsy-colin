"""Check the traffic model against the snapshots: the model is port/traffic.py, the same code the pygame port runs.

Usage: python tools/traffic_sim.py        (run from the repo root)

Verified: one update of the traffic table from work/biker.z80 (controls menu) reproduces all 20 entries of
work/biker_level.z80 and ends on the same random-generator seed (253). See notes/03-level-map.md, "Traffic movement".
"""
import os
import sys
import numpy as np
from skoolkit.snapshot import Snapshot
import original   # noqa: E402  (tools/original.py: the snapshots, from ZEsarUX or made from your copy of the game)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
from traffic import Traffic   # noqa: E402

SEED_ADDR = 62135  # $F2B7


def load(name):
    r = bytes(Snapshot.get(original.snapshot({"biker": "menu", "biker_level": "level"}[name])).ram(1))
    m = np.frombuffer(r[0x9858 - 0x4000:0x9858 - 0x4000 + 16384], dtype=np.uint8).reshape(128, 128).copy()
    tab = [list(r[0x758C - 0x4000 + 3 * i:0x758C - 0x4000 + 3 * i + 3]) for i in range(20)]
    return m, tab, r[SEED_ADDR - 0x4000]


m0, tab0, seed0 = load("biker")
m1, tab1, seed1 = load("biker_level")
print("menu seed", seed0, " level seed", seed1)
for frames in (1, 2, 3):
    s = Traffic(tab0, seed0, m0)
    for _ in range(frames):
        s.update()
    same = sum(1 for a, b in zip(s.table, tab1) if a == b)
    print(f"after {frames} frame(s): entries equal to the level snapshot {same}/20, seed {s.seed} (level snapshot {seed1})")
