"""Check the speedometer needle in the pygame port against the original's routine (headless).

Usage: python tools/check_port_needle.py      (run from the repo root; needs assets/hud_needle.json from tools/extract_assets.py)

For each speed counter 0..10 the port draws its HUD; the pixels in the dial must be the bare panel plus exactly the needle pixels the
original's line routine draws, and the needle tip must move steadily from pointing right (counter 0, full speed) to lying left (counter 10, stopped).
"""
import importlib.util
import json
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
import pygame   # noqa: E402

pygame.init()
screen = pygame.display.set_mode((256, 192))
spec = importlib.util.spec_from_file_location("biker", os.path.join(ROOT, "port", "biker.py"))
biker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biker)

needle = json.load(open("assets/hud_needle.json"))
w = biker.World()
ok = True
tips = []
for speed in range(11):
    w.speed = speed
    screen.blit(w.hud, (0, 0))
    base = screen.copy()
    w.draw_hud(screen)
    changed = {(x, y) for y in range(84, 112) for x in range(165, 241) if screen.get_at((x, y))[:3] != base.get_at((x, y))[:3]}
    expect = {tuple(p) for p in needle[str(speed)]["set"] + needle[str(speed)]["clear"]}
    good = changed == expect                       # below the SLEEP digits: nothing but the needle changes
    ok &= good
    xs = [x for x, _ in expect]
    tips.append(min(xs) if speed >= 5 else max(xs))
    print(f"speed counter {speed:2d}: {len(expect):2d} needle pixels, x {min(xs)}..{max(xs)}  {good}")
mono = all(tips[i] > tips[i + 1] for i in range(10))
print("needle tip moves steadily from the right (full speed, counter 0) over the top to the left (stopped, counter 10):", mono)
ok &= mono

# the real snapshots: the needle on the original's screen is the one extracted for that snapshot's speed counter (value at $DB91 = 200 - 19 * counter)
import glob   # noqa: E402
from skoolkit.snapshot import Snapshot   # noqa: E402
hud = open("assets/hud.bin", "rb").read()


def off(x, y):
    return ((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2) | (x >> 3)


seen = set()
for f in sorted(glob.glob("work/biker_*.z80")):
    r = bytes(Snapshot.get(f).ram(1))
    counter = (200 - r[56209 - 0x4000]) // 19
    got = {(x, y) for y in range(84, 112) for x in range(165, 241) if ((r[off(x, y)] >> (7 - (x & 7))) & 1) != ((hud[off(x, y)] >> (7 - (x & 7))) & 1)}
    expect = {tuple(p) for p in needle[str(counter)]["set"] + needle[str(counter)]["clear"]}
    seen.add(counter)
    ok &= got == expect
    print(f"{os.path.basename(f):28s} speed counter {counter:2d}: needle identical to the original's screen: {got == expect}")
print("counters seen in real snapshots:", sorted(seen))
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
