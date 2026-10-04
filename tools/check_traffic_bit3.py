"""Show that bit 3 of a traffic table entry's flags is never used (SkoolKit Z80 simulator).

Usage: python tools/check_traffic_bit3.py      (run from the repo root)

Every routine that reads the flags byte of a vehicle (collision $D8F9, move $F1CC and its turn routines, draw $F42F, sprite
choice $F4B3) masks it with 192 (heading), 48 (type), 7 (colour) or rewrites only bits 7-6 (AND 63 / RES 6 / SET 7 / OR 192), so bit 3 is carried along
and never looked at. The script proves it by running the original's frame (traffic update and drawing, from work/biker_level.z80) for 60 frames with
bit 3 clear on all 20 vehicles and again with it set: positions, headings, types, colours and the whole screen must come out the same, and bit 3 itself
must still be there afterwards.
"""
import os
import sys

import skoolkit
from skoolkit.simulator import Simulator, SP
from skoolkit.snapshot import Snapshot
import original   # noqa: E402  (tools/original.py: the snapshots, from ZEsarUX or made from your copy of the game)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)
ROM = list(open(os.path.join(os.path.dirname(skoolkit.__file__), "resources", "48.rom"), "rb").read())
TABLE, UPDATE, DRAW = 30092, 61900, 62511


def run(bit3, frames=60):
    snap = Snapshot.get(original.snapshot("level"))
    mem = ROM + list(snap.ram(1))
    regs = {"A": snap.a, "F": snap.f, "BC": snap.bc, "DE": snap.de, "HL": snap.hl, "IX": snap.ix, "IY": snap.iy, "SP": snap.sp, "I": snap.i, "R": snap.r}
    sim = Simulator(mem, regs, {"iff": 0, "im": 1}, {"fast_djnz": True, "fast_ldir": True})
    R, ops = sim.registers, sim.opcodes
    for k in range(20):
        mem[TABLE + 3 * k + 2] = (mem[TABLE + 3 * k + 2] & ~8) | (8 if bit3 else 0)
    for _ in range(frames):
        for addr in (UPDATE, DRAW):
            R[SP] = (R[SP] - 2) & 0xFFFF
            mem[R[SP]] = mem[(R[SP] + 1) & 0xFFFF] = 0
            R[24] = addr
            while R[24] != 0:
                ops[mem[R[24]]]()
    return [tuple(mem[TABLE + 3 * k:TABLE + 3 * k + 3]) for k in range(20)], bytes(mem[0x4000:0x5B00])


a_table, a_screen = run(False)
b_table, b_screen = run(True)
same_state = [(x, y, f & ~8) for x, y, f in a_table] == [(x, y, f & ~8) for x, y, f in b_table]
kept = all(f & 8 for _, _, f in b_table) and not any(f & 8 for _, _, f in a_table)
moved = len({t for t in a_table}) > 1
print(f"60 frames of traffic with bit 3 clear and with it set: positions/headings/types/colours the same: {same_state}, screens the same: {a_screen == b_screen}, bit 3 carried along: {kept}")
ok = same_state and a_screen == b_screen and kept and moved
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
