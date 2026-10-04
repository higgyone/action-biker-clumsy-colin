"""Check how the port's camera follows the bike against the original's own move handlers (SkoolKit Z80 simulator).

Usage: python tools/check_camera.py      (run from the repo root)

The four move handlers ($E538 right, $E5E5 up, $E689 down, $E736 left) test the tile ahead and then either move the bike on the screen or
scroll the view one tile. For thousands of random positions, view positions and directions the script runs the original handler from
work/biker_level.z80 and compares the result with World.follow() of the port: whenever the original moved, the bike's new position and the view
position must be the same, and the screen-position counters $E51C/$E51D must still equal (column + 1, 23 - row) of the bike in the view.
"""
import importlib.util
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
import pygame   # noqa: E402
import skoolkit   # noqa: E402
from skoolkit.simulator import Simulator, SP   # noqa: E402
from skoolkit.snapshot import Snapshot   # noqa: E402
import original   # noqa: E402  (tools/original.py: the snapshots, from ZEsarUX or made from your copy of the game)

pygame.init()
pygame.display.set_mode((64, 64))
spec = importlib.util.spec_from_file_location("biker", os.path.join(ROOT, "port", "biker.py"))
biker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biker)

ROM = list(open(os.path.join(os.path.dirname(skoolkit.__file__), "resources", "48.rom"), "rb").read())
snap = Snapshot.get(original.snapshot("level"))
mem = ROM + list(snap.ram(1))
regs = {"A": snap.a, "F": snap.f, "BC": snap.bc, "DE": snap.de, "HL": snap.hl, "IX": snap.ix, "IY": snap.iy, "SP": snap.sp, "I": snap.i, "R": snap.r}
sim = Simulator(mem, regs, {"iff": 0, "im": 1}, {"fast_djnz": True, "fast_ldir": True})
R, ops = sim.registers, sim.opcodes
HEADING, PX, PY, COL, ROW, CAM = 58649, 58650, 58651, 58652, 58653, 59659
ENTRY = {biker.RIGHT: (58680, 0x80), biker.UP: (58853, 0xC0), biker.DOWN: (59017, 0x40), biker.LEFT: (59190, 0x00)}
NAME = {biker.RIGHT: "right", biker.UP: "up", biker.DOWN: "down", biker.LEFT: "left"}
random.seed(1985)
world = biker.World()


def run(direction):
    entry, heading = ENTRY[direction]
    mem[HEADING] = heading
    R[SP] = (R[SP] - 2) & 0xFFFF
    mem[R[SP]] = mem[(R[SP] + 1) & 0xFFFF] = 0
    R[24] = entry
    while R[24] != 0:
        ops[mem[R[24]]]()


moved = scrolled = checked = bad = 0
seen = {}
for trial in range(6000):
    if trial % 40 == 0:                                   # a fresh random place and view, now and then (edges of the map included)
        x, y = random.randint(1, 124), random.randint(1, 124)
        if trial % 160 == 0:
            x = random.choice([1, 2, 3, 124, 125, 126]); y = random.choice([1, 2, 3, 124, 125, 126])
        cx = min(max(x - random.randint(0, 15), 0), 110)
        cy = min(max(y - random.randint(0, 15), 0), 110)
        mem[PX], mem[PY], mem[CAM], mem[CAM + 1] = x, y, cx, cy
        mem[COL], mem[ROW] = x - cx + 1, 23 - (y - cy)
    d = random.choice([biker.RIGHT, biker.UP, biker.DOWN, biker.LEFT] if trial % 3 else [random.choice(list(ENTRY))] * 4)
    before = (mem[PX], mem[PY], mem[CAM], mem[CAM + 1])
    run(d)
    after = (mem[PX], mem[PY], mem[CAM], mem[CAM + 1])
    if after[:2] == before[:2]:                           # blocked by a tile: nothing may change
        if after != before:
            bad += 1
            print("blocked but the camera moved", NAME[d], before, after)
        continue
    moved += 1
    world.px, world.py, world.cam = before[0], before[1], (before[2], before[3])
    ox, oy = before[0] - before[2], before[1] - before[3]
    world.follow(d)
    dx, dy = biker.STEP[d]
    ours = (world.px + dx, world.py + dy, world.cam[0], world.cam[1])
    scrolled += after[2:] != before[2:]
    key = (NAME[d], "scroll" if after[2:] != before[2:] else "move")
    seen[key] = seen.get(key, 0) + 1
    checked += 1
    counters_ok = (mem[COL], mem[ROW]) == (after[0] - after[2] + 1, 23 - (after[1] - after[3]))
    if ours != after or not counters_ok:
        bad += 1
        print("MISMATCH", NAME[d], "before", before, "offset", (ox, oy), "original", after, "port", ours, "counters", (mem[COL], mem[ROW]))
print(f"{checked} moves compared ({scrolled} scrolled the view, {checked - scrolled} moved the bike on the screen), {bad} differences")
print("  ", dict(sorted(seen.items())))
ok = bad == 0 and scrolled > 200 and checked - scrolled > 200
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
