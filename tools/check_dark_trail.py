"""Check the vehicle trail in the dark area: the original's own vehicle-drawing routine (in the simulator) against the port.

Usage: python tools/check_dark_trail.py      (run from the repo root)

Every frame the original draws each vehicle on screen (the loop at $F42F, 62511) and then restores the two cells behind it from the map
($F595 -> $F6D3 -> $F7B5). Without the headlamp $F7B5 returns the blank tile 205 for map x <= 41 and y > 80. For every vehicle position and
heading on a grid around that corner, the script runs the original's loop in the simulator (starting from work/biker_level.z80, one vehicle
on screen, the screen filled with a marker) and looks at what the two trailing cells hold, with and without the headlamp. The port's
World.vehicle_trails() must blank exactly the same cells.
"""
import importlib.util
import os
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
MAP, TABLE, TILE, CAMERA, ITEMS, LOOP = 0x9858, 30092, 0x79E0, 59659, 0x5B07, 62511
TRAIL = biker.World.TRAIL


def draw_vehicles():
    R[SP] = (R[SP] - 2) & 0xFFFF
    mem[R[SP]] = mem[(R[SP] + 1) & 0xFFFF] = 0          # return to $0000, which nothing else runs
    R[24] = LOOP
    while R[24] != 0:
        ops[mem[R[24]]]()


def cell(cx, cy):
    return [mem[0x4000 + (((cy * 8 + k) & 0xC0) << 5) + (((cy * 8 + k) & 7) << 8) + (((cy * 8 + k) & 0x38) << 2) + cx] for k in range(8)]


world = biker.World()
checked = blank_cells = bad = 0
for headlamp in (0, 1):
    for heading in range(4):
        for x in range(34, 52):
            for y in range(74, 90):
                cam = (x - 6, y - 6)
                mem[ITEMS] = headlamp
                mem[CAMERA], mem[CAMERA + 1] = cam
                for k in range(20):
                    mem[TABLE + 3 * k:TABLE + 3 * k + 3] = [120, 10, 0]      # off screen
                mem[TABLE:TABLE + 3] = [x, y, heading << 6]
                for cy in range(1, 19):
                    for cx in range(1, 19):
                        for k in range(8):
                            yy = cy * 8 + k
                            mem[0x4000 + ((yy & 0xC0) << 5) + ((yy & 7) << 8) + ((yy & 0x38) << 2) + cx] = 0xAA   # marker: nothing drawn
                draw_vehicles()
                world.items = headlamp
                world.prev_cam = cam
                world.traffic.table = [[x, y, heading << 6]]
                world.dark_blank[:] = False
                world.vehicle_trails()
                for dx, dy in TRAIL[heading]:
                    tx, ty = x + dx, y + dy
                    t = mem[MAP + ty * 128 + tx]
                    if not 32 <= t < 206 or not any(mem[TILE + 8 * t + k] for k in range(8)):
                        continue                                           # only cells whose real tile shows something tell the two apart
                    original_blank = not any(cell(tx - cam[0] + 1, ty - cam[1] + 1))
                    ours = bool(world.dark_blank[ty - cam[1], tx - cam[0]])
                    checked += 1
                    blank_cells += original_blank
                    if original_blank != ours:
                        bad += 1
                        print("MISMATCH headlamp", headlamp, "heading", heading, "vehicle", (x, y), "cell", (tx, ty), "original blank", original_blank, "port", ours)
print(f"{checked} trailing cells compared ({blank_cells} blank in the original, {checked - blank_cells} showing the map), {bad} differences")
ok = bad == 0 and blank_cells > 0 and checked > blank_cells
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
