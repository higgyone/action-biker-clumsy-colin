"""Check each fix of the port (the optional changes to the game; the default game is checked against the original by compare_original.py).

Usage: python tools/check_port_fixes.py      (run from the repo root)
"""
import importlib.util
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
import pygame   # noqa: E402

pygame.init()
pygame.display.set_mode((64, 64))
spec = importlib.util.spec_from_file_location("biker", os.path.join(ROOT, "port", "biker.py"))
biker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biker)
L, R, U, D = biker.LEFT, biker.RIGHT, biker.UP, biker.DOWN
KEY = {L: 1, R: 2, U: 4, D: 8}
ok = True


def world(*fixes):
    w = biker.World(None, fixes)
    w.intro = 0
    w.traffic.update = lambda: None                       # keep the vehicles out of these tests
    return w


def face(w, direction, x, y, speed=10, wait=0):
    w.place(x, y)
    w.heading, w.angle, w.speed, w.wait, w.last_keys = direction, biker.FRAME[direction], speed, wait, 0


print("fixes:", ", ".join(biker.FIXES))
# 1. infinite sleep, fuel, time
w = world("infinite_sleep")
w.crash(); w.lose_sleep()
w.items = 0
ys, xs = (w.map == 65).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
w.speed = 0
ys, xs = (w.map == 194).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
for _ in range(80):
    w.tick(0)
good = w.sleep == 50 and not w.over
print("infinite_sleep: SLEEP after a crash, water and oil:", w.sleep, good)
ok &= good
w = world("infinite_fuel")
w.place(1, 1)
w.speed, w.fuel_acc = 0, 255
for _ in range(400):
    w.speed, w.wait = 0, 0
    w.tick(0)
    w.sleep = 50
good = w.fuel == biker.FUEL_MAX
print("infinite_fuel: fuel after 400 passes of full speed:", w.fuel, good)
ok &= good
w = world()
w.place(1, 1)
w.fuel = 0
w.tick(0)
ok &= bool(w.over)
w = world("infinite_fuel", "infinite_time")
w.place(1, 1)
w.hour, w.tick5, w.second, w.tick_pass = 39, 1, 59, 1                  # one pass from eight o'clock
w.tick(0)
good = (w.hour, w.second) == (40, 0) and not w.over
print("infinite_time: the clock reaches eight o'clock:", (w.hour, w.second), "and the day goes on:", good)
ok &= good
w = world()
w.place(1, 1)
w.hour, w.tick5, w.second, w.tick_pass = 39, 1, 59, 1
w.tick(0)
ok &= bool(w.over)

FREE = next(d for d in (L, R, D, U) if world().can_go(59, 100, d))     # a way out of the start tile
# 2. quick_start: the passes from a standstill (just stopped, wait 10) until the bike has moved a tile
for fixes in ((), ("quick_start",)):
    w = world(*fixes)
    face(w, FREE, 59, 100, wait=10)
    n = 0
    while (w.px, w.py) == (59, 100) and n < 60:
        w.tick(KEY[FREE])
        n += 1
    print(f"quick_start {'on ' if fixes else 'off'}: first step after {n} passes, speed counter then {w.speed}")
    if fixes:
        ok &= n <= 1 and w.speed <= 8
    else:
        ok &= n >= 10

# 3. quick_turns: the bike facing right at speed counter 7 asked to go left: passes until it faces left
for fixes in ((), ("quick_turns",)):
    w = world(*fixes)
    face(w, R, 59, 100, speed=7, wait=7)
    n = 0
    while w.angle != biker.FRAME[L] and n < 100:
        w.tick(KEY[L])
        n += 1
        w.speed = 7                                       # hold the slow speed to isolate the turn
    print(f"quick_turns {'on ' if fixes else 'off'}: half turn at a slow speed took {n} passes")
    if fixes:
        ok &= n <= 4
    else:
        ok &= n >= 20

# 4. turn_assist
w0 = world()
spots_early, spots_side = [], []
for y in range(2, 125):
    for x in range(2, 125):
        if not w0.footprint_free(x, y):
            continue
        if w0.can_go(x, y, R) and not w0.can_go(x, y, U) and w0.can_go(x + 1, y, U) and w0.footprint_free(x + 1, y) and w0.can_go(x + 1, y, R):
            spots_early.append((x, y))
        if not w0.can_go(x, y, U) and w0.footprint_free(x + 1, y) and w0.can_go(x + 1, y, U):
            spots_side.append((x, y))
print(f"turn_assist: {len(spots_early)} places where an early 'up' meets a junction one tile on, {len(spots_side)} where the road is a tile to the side")
x, y = spots_early[len(spots_early) // 2]
res = {}
for fixes in ((), ("turn_assist",)):
    w = world(*fixes)
    face(w, R, x, y, speed=0)
    for _ in range(30):
        w.wait = 0
        w.tick(KEY[U])
        w.speed = 0
    res[bool(fixes)] = (w.px, w.py)
print(f"  early turn from {(x, y)} heading right, up held for 30 passes: without the fix the bike ends at {res[False]}, with it at {res[True]}")
ok &= res[False][1] == y and res[True][1] < y
x, y = spots_side[len(spots_side) // 2]
res = {}
for fixes in ((), ("turn_assist",)):
    w = world(*fixes)
    face(w, U, x, y, speed=0)
    for _ in range(30):
        w.wait = 0
        w.tick(KEY[U])
        w.speed = 0
    res[bool(fixes)] = (w.px, w.py)
print(f"  a tile off the side road at {(x, y)} heading up: without the fix {res[False]}, with it {res[True]}")
ok &= res[False] == (x, y) and res[True][1] < y
# the assist never changes a move that is free anyway
w1, w2 = world(), world("turn_assist")
for w in (w1, w2):
    face(w, U, 59, 100, speed=0)
    for _ in range(12):
        w.wait = 0
        w.tick(KEY[U])
        w.speed = 0
same = (w1.px, w1.py) == (w2.px, w2.py)
print("  a free road is ridden the same with and without it:", same)
ok &= same

# 4b. easy_parking (the house stop fix): Space with the bike stopped on a door marker enters the house; in the original it does not
door = next(d for d in world().houses if world().door_cell(d))
mx, my = world().door_cell(door)
res = {}
for fixes in ((), ("easy_parking",)):
    w = world(*fixes)
    face(w, U, mx, my, wait=0)
    w.tick(0, True)
    res[bool(fixes)] = w.walk is not None
print("easy_parking: stopped on a door, Space enters the house - original:", res[False], " with the fix:", res[True])
ok &= res[False] is False and res[True] is True
# ... and from a tile beside the marker, or one row off, the bike ends on the marker, so Colin walks up the path to the door
tries = entered = on_marker = 0
for d in [d for d in world().houses if world().door_cell(d)][:10]:
    mx, my = world().door_cell(d)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            w = world("easy_parking")
            if not w.footprint_free(mx + dx, my + dy):
                continue
            face(w, L, mx + dx, my + dy, wait=0)
            w.tick(0, True)
            tries += 1
            entered += w.walk is not None
            on_marker += w.walk is not None and (w.px, w.py) == (mx, my)
print(f"easy_parking: {tries} stops at or next to a door, {entered} enter the house, {on_marker} with the bike on the door's marker")
ok &= tries > 20 and entered == tries and on_marker == tries
# ... and at a door whose id two houses share (232), the bike stays at the house it stopped at instead of jumping to the other one
shared = [(d, c) for d in range(205, 256) for c in world().door_cells(d) if len(world().door_cells(d)) > 1]
stays = 0
for d, (mx, my) in shared:
    w = world("easy_parking")
    x = next(x for x in (mx, mx - 1, mx + 1) if w.footprint_free(x, my))
    face(w, L, x, my, wait=0)
    w.tick(0, True)
    stays += w.walk is not None and (w.px, w.py) == (mx, my)
print(f"easy_parking: shared door ids {sorted({d for d, _ in shared})}: {stays} of {len(shared)} stops stay at their own house")
ok &= len(shared) >= 2 and stays == len(shared)

# 5. item_markers
w = world("item_markers")
door, flags = next((d, f) for d, f in w.houses.items() if f and w.door_cell(d))
cx, cy = w.door_cell(door)
w.place(cx, cy)
surf = pygame.Surface((256, 192))
real = time.monotonic
time.monotonic = lambda: 0.0                              # the marker blinks: draw it in its "on" half
w.draw(surf)
off = surf.copy()
w.toggle_markers()
w.draw(surf)
on = surf.copy()
time.monotonic = real
px, py = (cx - w.camera()[0] + biker.VIEW_X) * 8, (cy - w.camera()[1] + biker.VIEW_Y) * 8
centre = tuple(on.get_at((px + 4, py + 4)))[:3]
changed = sum(1 for yy in range(192) for xx in range(256) if on.get_at((xx, yy)) != off.get_at((xx, yy)))
good = centre in ((255, 255, 0), (255, 0, 0), (0, 255, 255)) and changed > 20
print(f"item_markers: door {door} holds items {flags:07b}: marker colour {centre}, {changed} pixels drawn; hidden again after a second toggle:",
      end=" ")
w.toggle_markers()
time.monotonic = lambda: 0.0
w.draw(surf)
time.monotonic = real
hidden = all(surf.get_at((xx, yy)) == off.get_at((xx, yy)) for yy in range(192) for xx in range(256))
print(hidden)
ok &= good and hidden
# 6. breadcrumbs: a dot for every tile ridden, shown and hidden with B
res = {}
for fixes in ((), ("breadcrumbs",)):
    w = world(*fixes)
    face(w, FREE, 59, 100, speed=0)
    for _ in range(12):
        w.wait = 0
        w.tick(KEY[FREE])
        w.speed = 0
    res[bool(fixes)] = len(w.trail)
w.show_trail = True
surf = pygame.Surface((256, 192))
w.draw(surf)
shown = surf.copy()
w.show_trail = False
w.draw(surf)
differ = sum(1 for yy in range(8, 152) for xx in range(8, 152) if shown.get_at((xx, yy)) != surf.get_at((xx, yy)))
orange = sum(1 for yy in range(8, 152) for xx in range(8, 152) if tuple(shown.get_at((xx, yy)))[:3] == (255, 140, 0))
print(f"breadcrumbs: tiles remembered without the fix {res[False]}, with it {res[True]}; trail drawn: {differ} pixels differ, {orange} crumb pixels; hidden again after B")
ok &= res[False] == 0 and res[True] >= 5 and differ > 10 and orange > 10
w.new_game()
ok &= len(w.trail) <= 1                      # a new game starts the trail again (with the start tile)
# ... and where the bike stopped to go into a house the crumb is bigger, with a white ring; a new game forgets them
w = world("breadcrumbs", "easy_parking")
door = next(d for d in w.houses if w.door_cell(d))
mx, my = w.door_cell(door)
face(w, L, mx, my, wait=0)
w.tick(0, True)
while w.walk or w.inside:
    w.tick(0)
for _ in range(40):
    w.tick(1)
w.toggle_trail()
surf = pygame.Surface((256, 192))
w.draw(surf)
cx, cy = w.camera()
sx, sy = (mx + 1 - cx + biker.VIEW_X) * 8, (my + 1 - cy + biker.VIEW_Y) * 8
ring = sum(tuple(surf.get_at((sx + i, sy + j)))[:3] == (255, 255, 255) for i in range(-5, 6) for j in range(-5, 6))
print(f"breadcrumbs: the stop at house {door} is remembered: {(mx, my) in w.stops}, drawn with a white ring: {ring} white pixels around it")
ok &= (mx, my) in w.stops and ring >= 12
w.new_game()
ok &= not w.stops
# ... and when easy parking nudges the bike onto the door's path, the tiles it moves over join the trail (no gap in the crumbs)
gaps = 0
for d in [d for d in world().houses if world().door_cell(d)][:10]:
    mx, my = world().door_cell(d)
    for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1), (1, 0), (-1, 0)):
        w = world("breadcrumbs", "easy_parking")
        if not w.footprint_free(mx + dx, my + dy):
            continue
        face(w, L, mx + dx, my + dy, wait=0)
        w.trail = {(mx + dx, my + dy): 0}
        w.tick(0, True)
        if w.walk is not None:
            path = list(w.trail)
            gaps += any(abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1 for a, b in zip(path, path[1:])) or path[-1] != (mx, my)
print(f"breadcrumbs: easy parking's nudge onto the door leaves {gaps} gaps in the trail")
ok &= gaps == 0
# 7. map_view: Tab shows the whole map, you, where you have been and the box of the screen; the game waits meanwhile
w = world("map_view", "breadcrumbs")
face(w, FREE, 59, 100, speed=0)
for _ in range(14):
    w.wait = 0
    w.tick(KEY[FREE])
    w.speed = 0
here = (w.px, w.py)
w.toggle_map()
frozen = (w.px, w.py, w.sleep, w.hour, w.second)
for _ in range(30):
    w.tick(KEY[FREE])
paused = (w.px, w.py, w.sleep, w.hour, w.second) == frozen
real = time.monotonic
time.monotonic = lambda: 0.0
surf = pygame.Surface((256, 192))
w.draw(surf)
time.monotonic = real
scale = 192 / 128
red = tuple(surf.get_at((int(here[0] * scale) + 1, int(here[1] * scale) + 1)))[:3]
orange = sum(1 for yy in range(192) for xx in range(192) if tuple(surf.get_at((xx, yy)))[:3] == (255, 140, 0))
white = sum(1 for yy in range(192) for xx in range(192) if tuple(surf.get_at((xx, yy)))[:3] == (255, 255, 255))
print(f"map_view: game paused while the map is up {paused}; you at {here} drawn {red}; {orange} trail pixels, {white} frame pixels")
edge_x, edge_y = int((biker.DARK_X + 1) * scale), int((biker.DARK_Y + 1) * scale)
pink_v = sum(tuple(surf.get_at((edge_x, yy)))[:3] == (255, 0, 255) for yy in range(edge_y, 192))
pink_h = sum(tuple(surf.get_at((xx, edge_y)))[:3] == (255, 0, 255) for xx in range(0, edge_x))
print(f"map_view: the dark area's edge drawn along x {edge_x} ({pink_v} pixels) and y {edge_y} ({pink_h} pixels)")
ok &= pink_v > 10 and pink_h > 10
w.toggle_map()
for _ in range(30):                                       # back in the game the bike rides on
    w.wait = 0
    w.tick(KEY[FREE])
    w.speed = 0
resumed = (w.px, w.py) != here
ok &= paused and red == (255, 0, 0) and orange >= 10 and white >= 50 and resumed
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
