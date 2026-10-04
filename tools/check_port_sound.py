"""Headless check of the sound in the pygame port (no sound card needed).

Usage: python tools/check_port_sound.py      (run from the repo root)

1. Every sound is built from the original's own numbers: the ROM's BEEP gives frequency = 437500 / (HL + 30.125) and a length of
   DE cycles; the tunes are the three note tables read from the snapshot (assets/sounds.json).
2. The port plays the right sound at the right moment, using a recording stand-in for the sound card.
"""
import json
import os
import sys

import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
import importlib.util   # noqa: E402
import pygame           # noqa: E402
import sound            # noqa: E402

pygame.init()
pygame.display.set_mode((64, 64))
spec = importlib.util.spec_from_file_location("biker", os.path.join(ROOT, "port", "biker.py"))
biker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biker)

ok = True
tunes = json.load(open("assets/sounds.json"))
arrays = sound.samples(tunes)


def measured(wave):
    """(frequency in Hz, duration in ms) of a square wave from its zero crossings."""
    s = np.sign(wave.astype(np.int32))
    crossings = int((s[1:] != s[:-1]).sum())
    return crossings / 2 / (len(wave) / sound.RATE), 1000 * len(wave) / sound.RATE


# 1. the beeps follow the ROM formula
for name, (hl, de) in sound.BEEPS.items():
    f_expect, ms_expect = sound.frequency(hl), 1000 * sound.beep_seconds(hl, de)
    wave = sound.beep(hl, de)
    f, ms = measured(wave)
    if name == "tick":                                  # one 70 microsecond cycle: only the length can be checked
        good = abs(ms - ms_expect) < 0.05
        print(f"beep {name:5s}: HL={hl:3d} DE={de:3d} -> {len(wave)} samples = {ms:.3f} ms (expect {ms_expect:.3f})  {good}")
    else:
        cycles = de                                     # the crossings of a short beep can only be counted to about one sample
        good = abs(f - f_expect) / f_expect < max(0.03, 2.0 / cycles) and abs(ms - ms_expect) < 0.1
        print(f"beep {name:5s}: HL={hl:3d} DE={de:3d} -> {f:.0f} Hz (expect {f_expect:.0f}), {ms:.1f} ms (expect {ms_expect:.1f})  {good}")
    ok &= good

# the tunes: lengths from the notes
for name, notes in tunes.items():
    expect = sound.tune_seconds(notes)
    got = len(arrays[name]) / sound.RATE
    good = abs(got - expect) < 0.01 and len(notes) == {"start": 5, "end": 14, "win": 28, "house": 19}[name]
    print(f"tune {name:5s}: {len(notes):2d} notes, {got:.2f} s (expect {expect:.2f}) {good}")
    ok &= good
first = tunes["start"][0]
f, ms = measured(sound.beep(first[1], first[0]))
print(f"first note of the start-up fanfare: {f:.0f} Hz for {ms:.0f} ms (the table says HL={first[1]}, DE={first[0]} -> "
      f"{sound.frequency(first[1]):.0f} Hz, {1000 * sound.beep_seconds(first[1], first[0]):.0f} ms)")


# 2. when the port plays them
class Recorder:
    def __init__(self):
        self.log = []

    def seconds(self, name):
        return len(arrays[name]) / sound.RATE

    def play(self, name):
        self.log.append(name)

    def play_seq(self, name, count, gap, lead=0.0):
        if count > 0:
            self.log.append((name, count))


def door_with(w, flag):
    return next(d for d, f in w.houses.items() if f & flag)


rec = Recorder()
w = biker.World(rec)
intro = round(rec.seconds("start") * biker.PASS_HZ)
table = [list(e) for e in w.traffic.table]
for _ in range(intro):
    w.tick(0)
paused = [list(e) for e in w.traffic.table] == table and rec.log == ["start"]
print(f"start-up: fanfare plays once, the game waits {intro} passes (nothing moves, no ticks): {paused}")
ok &= paused and w.intro == 0
rec.log.clear()
w.place(1, 1)
for _ in range(3):
    w.tick(0)
ticks = rec.log.count("tick")
print("a click every pass:", ticks, "ticks in 3 passes")
ok &= ticks == 3

# a crash runs $D95D on every pass of an overlap; the routine holds the game up for 76 ms (two 27 ms beeps, two 7 ms flashes, then SLEEP and the score)
crash_ms = 1000 * len(arrays["crash"]) / sound.RATE
print(f"crash sound: {crash_ms:.1f} ms (the original's routine takes 75.9 ms in the simulator)")
ok &= abs(crash_ms - 75.9) < 0.6
rec.log.clear()
w.place(w.traffic.table[0][0], w.traffic.table[0][1])
w.traffic.update = lambda: None                      # hold the vehicle still so the overlap lasts
sleep0 = w.sleep
passes = 60
for _ in range(passes):
    w.tick(0)
crashes = rec.log.count("crash")
expect = passes / (1 + biker.CRASH_SECONDS * biker.PASS_HZ)     # each overlap pass costs 1 pass + the routine's 76 ms
print(f"crash: {crashes} crashes in {passes} passes of overlap (expect about {expect:.0f}: one on every pass that runs, the game stands still for the rest of each beep); SLEEP {sleep0} -> {w.sleep}")
ok &= abs(crashes - expect) <= 1 and sleep0 - w.sleep == min(crashes, sleep0)

# pickups and hazards
w = biker.World(rec)
rec.log.clear()
ys, xs = (w.map == 190).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
ok &= rec.log == ["crisp"]
print("crisp packet plays:", rec.log)
rec.log.clear()
w.fuel = 10
ys, xs = (w.map == 198).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
ok &= rec.log == [("step", 8)]
print("fuel can with 8 steps missing plays:", rec.log)
rec.log.clear()
w.speed, w.items = 0, 0
ys, xs = (w.map == 194).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
ok &= rec.log == [("tick", 16)]
print("oil at full speed plays:", rec.log)
rec.log.clear()
ys, xs = (w.map == 65).nonzero()
w.items = 0
w.hit_tile(int(xs[0]), int(ys[0]))
ok &= rec.log == ["crash"]
print("water without the snorkel plays:", rec.log)
w = biker.World(rec)
w.intro = 0
w.place(1, 1)
w.speed, w.fuel_acc = 0, 255
rec.log.clear()
w.tick(0)
ok &= "step" in rec.log
print("a fuel gauge step plays a click:", "step" in rec.log)

# leaving a house: the jingle after the message, the room stays up for it
w = biker.World(rec)
w.intro = 0
door = door_with(w, 1)
w.marker = door
w.park()
while w.walk:
    w.tick(0)
jingle = round(rec.seconds("house") * biker.PASS_HZ)
rec.log.clear()
total = w.inside[1]
passes = 0
played_at = None
while w.inside:
    w.tick(0)
    passes += 1
    if "house" in rec.log and played_at is None:
        played_at = passes
bar_passes = total - jingle
print(f"house: room lasts {total} passes = message {bar_passes} + jingle {jingle}; jingle started after {played_at} passes (expect {bar_passes}); played {rec.log.count('house')}x")
ok &= total == w.bar.total + jingle if w.bar else True
ok &= rec.log.count("house") == 1 and played_at is not None and abs(played_at - bar_passes) <= 1

# the endings: messages first (2.46 s pauses), then the tune, then a new game with its fanfare; the finish has its own tune
for label, tune, setup in (("SLEEP 0", "end", lambda w: setattr(w, "sleep", 0)),
                           ("the finish", "win", lambda w: (setattr(w, "items", w.items | 32), setattr(w, "px", 105), setattr(w, "py", 27)))):
    w = biker.World(rec)
    w.intro = 0
    rec.log.clear()
    setup(w)
    w.tick(0)
    messages = w.bar.total
    limit = messages + round(rec.seconds(tune) * biker.PASS_HZ)
    ok &= w.over_limit == limit and tune not in rec.log
    n, played_at = 0, None
    while w.over and n < limit + 10:
        w.tick(0)
        n += 1
        if tune in rec.log and played_at is None:
            played_at = n
    print(f"{label}: messages {messages} passes ({messages / biker.PASS_HZ:.1f} s), tune '{tune}' started after {played_at}, new game after {n} passes (expect about {limit}), fanfare again: {rec.log.count('start')}")
    ok &= abs(n - limit) <= 2 and rec.log.count("start") == 1 and played_at is not None and abs(played_at - messages) <= 1 and rec.log.count(tune) == 1

# the real thing, on a dummy audio device: every sound builds and plays
real = sound.Sound(tunes)
for name in list(real.arrays):
    real.play(name)
real.play_seq("tick", 16, 0.033)
print("pygame mixer builds and plays all", len(real.arrays), "sounds")
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
