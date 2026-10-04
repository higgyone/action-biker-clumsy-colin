"""Check the port's fuel gauge and clock face against the original's screen, frame by frame.

Usage: python tools/check_hud.py      (run from the repo root; needs work/_tmp/original.z80 from tools/check_patched_game.py)

The original and the port ride right from the start with the same keys (compare_original.py's set-up). After every frame two parts of the
HUD are compared pixel by pixel in colour:
- the FUEL box (chars 28-30, rows 20-22): every gauge step ($E28F/$E290) XORs one more line over the box ($DA67) and the lines stay, so the
  box is inverted from the top down to the level;
- the clock face (chars 1-3, rows 20-22): both hands XORed on with the original's line routine ($DCFB; the pixels made by tools/extract_assets.py).
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
import numpy as np   # noqa: E402
import pygame   # noqa: E402
import skoolkit   # noqa: E402
from skoolkit.simulator import Simulator   # noqa: E402
from skoolkit.snapshot import Snapshot   # noqa: E402
import original   # noqa: E402  (tools/original.py: the snapshots, from ZEsarUX or made from your copy of the game)

pygame.init()
pygame.display.set_mode((64, 64))
spec = importlib.util.spec_from_file_location("biker", os.path.join(ROOT, "port", "biker.py"))
biker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biker)

ROM = list(open(os.path.join(os.path.dirname(skoolkit.__file__), "resources", "48.rom"), "rb").read())
LOOP, AFTER_FRAME = 58046, 58049
A = dict(SLEEP=23300, SCORE=23301, ITEMS=23303, SPEED=58647, HEADING=58649, PX=58650, PY=58651, CAM=59659, FRAME=59188, HOUR=56275, SECOND=56274,
         FUEL_ACC=55778, SEED=62135, TABLE=30092, MAP=0x9858)
BASE = 0x75C8


class Keys:
    held = ()

    def read_port(self, registers, port):
        v = 0xFF
        if port == 0xF7FE:
            v &= 0xFE                                     # key 1 for the controls menu (the game never reads this row in play)
        if port == 0x7FFE:
            v &= ~((8 if "left" in self.held else 0) | (4 if "right" in self.held else 0)) & 0xFF
        elif port == 0xFDFE and "up" in self.held:
            v &= ~1 & 0xFF
        elif port == 0xFEFE and "down" in self.held:
            v &= ~2 & 0xFF
        return v


def boot(path=None):
    path = path or original.snapshot("original")
    snap = Snapshot.get(path)
    mem = ROM + list(snap.ram(1))
    regs = {"A": snap.a, "F": snap.f, "BC": snap.bc, "DE": snap.de, "HL": snap.hl, "IX": snap.ix, "IY": snap.iy, "SP": snap.sp, "I": snap.i, "R": snap.r}
    sim = Simulator(mem, regs, {"iff": 0, "im": 1}, {"fast_djnz": True, "fast_ldir": True})
    keys = Keys()
    sim.set_tracer(keys)
    R, ops = sim.registers, sim.opcodes
    R[24] = snap.pc
    while R[24] != LOOP:
        ops[mem[R[24]]]()
    return sim, mem, keys


def run_frame(sim, mem):
    R, ops = sim.registers, sim.opcodes
    R[24] = LOOP
    n = 0
    while R[24] != AFTER_FRAME:
        ops[mem[R[24]]]()
        n += 1
        if n > 20_000_000:
            raise RuntimeError("frame too long")



def port_frame(w, mask):
    done = 0
    guard = 0
    while done < 2:
        guard += 1
        assert guard < 5000
        stalled = w.stall >= 1 or bool(w.intro)
        w.tick(mask, False)
        if not stalled:
            done += 1
    while w.stall >= 1:                                   # let a message or crash that has just begun run out, as the original's routine has
        w.tick(mask, False)


PALETTE = [(0, 0, 0), (0, 0, 205), (205, 0, 0), (205, 0, 205), (0, 205, 0), (0, 205, 205), (205, 205, 0), (205, 205, 205)]
BRIGHT = [(0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255)]
AREAS = {"fuel box": [(x, y) for y in range(160, 184) for x in range(224, 248)],
         "clock face": [(x, y) for y in range(160, 184) for x in range(8, 32)]}


def original_pixels(mem, area):
    out = []
    for x, y in area:
        byte = mem[0x4000 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + x // 8]
        a = mem[0x5800 + (y // 8) * 32 + x // 8]
        pal = BRIGHT if a & 64 else PALETTE
        out.append(pal[a & 7] if byte & (128 >> (x % 8)) else pal[(a >> 3) & 7])
    return out


sim, mem, keys = boot()
w = biker.World()
w.intro = 0
screen = pygame.Surface((256, 192))
keys.held = ("right",)
frames, gauge, steps = 0, None, 0
same = {name: 0 for name in AREAS}
for n in range(1, 1500):
    if n > 1:
        run_frame(sim, mem)
        port_frame(w, 2)
    if (mem[57999], mem[58000]) != gauge:
        gauge = (mem[57999], mem[58000])
        steps += 1
    w.draw(screen)
    pix = pygame.surfarray.array3d(screen)
    frames += 1
    for name, area in AREAS.items():
        if [tuple(int(v) for v in pix[x, y]) for x, y in area] == original_pixels(mem, area):
            same[name] += 1
        elif frames - same[name] <= 3:
            print(f"  DIFFERENT {name} at frame {n} (port fuel {w.fuel}, clock {w.second}, {w.hour})")
    if w.fuel <= 0 or mem[A["SLEEP"]] <= 3:
        break
print(f"{frames} frames compared ({steps} gauge states, full tank down to {w.fuel} of {biker.FUEL_MAX}): " +
      ", ".join(f"{name} identical in {k}" for name, k in same.items()))
ok = steps > 10 and all(k == frames for k in same.values())
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
