"""Check the screens before the game: three loading screens from the tape, Select Controls, and their borders.

Usage: python tools/check_screens.py      (run from the repo root)

1. The tape's loader shows three screens in this order: the first 6912 bytes of its 7020-byte block (the cover), then the 6912-byte blocks of the KP Skips
   advert and of the title; assets/screen_cover.bin, screen_ad.bin and screen_title.bin must be exactly those.
2. The port shows them in that order with the ROM's white border, then Select Controls and the game with the blue border the menu sets.
"""
import os
import sys
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.chdir(ROOT)
import importlib.util   # noqa: E402
import pygame   # noqa: E402
import original   # noqa: E402

ok = True
name, data = original.unzip(original.find())
tape = [b for b in original.tape_blocks(name, data) if b[0] == 255]
want = [tape[1][1:6913], tape[3][1:6913], tape[5][1:6913]]      # blocks: BASIC, 7020 (cover), 17500, 6912 (advert), 17000, 6912 (title), the game's last part
sizes = [len(b) - 2 for b in tape]
print("tape data blocks:", sizes)
for n, expect in zip(("screen_cover.bin", "screen_ad.bin", "screen_title.bin"), want):
    same = open(os.path.join("assets", n), "rb").read() == bytes(expect)
    ok &= same
    print(f"assets/{n}: identical to the tape's screen: {same}")
ok &= sizes[1:6] == [7020, 17500, 6912, 17000, 6912]

spec = importlib.util.spec_from_file_location("biker", os.path.join(ROOT, "port", "biker.py"))
biker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biker)
seen = []


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))


def look(label):
    w = pygame.display.get_surface()
    scale = biker.SCALE
    seen.append((label, tuple(w.get_at((2, 2)))[:3], tuple(w.get_at(((biker.BORDER + 128) * scale, (biker.BORDER + 96) * scale)))[:3]))


def script():
    time.sleep(0.6)
    look("setup")
    key(pygame.K_RETURN)
    for n in (1, 2, 3):
        time.sleep(0.4)
        look(f"loading screen {n}")
        key(pygame.K_SPACE)
    time.sleep(0.4)
    look("select controls")
    key(pygame.K_5)
    time.sleep(0.8)
    look("game")
    key(pygame.K_ESCAPE)
    time.sleep(0.2)
    key(pygame.K_q)


threading.Thread(target=script, daemon=True).start()
biker.main(["--no-sound-effects", "--no-music"])
for label, border, centre in seen:
    print(f"{label:18s}: border {border}, middle of the picture {centre}")
borders = [b for _, b, _ in seen]
ok &= borders[1:4] == [biker.BORDER_LOADING] * 3 and borders[4:] == [biker.BORDER_GAME] * 2 and borders[0] == biker.BORDER_SETUP
ok &= len({c for _, _, c in seen[1:4]}) == 3                      # three different pictures
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
