"""Check how the port draws the traffic against the original's screen, frame by frame.

Usage: python tools/check_vehicle_drawing.py      (run from the repo root; needs work/_tmp/original.z80 from tools/check_patched_game.py)

The original and the port are played with compare_original.py's key scripts. After every frame each vehicle cell inside the view is read from
the original's screen memory and from the port's drawn picture (ink pixels) and the two must be identical. Vehicles moving left or right are
3x2 cells ($F551, $F5D0); moving up or down they are 2x2, using the last two graphics of each row ($F625, $F677). On a frame where the
view scrolls, the original's vehicles move with the screen and the edge scrolled in shows none; the port draws only the cells that were in
the view at the traffic pass. Cells next to the bike are skipped.
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


def script(seed, frames):
    rng = random.Random(seed)
    out = []
    while len(out) < frames:
        d = rng.choice(["left", "right", "up", "down", None, None])
        out += [d] * rng.randint(2, 14)
    return out[:frames]



def cell(mem, cx, cy):
    """The 8 bytes of screen character (cx, cy) in the original's screen memory."""
    return bytes(mem[0x4000 + (((cy * 8 + k) & 0xC0) << 5) + (((cy * 8 + k) & 7) << 8) + (((cy * 8 + k) & 0x38) << 2) + cx] for k in range(8))


def check(seed, frames):
    sim, mem, keys = boot()
    w = biker.World()
    w.intro = 0
    screen = pygame.Surface((256, 192))
    counts = {"left/right": [0, 0], "up/down": [0, 0]}
    for n, d in enumerate(script(seed, frames), 1):
        keys.held = (d,) if d else ()
        run_frame(sim, mem)
        port_frame(w, {"left": 1, "right": 2, "up": 4, "down": 8, None: 0}[d])
        w.draw(screen)
        cam = (mem[A["CAM"]], mem[A["CAM"] + 1])
        pix = pygame.surfarray.array3d(screen)
        for x, y, f in [tuple(mem[A["TABLE"] + 3 * k:A["TABLE"] + 3 * k + 3]) for k in range(20)]:
            if abs(x - w.px) < 4 and abs(y - w.py) < 4:
                continue
            kind = "up/down" if f & 0x40 else "left/right"
            for row in range(2):
                for col in range(2 if f & 0x40 else 3):
                    sx, sy = x + col - cam[0] + 1, y + row - cam[1] + 1
                    if not (1 <= sx <= 18 and 1 <= sy <= 18):
                        continue
                    orig = cell(mem, sx, sy)
                    port = bytes(sum(128 >> i for i in range(8) if pix[sx * 8 + i, sy * 8 + k].any()) for k in range(8))
                    if any(orig) or any(port):
                        counts[kind][0] += 1
                        counts[kind][1] += orig == port
                        if orig != port and counts[kind][0] - counts[kind][1] <= 5:
                            print(f"  DIFFERENT script {seed} frame {n}: vehicle at {(x, y)} flags {f:02X}, cell {(col, row)}")
        if mem[A["SLEEP"]] <= 3:
            break
    print(f"script {seed}: " + ", ".join(f"{k} {v[1]}/{v[0]} cells identical" for k, v in counts.items()))
    return all(v[0] == v[1] for v in counts.values()) and counts["up/down"][0] > 0


ok = all([check(s, 250) for s in range(1, 4)])
print("ALL OK" if ok else "DIFFERENCES")
sys.exit(0 if ok else 1)
