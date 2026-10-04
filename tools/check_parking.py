"""Check the port's parking (entering a house) against the original's pass routine in the simulator.

Usage: python tools/check_parking.py      (run from the repo root)

The original enters a house ($F80C, 63500) only on a pass where the bike has just moved (so its leading edge touched a door marker, $E516) and
the trigger key (Space) is down. For every door marker and each of the four directions the script puts the bike a few tiles short of the
marker, standing still, holds the direction key and Space, and runs the original's pass ($D8A2 routine, one pass at a time). The port (default
mode, no fixes) must enter the house on the same pass at the same position, or not at all when the original does not. The position is
taken where $F80C has picked the parked sprite frame (63533): facing right it first calls the move-right handler, so the bike is a tile further on.
"""
import importlib.util
import os
import sys

import numpy as np

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
MAP, HEADING, PX, PY, SPEED, WAIT, PASS = 0x9858, 58649, 58650, 58651, 58647, 55496, 55458
# direction -> (heading byte, keys on port $7FFE for N/M/Space, other rows), as the game reads them ($DFA8)
FRAME = biker.FRAME


class Keys:
    """Keyboard: N left, M right (row $7FFE bits 3, 2), A up ($FDFE bit 0), Z down ($FEFE bit 1), Space (row $7FFE bit 0)."""
    held = ()

    def read_port(self, registers, port):
        v = 0xFF
        if port == 0x7FFE:
            v &= ~((1 if "space" in self.held else 0) | (8 if "left" in self.held else 0) | (4 if "right" in self.held else 0)) & 0xFF
        elif port == 0xFDFE and "up" in self.held:
            v &= ~1 & 0xFF
        elif port == 0xFEFE and "down" in self.held:
            v &= ~2 & 0xFF
        return v & 0xFF


keys = Keys()
sim.set_tracer(keys)
DIRS = {"right": (biker.RIGHT, 0x80), "left": (biker.LEFT, 0x00), "down": (biker.DOWN, 0x40), "up": (biker.UP, 0xC0)}
STEPS = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}
base_map = bytes(mem[MAP:MAP + 128 * 128])
world = biker.World()
world.map = np.frombuffer(base_map, dtype=np.uint8).reshape(128, 128).copy()
first = {}
for y in range(128):
    for x in range(128):
        if world.map[y, x] >= 205:
            first.setdefault(int(world.map[y, x]), (x, y))      # the first cell of each of the 49 door markers
markers = list(first.values())


def original(name, x, y, passes=6):
    """Pass number (1-based) on which the original enters the house, and the bike position then; None if it never does."""
    d, heading = DIRS[name]
    mem[PX], mem[PY], mem[HEADING], mem[SPEED], mem[WAIT] = x, y, heading, 10, 0
    mem[58648] = mem[58646] = 0
    keys.held = (name, "space")
    for n in range(1, passes + 1):
        R[SP] = (R[SP] - 2) & 0xFFFF
        mem[R[SP]] = mem[(R[SP] + 1) & 0xFFFF] = 0
        R[0] = 1                                          # A = 1 pass
        R[24] = PASS
        count = 0
        while R[24] != 0:
            if R[24] == 63533:                            # $F80C has chosen the parked frame (facing right after its step right, $E538)
                return n, (mem[PX], mem[PY])
            ops[mem[R[24]]]()
            count += 1
            if count > 5_000_000:
                raise RuntimeError("pass took too long")
    return None


def port(name, x, y, passes=6):
    d, heading = DIRS[name]
    w = world
    w.place(x, y)
    w.heading, w.angle, w.speed, w.wait, w.last_keys = d, FRAME[d], 10, 0, 0
    w.marker, w.walk, w.inside, w.visit, w.intro, w.stall, w.phase = 0, None, None, None, 0, 0.0, 1
    w.traffic.update = lambda: None
    w.sound = None
    bit = {"left": 1, "right": 2, "up": 4, "down": 8}[name]
    for n in range(1, passes + 1):
        w.tick(bit, True)
        if w.walk is not None:
            return n, (w.px, w.py)
        w.sleep = 50
        w.over = None
    return None


same = diff = parked = 0
for (mx, my) in markers:
    for name, (dx, dy) in STEPS.items():
        for k in range(0, 3):
            # front edge tiles: right (x+2, y), (x+2, y+1) ... start k tiles short of touching the marker cell
            x, y = (mx - 2 - k * dx if dx else mx), (my if dx else my)
            if dx > 0:
                x, y = mx - 2 - k, my
            elif dx < 0:
                x, y = mx + 1 + k, my
            elif dy > 0:
                x, y = mx, my - 2 - k
            else:
                x, y = mx, my + 1 + k
            if not (0 < x < 126 and 0 < y < 126):
                continue
            a, b = original(name, x, y), port(name, x, y)
            if a == b:
                same += 1
                parked += a is not None
            else:
                diff += 1
                if diff <= 10:
                    print("DIFFERENT", name, "marker", (mx, my), "start", (x, y), "original", a, "port", b)
print(f"{same + diff} runs ({parked} enter a house): the port matches the original in {same}, differs in {diff}")
ok = diff == 0 and parked > 20
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
