"""Check the port's five control schemes against the original's Select Controls menu (SkoolKit Z80 simulator).

Usage: python tools/check_controls.py      (run from the repo root)

For each key 1-5 on the menu ($DD77, 56695) the script runs the original's menu code from work/biker.z80 (the menu snapshot) with that key held and reads
back the key-reading routine at $DFA8 (57256) that the menu patched: the A value and the mask of each of the five tests, the IN port and whether the test
is CALL Z (keys, Fuller) or CALL NZ (Kempston). port/controls.py must hold exactly those. It also drives the port's Controls class with the pygame keys the
tables name (N M A Z Space, 6 7 9 8 0, 5 8 7 6 Space).
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
import pygame   # noqa: E402
import skoolkit   # noqa: E402
from skoolkit.simulator import Simulator   # noqa: E402
from skoolkit.snapshot import Snapshot   # noqa: E402
import original   # noqa: E402  (tools/original.py: the snapshots, from ZEsarUX or made from your copy of the game)
import controls   # noqa: E402

pygame.init()
pygame.display.set_mode((64, 64))
ROM = list(open(os.path.join(os.path.dirname(skoolkit.__file__), "resources", "48.rom"), "rb").read())
ROUTINE, MENU = 57256, 56695
ok = True


class Menu:
    """Keyboard for the menu: only the key for one menu line (row $F7FE, bit n-1) is down."""
    def __init__(self, n):
        self.n = n

    def read_port(self, registers, port):
        return 0xFF & ~(1 << (self.n - 1)) if port == 0xF7FE else 0xFF


def patched_routine(n):
    snap = Snapshot.get(original.snapshot("menu"))
    mem = ROM + list(snap.ram(1))
    regs = {"A": snap.a, "F": snap.f, "BC": snap.bc, "DE": snap.de, "HL": snap.hl, "IX": snap.ix, "IY": snap.iy, "SP": snap.sp, "I": snap.i, "R": snap.r}
    # the menu snapshot was taken before a choice was made, so the routine still holds the tape's own (Cursor) values
    sim = Simulator(mem, regs, {"iff": 0, "im": 1}, {"fast_djnz": True, "fast_ldir": True})
    sim.set_tracer(Menu(n))
    from skoolkit.simulator import SP
    R, ops = sim.registers, sim.opcodes
    R[SP] = (R[SP] - 2) & 0xFFFF
    mem[R[SP]] = mem[(R[SP] + 1) & 0xFFFF] = 0
    R[24] = MENU
    steps = 0
    while R[24] != 0 and R[24] != 56996:                  # stop when the menu hands over ($DDA4, 56996: the screen set-up that follows every choice)
        ops[mem[R[24]]]()
        steps += 1
        assert steps < 5_000_000
    return mem


for name, s in controls.SCHEMES.items():
    mem = patched_routine(s["menu"])
    got = [(mem[ROUTINE + 6 + 9 * i], mem[ROUTINE + 10 + 9 * i]) for i in range(5)]
    in_port = {mem[ROUTINE + 8 + 9 * i] for i in range(5)}
    opcode = {mem[ROUTINE + 11 + 9 * i] for i in range(5)}
    joystick = bool(s.get("joystick"))
    want = [(a if a is not None else g[0], m) for (a, m), g in zip(s["keys"], got)]
    good = got == want and in_port == {s["in"]} and opcode == ({196} if name == "KEMPSTON" else {204})
    ok &= good
    print(f"{s['menu']} {name:9s}: masks {[m for _, m in got]}, IN port {sorted(in_port)}, {'CALL NZ' if 196 in opcode else 'CALL Z'}"
          + ("" if joystick else f", A values {[a for a, _ in got]}") + f"  {good}")

# the keys the port reads for each keyboard scheme
for name, expect in (("KEYBOARD", "n m a z space"), ("SINCLAIR", "6 7 9 8 0"), ("CURSOR", "5 8 7 6 space")):
    c = controls.Controls(name)
    names = [pygame.key.name(k) for k in c.keys]
    good = names == expect.split()
    ok &= good
    print(f"{name:9s}: port reads keys {names}  {good}")


class State(dict):
    def __missing__(self, key):
        return False


c = controls.Controls("KEYBOARD")
k = State()
k[pygame.K_n] = k[pygame.K_a] = k[pygame.K_SPACE] = True
mask, fire = c.read(k)
print("N + A + Space ->", mask, fire, "(expect 5, True: left + up)")
ok &= (mask, fire) == (5, True)
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
