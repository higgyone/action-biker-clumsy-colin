"""Load your own copy of the original game and run it in SkoolKit's Z80 simulator to the two moments the port's assets come from.

    from original import Original
    game = Original("path/to/Action Biker.tap")      # or .tzx, or .z80 saved at the Select Controls menu, or a .zip holding one of them
    game.menu    # 48K RAM (bytes, $4000-$FFFF) at the Select Controls menu, before any game: the clean map, the tape's traffic table
    game.level   # 48K RAM after key 1 and the game's own start-up ($D858), at the main loop: items placed, the HUD drawn
    game.screens # the tape's two loading screens (6912 bytes each), or [] for a snapshot
    snapshot("level")  # a .z80 path of that moment for the checks: work/biker_level.z80 if it exists (the ZEsarUX one), else
                       # work/_tmp/level.z80, made from your copy of the game when missing (likewise "menu": work/biker.z80)

A tape (.tap or .tzx) is loaded by SkoolKit's tape-loading simulator (tap2sna), so the game's own loader runs as on a real Spectrum. The
loaded snapshot is kept in work/_tmp/original.z80, which the comparison tools (compare_original.py and others) start from. A .z80 must be
of the game waiting at its Select Controls menu with no game played yet (most .z80 copies of the game are); one taken in the middle of a
game is refused, because the map and the house table no longer hold their start values. Its item seed ($5B00) is set to 0, as a fresh
load has it.

Copies differ: of the TOSEC set, the .tzx, the [a] .tap and the [a2] .tzx give exactly the assets the port was made with. The plain .tap
and the [a] .tzx load with the colours of buildings 4-8 ($787F-$7917) zeroed, so those buildings are black on black (as that tape plays);
a warning is printed. The [a] .z80 has damaged bike sprites at $5B09.

With no path, a copy found under game/ or Action-Biker_ZX-Spectrum_EN/ is used: a .tzx first, then a .tap, then a .z80, plain
names before [a] variants, as a file or inside a .zip.
"""
import glob
import io
import os
import zipfile

import skoolkit
from skoolkit.simulator import Simulator
from skoolkit.simutils import A, F, B, C, D, E, H, L, SP, I, R as RR
from skoolkit.snapshot import Snapshot, write_snapshot

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
TMP = os.path.join(ROOT, "work", "_tmp")
ROM = open(os.path.join(os.path.dirname(skoolkit.__file__), "resources", "48.rom"), "rb").read()
MENU_LOOP = range(0xDDC0, 0xDDE8)     # the Select Controls menu ($DD77) waiting for a key: the PCs .z80 copies of the game are saved at
LOOP = 58046                          # the main game loop ($E2AE) after the start-up
MAP = 0x9858
PICKUPS = (190, 194, 198)             # crisp packet, oil, fuel can: placed by a game's start-up, never on the map as the tape loads it
SEARCH = ("Action-Biker_ZX-Spectrum_EN", "game")
KINDS = (".tap", ".tzx", ".z80")


def find():
    """A copy of the game in the usual places, or None: a .tzx first, then a .tap, then a .z80 (a tape gives the loading screens, and of
    the TOSEC set the .tzx is a complete copy), each as a file or inside a .zip."""
    found = []
    for folder in SEARCH:
        for path in sorted(glob.glob(os.path.join(ROOT, folder, "**", "*"), recursive=True)):
            if not os.path.isfile(path):          # folders can be named like files ("... .TAP")
                continue
            low = path.lower()
            if low.endswith(".zip"):
                inner = [n.lower() for n in zipfile.ZipFile(path).namelist() if n.lower().endswith(KINDS)]
                kind = os.path.splitext(inner[0])[1] if inner else None
            else:
                kind = os.path.splitext(low)[1] if low.endswith(KINDS) else None
            if kind:
                found.append((KINDS.index(kind) if kind != ".tzx" else -1, "[" in os.path.basename(path), path))
    return min(found)[2] if found else None


def unzip(path):
    """(name, bytes) of the game file: the file itself, or the first .tap/.tzx/.z80 inside a .zip."""
    if path.lower().endswith(".zip"):
        zf = zipfile.ZipFile(path)
        name = next(n for n in zf.namelist() if n.lower().endswith(KINDS))
        return name, zf.read(name)
    return path, open(path, "rb").read()


def tape_blocks(name, data):
    """The data blocks of a .tap or .tzx (flag byte first, checksum last). TZX: standard (ID $10) and turbo (ID $11) blocks; the
    other block types carry no data or are skipped."""
    blocks = []
    if name.lower().endswith(".tap"):
        pos = 0
        while pos + 2 <= len(data):
            n = data[pos] | data[pos + 1] << 8
            blocks.append(data[pos + 2:pos + 2 + n])
            pos += 2 + n
        return blocks
    pos = 10
    skip = {0x12: 4, 0x20: 2, 0x22: 0, 0x24: 2, 0x25: 0, 0x2A: 4, 0x5A: 9}   # fixed-length blocks without data
    while pos < len(data):
        bid = data[pos]
        pos += 1
        if bid == 0x10:
            n = data[pos + 2] | data[pos + 3] << 8
            blocks.append(data[pos + 4:pos + 4 + n])
            pos += 4 + n
        elif bid == 0x11:
            n = data[pos + 15] | data[pos + 16] << 8 | data[pos + 17] << 16
            blocks.append(data[pos + 18:pos + 18 + n])
            pos += 18 + n
        elif bid == 0x14:
            n = data[pos + 7] | data[pos + 8] << 8 | data[pos + 9] << 16
            blocks.append(data[pos + 10:pos + 10 + n])
            pos += 10 + n
        elif bid == 0x13:
            pos += 1 + 2 * data[pos]
        elif bid == 0x15:
            n = data[pos + 5] | data[pos + 6] << 8 | data[pos + 7] << 16
            pos += 8 + n
        elif bid == 0x21 or bid == 0x30:
            pos += 1 + data[pos]
        elif bid == 0x31:
            pos += 2 + data[pos + 1]
        elif bid == 0x32:
            pos += 2 + (data[pos] | data[pos + 1] << 8)
        elif bid == 0x35:
            pos += 20 + int.from_bytes(data[pos + 16:pos + 20], "little")
        elif bid == 0x33:
            pos += 1 + 3 * data[pos]
        elif bid in skip:
            pos += skip[bid]
        else:
            raise ValueError(f"{name}: TZX block ${bid:02X} is not supported; try the .tap")
    return blocks


class Keys:
    """Port reads for the simulator: nothing pressed until `press` is set, then key 1 (row $F7FE) for the controls menu."""
    press = False

    def read_port(self, registers, port):
        return 0xFE if self.press and port & 0xFF == 0xFE and port >> 8 == 0xF7 else 0xFF


class Original:
    def __init__(self, path=None, quiet=False):
        path = path or find()
        if not path:
            raise SystemExit("No copy of Action Biker found: pass the path of your .tap, .tzx or .z80 (or put it in game/).")
        self.path = path
        name, data = unzip(path)
        os.makedirs(TMP, exist_ok=True)
        if name.lower().endswith((".tap", ".tzx")):
            self.screens = [b[1:6913] for b in tape_blocks(name, data) if len(b) == 6914 and b[0] == 255]
            tape = os.path.join(TMP, "original" + os.path.splitext(name)[1].lower())
            open(tape, "wb").write(data)
            snap = os.path.join(TMP, "original.z80")
            if not quiet:
                print(f"loading {os.path.basename(name)} in the tape-loading simulator ...", flush=True)
            from skoolkit import tap2sna
            here = os.getcwd()
            os.chdir(TMP)                              # tap2sna reads a path with a drive letter ("C:...") as a URL
            try:
                tap2sna.main(["-d", ".", os.path.basename(tape), "original.z80"])
            finally:
                os.chdir(here)
        else:
            self.screens = []
            snap = os.path.join(TMP, "original.z80")
            open(snap, "wb").write(data)
            # $5B00 holds the item generator's seed for the next game; a fresh load has 0 there, which a snapshot need not (some hold 1),
            # and the seed decides which houses get the items. Set it as a fresh load has it, so every copy starts the same first game.
            fixed = Snapshot.get(snap)
            fixed.poke(["23296-23297,0"])
            fixed.write(snap)
        self.snapshot = snap
        self.menu, self.level, self.menu_screen = self._run(snap)

    def _run(self, path):
        snap = Snapshot.get(path)
        mem = list(ROM) + list(snap.ram(1))
        regs = {"A": snap.a, "F": snap.f, "BC": snap.bc, "DE": snap.de, "HL": snap.hl, "IX": snap.ix, "IY": snap.iy, "SP": snap.sp,
                "I": snap.i, "R": snap.r}
        sim = Simulator(mem, regs, {"iff": 0, "im": 1}, {"fast_djnz": True, "fast_ldir": True})
        keys = Keys()
        sim.set_tracer(keys)
        R, ops = sim.registers, sim.opcodes
        R[24] = snap.pc
        n = 0
        while R[24] not in MENU_LOOP:                  # from the end of the loader (or the snapshot) to the menu waiting for a key
            ops[mem[R[24]]]()
            n += 1
            if n > 50_000_000:
                raise SystemExit(f"{self.path}: the game never reached its Select Controls menu - is this Action Biker?")
        menu = bytes(mem[0x4000:])
        self._save("menu", mem, R)
        m = menu[MAP - 0x4000:MAP - 0x4000 + 16384]
        if any(t in PICKUPS for t in m):
            raise SystemExit(f"{self.path}: this snapshot was saved after a game had started (the map holds pickups); use the tape or a "
                             "snapshot saved at the Select Controls menu before playing.")
        keys.press = True                              # key 1: keyboard controls, then the game's start-up runs to the main loop
        n = 0
        while R[24] != LOOP:
            ops[mem[R[24]]]()
            n += 1
            if n > 50_000_000:
                raise SystemExit(f"{self.path}: the game did not start after key 1")
        self._save("level", mem, R)
        return menu, bytes(mem[0x4000:]), menu[:6912]

    def _save(self, kind, mem, R):
        """Write the simulator's state as work/_tmp/<kind>.z80 (the checks start from these when the ZEsarUX snapshots are not there)."""
        from skoolkit.simutils import IXh, IXl, IYh, IYl
        regs = [f"a={R[A]}", f"f={R[F]}", f"bc={R[B] << 8 | R[C]}", f"de={R[D] << 8 | R[E]}", f"hl={R[H] << 8 | R[L]}",
                f"ix={R[IXh] << 8 | R[IXl]}", f"iy={R[IYh] << 8 | R[IYl]}", f"sp={R[SP]}", f"i={R[I]}", f"r={R[RR]}", f"pc={R[24]}"]
        write_snapshot(os.path.join(TMP, f"{kind}.z80"), list(mem[0x4000:]), regs, ["iff=0", "im=1"])


ZESARUX = {"menu": "work/biker.z80", "level": "work/biker_level.z80"}


def snapshot(kind):
    """Path of a .z80 at the menu or at the start of the level: the ZEsarUX one this project was made with if it is there, else one made in
    the simulator from your copy of the game (work/_tmp/menu.z80, level.z80), which is created on first use. "original": the game as
    loaded (work/_tmp/original.z80, at the end of the tape's loader or your snapshot), which compare_original.py and others start from."""
    own = os.path.join(ROOT, ZESARUX.get(kind, "-"))
    if os.path.exists(own):
        return own
    made = os.path.join(TMP, f"{kind}.z80")
    if not os.path.exists(made):
        Original(quiet=True)
    return made
