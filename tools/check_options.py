"""Check the setup screen (port/options.py) by playing the start-up screens with simulated key presses (no window needed).

Usage: python tools/check_options.py      (run from the repo root)

1. On the setup screen tick 2 and 9 (infinite fuel, breadcrumbs) and untick S (sound effects), Enter; skip the two loading screens and choose
   keyboard controls (1): the game starts with those two fixes, and the saved choice has the sound effects off and the music on.
2. A second run with just Enter starts with the same choice.
3. --fix map_view starts the setup screen with only that line ticked (and the sound on), whatever was saved.
4. In a game P pauses (the clock stands still) and P carries on; Esc pauses too, and Q quits from the pause.
The saved choice goes to a scratch file here, not ~/.action_biker.json.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
import pygame   # noqa: E402
import biker   # noqa: E402
import options   # noqa: E402

options.SAVED = os.path.join(tempfile.mkdtemp(), "action_biker.json")


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


def run(keys, argv=()):
    """Play main() with one key press per frame, then a few empty frames and the window closed; the fixes of the game it started (None if none)."""
    frames = [[key(k)] for k in keys] + [[]] * 5
    made = []

    class World(biker.World):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            made.append(self)
    real, real_get = biker.World, pygame.event.get
    biker.World = World
    pygame.event.get = lambda *a, **kw: frames.pop(0) if frames else [pygame.event.Event(pygame.QUIT)]
    try:
        biker.main(list(argv))
    finally:
        biker.World, pygame.event.get = real, real_get
    return sorted(made[0].fixes) if made else None


START = [pygame.K_RETURN, pygame.K_SPACE, pygame.K_SPACE, pygame.K_1]    # Enter on the setup screen, skip the two loading screens, keyboard
first = run([pygame.K_2, pygame.K_9, pygame.K_s] + START)
saved = json.load(open(options.SAVED))
print("1. lines 2 and 9 ticked, S unticked:", first, saved)
again = run(START)
print("2. remembered next time:", again)
given = run(START, ["--fix", "map_view"])
print("3. --fix map_view:", given, json.load(open(options.SAVED)))


def pause_trial():
    """In a game: P pauses (the clock stands still for 60 frames), P carries on (it moves again), Esc pauses too, and Q quits from the pause."""
    made, seen = [], []
    script = [key(k) for k in START] + [None] * 200 + [key(pygame.K_p)] + [None] * 60 + [key(pygame.K_p)] + [None] * 60         + [key(pygame.K_ESCAPE)] + [None] * 5 + [key(pygame.K_q)]

    class World(biker.World):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            made.append(self)

    def get(*a, **kw):
        if made:
            w = made[0]
            seen.append((w.tick_pass, w.tick5, w.second))
        if not script:
            seen.append("still running")
            return [pygame.event.Event(pygame.QUIT)]
        e = script.pop(0)
        return [e] if e else []
    real, real_get = biker.World, pygame.event.get
    biker.World, pygame.event.get = World, get
    try:
        biker.main(["--no-sound-effects", "--no-music"])
    finally:
        biker.World, pygame.event.get = real, real_get
    return seen


seen = pause_trial()
paused_part, playing_part = seen[206:262], seen[266:322]    # frames well inside the pause (after the 4 s start fanfare), and after it
print("4. pause: clock while paused", "still" if len(set(paused_part)) == 1 else "MOVED", "| after P again",
      "moving" if len(set(playing_part)) > 1 else "STILL", "| Q quit from the Esc pause:", "still running" not in seen)
ok_pause = len(set(paused_part)) == 1 and len(set(playing_part)) > 1 and "still running" not in seen

ok = ok_pause and (first == ["breadcrumbs", "infinite_fuel"] and saved == {"fixes": first, "sound_effects": False, "music": True} and again == first
      and given == ["map_view"])
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
