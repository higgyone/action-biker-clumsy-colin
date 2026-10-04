"""Play the original and the port side by side with the same key presses and compare them frame by frame.

Usage: python tools/compare_original.py [SCRIPTS [FRAMES]]      (run from the repo root; default 3 scripts of 250 frames)

The original (the tape's own code, started through the controls menu in SkoolKit's Z80 simulator, work/_tmp/original.z80 made by
tools/check_patched_game.py) and the port (default mode, no fixes, silent) are given the same keys on every frame: random runs of a direction held for
a few frames, or nothing. After every frame (two passes) the script compares what the player would see and feel: the bike's tile, view, speed counter,
heading and sprite frame, SLEEP, score, items, the clock, the fuel accumulator, the seed and all 20 vehicles. Passes the port spends standing still while
a message or crash routine runs (the original does that inside one pass) are not counted. Stops a script when SLEEP gets low (the ending routines are long).
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


def word(mem, a):
    return mem[a] | mem[a + 1] << 8


def original_state(mem):
    return {
        "bike": (mem[A["PX"]], mem[A["PY"]]), "view": (mem[A["CAM"]], mem[A["CAM"] + 1]), "speed": mem[A["SPEED"]],
        "heading": mem[A["HEADING"]] >> 6, "frame": (word(mem, A["FRAME"]) - BASE) >> 5, "sleep": mem[A["SLEEP"]], "score": word(mem, A["SCORE"]),
        "items": mem[A["ITEMS"]], "clock": (mem[A["HOUR"]], mem[A["SECOND"]]), "seed": mem[A["SEED"]],
        "traffic": [tuple(mem[A["TABLE"] + 3 * k:A["TABLE"] + 3 * k + 3]) for k in range(20)],
    }


def port_state(w):
    return {
        "bike": (w.px, w.py), "view": tuple(w.cam), "speed": w.speed, "heading": w.heading, "frame": w.angle, "sleep": w.sleep, "score": w.score,
        "items": w.items, "clock": (w.hour, w.second), "seed": w.traffic.seed, "traffic": [tuple(e) for e in w.traffic.table],
    }


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


def compare(seed, frames):
    sim, mem, keys = boot()
    w = biker.World()
    w.intro = 0
    first = original_state(mem), port_state(w)
    same_map = bytes(mem[A["MAP"]:A["MAP"] + 16384]) == bytes(w.map.astype(np.uint8).tobytes())
    print(f"script {seed}: start states equal: {first[0] == first[1]}, map with its pickups equal: {same_map}")
    for k in first[0]:
        if first[0][k] != first[1][k]:
            print(f"    start {k}: original {first[0][k]}, port {first[1][k]}")
    diffs = {}
    for n, d in enumerate(script(seed, frames), 1):
        keys.held = (d,) if d else ()
        mask = {"left": 1, "right": 2, "up": 4, "down": 8, None: 0}[d]
        run_frame(sim, mem)
        port_frame(w, mask)
        a, b = original_state(mem), port_state(w)
        for k in a:
            if a[k] != b[k] and k not in diffs:
                diffs[k] = (n, d, a[k], b[k])
        if mem[A["SLEEP"]] <= 3:
            break
    print(f"  {n} frames compared; fields that ever differed: {sorted(diffs) or 'none'}")
    for k, (frame, d, a, b) in diffs.items():
        print(f"    {k}: first at frame {frame} (key {d}): original {a}, port {b}")
    return not diffs and first[0] == first[1] and same_map


scripts = int(sys.argv[1]) if len(sys.argv) > 1 else 3
frames = int(sys.argv[2]) if len(sys.argv) > 2 else 250
ok = all([compare(s, frames) for s in range(1, scripts + 1)])
print("ALL OK" if ok else "DIFFERENCES")
sys.exit(0 if ok else 1)
