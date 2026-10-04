"""Make a copy of the Action Biker tape (.tap and .tzx) in which SLEEP and fuel never go down, for testing.

Usage: python tools/make_patched_game.py [TAPE]     (run from the repo root; writes work/biker_infinite.tap and .tzx, or the one kind given)

The game code is stored on the tape exactly as it sits in memory, so three bytes can be changed in place; the tape block's
checksum byte (the XOR of the flag and data bytes) is then recalculated. Patches (addresses from notes/03-level-map.md):

  1. $D97F  (55679) DEC A -> NOP   the crash routine at $D95D: SLEEP is stored back unchanged after a hit (vehicle, water)
  2. $EF52  (61266) DEC A -> NOP   the oil handler: same, so oil costs nothing either
  3. $D9F8  (55800) JR $DA47 -> RET   the fuel routine at $DA03: the gauge never takes a step, so the tank stays full
  4. $E2E2  (58082) CP 40 -> CP 255   the end-of-game test in the main loop ($E2AE): it compares the clock's hour hand ($DBD3) with 40 and
                                      only then asks whether the minute hand is 0 (eight o'clock). The hand wraps at 60, so it is never 255
                                      and the day never ends. The clock itself keeps running: the hands move, SLEEP still recovers
                                      5 every 300 passes, the fuel cans come back and tea with the friend's mum still works.

Not changed: SLEEP still recovers (it is at 50 and stays there) and the clock still runs; only its eight o'clock ending is switched off.

A second pair of files, work/biker_infinite_fast.tap and .tzx, has one more byte changed (the four patches above plus this one) so the bike runs at full speed at once:

  5. $E4F5  (58613) AND A -> XOR A   the movement routine at $E4E8: while a direction key is held the speed counter ($E517) normally
                                     counts down one step a pass from 10 (stopped) to 0 (full speed); now `JR Z` always jumps over the
                                     `DEC A` and the counter is stored as 0 on the first pass.

Letting go still slows the bike down one step a pass (it coasts), and the turn animation still comes first. Fuel is not used up in
either file. Each patch pattern must occur exactly once in the file, or the script stops without writing anything.
"""
import glob
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from original import unzip   # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)

# (surrounding bytes to search for, offset of the byte to change inside them, expected old value, new value)
PATCHES = [
    ("sleep: crash routine DEC A -> NOP",
     bytes.fromhex("a7 c8 3d 32 04 5b cd 8d e0 c9 f5 3a 48 5c"), 2, 0x3D, 0x00),
    ("sleep: oil handler DEC A -> NOP",
     bytes.fromhex("3a 04 5b a7 28 10 3d 32 04 5b cd 8d e0 cd"), 6, 0x3D, 0x00),
    ("fuel: the gauge step JR -> RET",
     bytes.fromhex("3a 17 e5 fe 0a c8 4f 3e 0a 91 cb 3f 4f 3a e2 d9 81 32 e2 d9 d0 18 4d"), 21, 0x18, 0xC9),
    ("clock: the eight o'clock test CP 40 -> CP 255",
     bytes.fromhex("3a d3 db fe 28 28 18 3a 04 5b 3c ca"), 4, 0x28, 0xFF),
]


FAST = [
    ("speed: a held key sets the speed counter to 0 (AND A -> XOR A)",
     bytes.fromhex("3a 17 e5 a7 28 01 3d 32 17 e5 cd 1e e5 c9"), 3, 0xA7, 0xAF),
]


def apply_patches(data, patches=PATCHES):
    """Patch a bytearray; returns the list of file offsets changed."""
    changed = []
    for name, pattern, off, old, new in patches:
        hits = [i for i in range(len(data) - len(pattern) + 1) if data[i:i + len(pattern)] == pattern]
        if len(hits) != 1:
            sys.exit(f"patch '{name}': expected exactly one match, found {len(hits)}")
        at = hits[0] + off
        if data[at] != old:
            sys.exit(f"patch '{name}': byte at {at:#x} is {data[at]:#04x}, expected {old:#04x}")
        data[at] = new
        changed.append(at)
    return changed


def fix_tap(data, changed):
    """Recalculate the checksum of every TAP block that was touched. Returns the number fixed."""
    pos, fixed = 0, 0
    while pos < len(data):
        ln = data[pos] | data[pos + 1] << 8
        start, end = pos + 2, pos + 2 + ln          # block = flag + data + checksum
        if any(start <= c < end - 1 for c in changed):
            x = 0
            for b in data[start:end - 1]:
                x ^= b
            data[end - 1] = x
            fixed += 1
        pos = end
    return fixed


def fix_tzx(data, changed):
    """Same for a TZX: walk the blocks, fix standard-speed (0x10) and turbo (0x11) data blocks that were touched."""
    pos, fixed = 10, 0                               # after the 10-byte header "ZXTape!" 1A major minor
    while pos < len(data):
        bid = data[pos]
        if bid == 0x10:
            ln = data[pos + 3] | data[pos + 4] << 8
            start, end = pos + 5, pos + 5 + ln
        elif bid == 0x11:
            ln = data[pos + 16] | data[pos + 17] << 8 | data[pos + 18] << 16
            start, end = pos + 19, pos + 19 + ln
        else:                                        # blocks that carry no tape data: skip them
            skip = {0x30: lambda p: 2 + data[p + 1], 0x32: lambda p: 3 + (data[p + 1] | data[p + 2] << 8),
                    0x20: lambda p: 3, 0x21: lambda p: 2 + data[p + 1], 0x22: lambda p: 1,
                    0x31: lambda p: 3 + data[p + 2], 0x35: lambda p: 15 + (data[p + 11] | data[p + 12] << 8 | data[p + 13] << 16 | data[p + 14] << 24)}
            if bid not in skip:
                sys.exit(f"unexpected TZX block {bid:#x} at {pos:#x}: not handled")
            pos += skip[bid](pos)
            continue
        if any(start <= c < end - 1 for c in changed):
            x = 0
            for b in data[start:end - 1]:
                x ^= b
            data[end - 1] = x
            fixed += 1
        pos = end
    return fixed


def main():
    """Patch the .tap and .tzx of this project's folder, or the tape given on the command line (a .tap, .tzx, or a .zip holding one)."""
    if len(sys.argv) > 1:
        name, raw = unzip(sys.argv[1])
        ext = os.path.splitext(name)[1].lower().lstrip(".")
        if ext not in ("tap", "tzx"):
            sys.exit("give a .tap or .tzx tape (a snapshot cannot be patched this way)")
        sources = [(raw, ext, fix_tap if ext == "tap" else fix_tzx)]
    else:
        sources = [(open(glob.glob("Action-Biker_ZX-Spectrum_EN/*.TAP/*.tap")[0], "rb").read(), "tap", fix_tap),
                   (open(glob.glob("Action-Biker_ZX-Spectrum_EN/*.TZX/*.tzx")[0], "rb").read(), "tzx", fix_tzx)]
    os.makedirs("work", exist_ok=True)
    for tag, patches in (("infinite", PATCHES), ("infinite_fast", PATCHES + FAST)):
        for raw, ext, fix in sources:
            dst = f"work/biker_{tag}.{ext}"
            data = bytearray(raw)
            changed = apply_patches(data, patches)
            fixed = fix(data, changed)
            open(dst, "wb").write(bytes(data))
            print(f"{dst}: patched {len(changed)} bytes at {[hex(c) for c in changed]}, {fixed} block checksum(s) fixed")

if __name__ == "__main__":
    main()
