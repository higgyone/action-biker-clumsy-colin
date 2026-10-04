"""Run the real game code in SkoolKit's Z80 simulator to show what the patched tape does.

Usage: python tools/make_patched_game.py && python tools/check_patched_game.py        (run from the repo root)

The script loads the original and the patched tape through SkoolKit's tape-loading simulator (tap2sna) into work/_tmp/, then
starts each game where the loader finished (the main game loop at $E2AE, via the Select Controls menu with key 1 held).
For each game the script runs the game's own start-up, then (1) puts the bike on a vehicle for one frame and (2) forces the fuel counter to roll over for one frame,
and prints SLEEP and the fuel gauge before and after. Expected: the original loses a SLEEP point and a fuel step, the patched
game neither. Another test puts the clock on eight o'clock: the original ends the day, both patched tapes carry on. A last test holds the right key for four passes from a standstill and prints the speed counter: 9, 8, 7, 6 in the original and the
first patched tape, 0, 0, 0, 0 in the fast one (work/biker_infinite_fast.tap).
"""
import os
import sys
import skoolkit
from skoolkit.simulator import Simulator
from skoolkit.snapshot import Snapshot

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)
ROM = list(open(os.path.join(os.path.dirname(skoolkit.__file__), "resources", "48.rom"), "rb").read())

from skoolkit.simulator import SP as SP_REG   # noqa: E402
SLEEP, FUEL_C, FUEL_B, FUEL_ACC, SPEED, WAIT = 23300, 57999, 58000, 55778, 58647, 55496
PX, PY, TABLE = 58650, 58651, 30092
LOOP, AFTER_FRAME = 58046, 58049      # the main loop's CALL 55449 (one frame) and the instruction after it


class Keys:
    """Port reads for the simulator: no key pressed, except '1' (row $F7FE) to get past the Select Controls menu."""
    def read_port(self, registers, port):
        return 0xFE if port == 0xF7FE else 0xFF


def run_to(sim, start, stop, limit=300_000_000, label=""):
    """Like Simulator.run(start, stop) but gives up (instead of hanging) after `limit` instructions."""
    regs, mem, ops = sim.registers, sim.memory, sim.opcodes
    if start is not None:
        regs[24] = start
    n = 0
    while True:
        ops[mem[regs[24]]]()
        n += 1
        if regs[24] == stop:
            return n
        if n >= limit:
            sys.exit(f"{label}: no arrival at {stop} after {n} instructions (PC {regs[24]})")


def start(path):
    snap = Snapshot.get(path)
    mem = ROM + list(snap.ram(1))
    regs = {"A": snap.a, "F": snap.f, "BC": snap.bc, "DE": snap.de, "HL": snap.hl, "IX": snap.ix, "IY": snap.iy,
            "SP": snap.sp, "I": snap.i, "R": snap.r}
    sim = Simulator(mem, regs, {"iff": 0, "im": 1}, {"fast_djnz": True, "fast_ldir": True})   # the game waits in long DJNZ loops
    sim.set_tracer(Keys())
    n = run_to(sim, snap.pc, LOOP, label=path)         # the menu (key 1) and the game's own set-up ($D858), up to the main loop
    print(f"  {path}: start-up took {n:,} instructions", flush=True)
    return sim, mem


def frame(sim):
    run_to(sim, LOOP, AFTER_FRAME, 5_000_000, "frame")


def trial(path):
    sim, mem = start(path)
    # 1. bike on top of vehicle 0 for one frame
    mem[PX], mem[PY] = mem[TABLE], mem[TABLE + 1]
    mem[WAIT] = 0
    before = mem[SLEEP]
    frame(sim)
    sleep_after = mem[SLEEP]
    # 2. fuel counter about to roll over, bike moving (speed counter 0), well away from any vehicle
    mem[PX], mem[PY] = 59, 100
    mem[SPEED], mem[WAIT], mem[FUEL_ACC] = 0, 0, 255
    gauge = (mem[FUEL_C], mem[FUEL_B])
    frame(sim)
    return before, sleep_after, gauge, (mem[FUEL_C], mem[FUEL_B])


from skoolkit import tap2sna   # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import original   # noqa: E402

original.snapshot("original")                          # your copy of the game as loaded (tools/original.py)
os.makedirs("work/_tmp", exist_ok=True)
for out, tape in (("patched.z80", "work/biker_infinite.tap" if os.path.exists("work/biker_infinite.tap") else "work/biker_infinite.tzx"),
                  ("patched_fast.z80", "work/biker_infinite_fast.tap" if os.path.exists("work/biker_infinite_fast.tap") else "work/biker_infinite_fast.tzx")):
    if not os.path.exists(f"work/_tmp/{out}"):
        print("loading", tape, "...", flush=True)
        tap2sna.main(["-d", "work/_tmp", tape, out])

for label, path in (("original", "work/_tmp/original.z80"), ("patched ", "work/_tmp/patched.z80")):
    b, a, g0, g1 = trial(path)
    print(f"{label}: SLEEP {b} -> {a} after hitting a vehicle;  fuel gauge (C,B) {g0} -> {g1} after a counter roll-over")


def speed_trial(path):
    """Hold the right key for a few passes from a standstill (speed counter 10): the speed counter after each pass ($E4E8 does the counting)."""
    sim, mem = start(path)
    out = []
    for _ in range(4):
        mem[57255] = 2                                   # $DFA7: the direction input, bit 1 = right
        sim.registers[SP_REG] = (sim.registers[SP_REG] - 2) & 0xFFFF
        mem[sim.registers[SP_REG]] = mem[(sim.registers[SP_REG] + 1) & 0xFFFF] = 0     # return to $0000
        sim.registers[24] = 58603                        # $E4EB: the key test, after the key read
        while sim.registers[24] != 0:
            sim.opcodes[mem[sim.registers[24]]]()
        out.append(mem[SPEED])
    return out


for label, path in (("original    ", "work/_tmp/original.z80"), ("infinite    ", "work/_tmp/patched.z80"), ("infinite+fast", "work/_tmp/patched_fast.z80")):
    print(f"{label}: speed counter on four passes with a key held, starting stopped (10 = stopped, 0 = full speed): {speed_trial(path)}")


def day_trial(path):
    """Put the clock on eight o'clock (hour hand $DBD3 = 40, minute hand $DBD2 = 0) just after a frame and let the main loop test it:
    returns what happened ("the day ends" if the loop reaches the eight o'clock message at $E3A0, else "the game goes on")."""
    sim, mem = start(path)
    frame(sim)                                           # run one frame so the loop sits at $E2C1, right after the frame call
    mem[56275], mem[56274], mem[SLEEP] = 40, 0, 50
    regs, ops = sim.registers, sim.opcodes
    for _ in range(2000):
        ops[mem[regs[24]]]()
        if regs[24] == 58272:                            # $E3A0: "It's eight o'clock"
            return "the day ends"
        if regs[24] == LOOP:                             # back round the main loop
            return "the game goes on"
    return "?"


for label, path in (("original    ", "work/_tmp/original.z80"), ("infinite    ", "work/_tmp/patched.z80"), ("infinite+fast", "work/_tmp/patched_fast.z80")):
    print(f"{label}: clock on eight o'clock: {day_trial(path)}")
