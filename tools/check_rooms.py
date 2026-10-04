"""Check the port's house rooms against the original's screen, one visit per house.

Usage: python tools/check_rooms.py      (run from the repo root)

For every door marker the script parks the bike at it in the original (level snapshot, SkoolKit's simulator, the parking set-up of
tools/check_parking.py) and runs $F80C until the room, its furniture, the items and Colin are on screen (63585, before the item
messages). The port's World.interior() for the same door, with the original's item placement, must give the same 18x18 play area:
pixels and colours (bright included). The empty room itself (walls, door and windows) is a stored picture that $F8CC swaps in.
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


PALETTE = [(0, 0, 0), (0, 0, 205), (205, 0, 0), (205, 0, 205), (0, 205, 0), (0, 205, 205), (205, 205, 0), (205, 205, 205)]
BRIGHT = [(0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0), (255, 255, 255)]


def screen_rgb():
    """The original's play area (chars 1-18) as RGB, the way the port colours a Spectrum screen."""
    out = np.zeros((144, 144, 3), dtype=np.uint8)
    for y in range(8, 152):
        for cx in range(1, 19):
            byte = mem[0x4000 + ((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + cx]
            a = mem[0x5800 + (y // 8) * 32 + cx]
            pal = BRIGHT if a & 64 else PALETTE
            for i in range(8):
                out[y - 8, (cx - 1) * 8 + i] = pal[a & 7] if byte & (128 >> i) else pal[(a >> 3) & 7]
    return out


def visit(name, x, y):
    """Park in the original from (x, y) moving `name`; True once the room is drawn, False if the bike never parks."""
    d, heading = DIRS[name]
    mem[PX], mem[PY], mem[HEADING], mem[SPEED], mem[WAIT] = x, y, heading, 10, 0
    mem[58648] = mem[58646] = 0
    keys.held = (name, "space")
    for _ in range(6):
        R[SP] = (R[SP] - 2) & 0xFFFF
        mem[R[SP]] = mem[(R[SP] + 1) & 0xFFFF] = 0
        R[0] = 1
        R[24] = PASS
        count = 0
        while R[24] != 0:
            if R[24] == 63500:
                while R[24] != 63585:
                    ops[mem[R[24]]]()
                return True
            ops[mem[R[24]]]()
            count += 1
            if count > 5_000_000:
                raise RuntimeError("pass took too long")
    return False




def original_items(door):
    """The $5B07 flags of the items in this room in the original's memory: the high nibbles of bytes 1 and 2 of its record at
    $66B2 + 3 * (door - 205), packed as $F844 packs them (the same decoding as tools/extract_assets.py)."""
    b = mem[0x66B2 + 3 * (door - 205):0x66B2 + 3 * (door - 205) + 3]
    return (((b[1] >> 4) << 3) & 0xF7) | (b[2] >> 4)


saved = list(mem)
rooms = same = 0
for door, (mx, my) in sorted(first.items()):
    for name, start in (("right", (mx - 2, my)), ("left", (mx + 1, my)), ("down", (mx, my - 2)), ("up", (mx, my + 1))):
        mem[:] = saved
        if 0 < start[0] < 126 and 0 < start[1] < 126 and visit(name, *start):
            break
    else:
        print("  could not park at door", door)
        continue
    world.houses = {door: original_items(door)}
    port = pygame.surfarray.array3d(world.interior(door)).transpose(1, 0, 2)[8:152, 8:152]
    orig = screen_rgb()
    rooms += 1
    if np.array_equal(port, orig):
        same += 1
    else:
        print(f"  DIFFERENT room at door {door}: {(port != orig).any(axis=2).sum()} pixels")
print(f"{rooms} rooms compared, {same} identical")
ok = rooms == len(first) and same == rooms
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
