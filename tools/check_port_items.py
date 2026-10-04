"""Headless check of the item points and the tea in the pygame port (no window needed).

Usage: python tools/check_port_items.py      (run from the repo root)

Rules decoded from $FD63 and $FD45 (notes/03-level-map.md): each item scores 10 (Martin 100, the friend's mum 0) on top of
the 3 for a visit and leaves the room; the Turbo DIY kit does nothing; tea runs the clock 600 passes (SLEEP +10, hour hand +10) over 0.84 s after the
mum's message, the hands moving on the HUD.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
import importlib.util   # noqa: E402
import pygame           # noqa: E402

pygame.init()
pygame.display.set_mode((64, 64))
spec = importlib.util.spec_from_file_location("biker", os.path.join(ROOT, "port", "biker.py"))
biker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(biker)

ok = True


def door_with(w, flag):
    return next(d for d, f in w.houses.items() if f & flag)


def enter(w, door):
    """Park at a door and let Colin walk in; returns once the room is showing."""
    w.marker = door
    w.park()
    while w.walk:
        w.tick(0)


def visit(w, door):
    enter(w, door)
    while w.inside:                       # let the room close
        w.tick(0)


# 1. points per item and removal from the room
w = biker.World()
for flag, pts in ((1, 10), (2, 10), (4, 10), (8, 10), (16, 10), (32, 100)):
    door = door_with(w, flag)
    before = w.score
    visit(w, door)
    got = w.score - before
    gone = not w.houses[door] & flag
    print(f"item {flag:2d} ({biker.ITEM_NAMES[flag]:14s}) door {door}: score +{got} (expect {3 + pts}), taken from the room: {gone}")
    ok &= got == 3 + pts and gone and bool(w.items & flag)
martin_door = 242
for label, door in (("revisit Martin's emptied house", martin_door), ("a door with no items at all", 205)):
    before = w.score
    visit(w, door)
    print(f"{label}: score +{w.score - before} (expect 3), message: {w.message!r}")
    ok &= w.score - before == 3 and w.message == "No items in this house"

# 2. the Turbo kit does nothing to speed or fuel
w = biker.World()
speed, fuel = w.speed, w.fuel
w.items |= 16
w.tick(0)
ok &= (w.speed, w.fuel) == (speed, fuel)
print("Turbo kit: speed and fuel unchanged:", (w.speed, w.fuel) == (speed, fuel))

# 3. tea: 600 clock passes, SLEEP +10, hour +10, no fuel, the mum stays
w = biker.World()
mum = door_with(w, biker.MUM)
w.sleep = 20
state = (w.tick_pass, w.tick5, w.second, w.hour)
fuel = w.fuel
w.marker = mum
w.park()
before = (w.sleep, w.hour)
while w.walk or (w.bar and w.bar.at("tea") is None and w.tea_done == 0):   # nothing happens to the clock until the tea step
    w.tick(0)
during = []
while w.tea_done is not None:
    w.tick(0)
    during.append(w.hour)
print("tea runs after the message lines:", before == (20, state[3]), " over", len(during), "passes, hour hand", during)
ok &= before == (20, state[3]) and len(during) >= 10 and len(set(during)) > 5
print("tea: SLEEP", 20, "->", w.sleep, "(expect 30)  hour", state[3], "->", w.hour, "(expect", (state[3] + 10) % 60, ")",
      " second", state[2], "->", w.second, " fuel", fuel, "->", w.fuel)
ok &= w.sleep == 30 and w.hour == (state[3] + 10) % 60 and w.second == state[2] and w.fuel == fuel
while w.walk or w.inside:
    w.tick(0)
ok &= bool(w.houses[mum] & biker.MUM)
w.sleep = 47
w.marker = mum
w.park()
while w.walk or w.inside:
    w.tick(0)
print("tea again at SLEEP 47 ->", w.sleep, "(capped at 50)")
ok &= w.sleep == 50

# 4. the messages: the texts are the game's own (assets/messages.json), two lines per item, shown one after the other
w = biker.World()
M = w.msgs
for flag, idx in biker.ITEM_INDEX.items():
    door = door_with(w, flag)
    enter(w, door)
    good = w.bar.lines == M["items"][idx] and len(w.bar.lines) == 2 and all(len(t) == 24 for t in w.bar.lines)
    ok &= good
    rested, passes = [], 0                            # the lines that were seen at rest on the middle row, in order
    while w.bar:
        for text, y in w.bar.frame():
            if y == 168 and (not rested or rested[-1] != text):
                rested.append(text)
        w.tick(0)
        passes += 1
    one_at_a_time = rested == M["items"][idx]
    expect = round(biker.PAUSE_ITEM * biker.PASS_HZ) * 3 + 3 * biker.SCROLL_PASSES
    if flag == biker.MUM:                             # the tea comes before the line goes (0.84 s, measured: the visit is 9.47 s from the room to the end)
        expect += round(biker.TEA_SECONDS * biker.PASS_HZ)
    ok &= one_at_a_time and passes == expect
    while w.inside:
        w.tick(0)
    print(f"item {biker.ITEM_NAMES[flag]:18s}: line 1 {M['items'][idx][0].strip()!r}, then line 2 {M['items'][idx][1].strip()!r}, one at a time: "
          f"{one_at_a_time}, {passes} passes (expect {expect}): {good}")
w = biker.World()
enter(w, 205)
ok &= w.bar.lines == M["no_items"]
print("a door with no items shows:", w.bar.lines[0].strip())
# pickups: the crisp packet speaks only inside the dark area (the original tests $F005 first); outside, the score goes up at once
w = biker.World()
ys, xs = (w.map == 190).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
ok &= w.bar is None and w.score == 2
print("crisp packet outside the dark area: no message, score", w.score, "(expect 2)")
w = biker.World()
w.dark_flag = 0
w.hit_tile(int(xs[1]), int(ys[1]))
ok &= w.bar and w.bar.lines == M["crisps"] and w.score == 0
print("crisp packet inside the dark area shows:", w.bar.lines[0].strip(), "- score still", w.score, "until the message is over")
# the endings use the game's texts, two lines each (messages 0+1 eight o'clock, 2+3 SLEEP 0, 4+5 fuel), then the bar goes empty
for label, setup, pair in (("SLEEP 0", lambda w: setattr(w, "sleep", 0), (2, 4)), ("eight o'clock", lambda w: w.__dict__.update(hour=39, tick5=1, second=59, tick_pass=1), (0, 2)),
                           ("no fuel", lambda w: setattr(w, "fuel", 0), (4, 6))):
    w = biker.World()
    setup(w)
    w.tick(0)
    good = bool(w.over) and w.bar.lines == M["ending"][pair[0]:pair[1]] and not w.bar.hold
    ok &= good
    print(f"{label} shows:", [t.strip() for t in w.bar.lines], "(held:", w.bar.hold, ")", good)
w = biker.World()
w.items |= 32
w.place(105, 27)
w.tick(0)
ok &= bool(w.over) and w.bar.lines == M["finish"]
print("the finish shows:", [t.strip() for t in w.bar.lines])

# 4b. the message routines block the game: everything else stands still for the whole message, and some effects fall in the middle of it.
#     The total lengths are the original's, measured by running each handler in the simulator (T-states at 3.5 MHz): crisps inside the dark 1.279 s,
#     dark in 2.375 s, dark out 0.965 s, fuel can with 6 steps missing 1.298 s, oil 2.643 s.
def hit(tile, setup=None):
    w = biker.World()
    w.intro = 0
    if setup:
        setup(w)
    ys, xs = (w.map == tile).nonzero()
    w.hit_tile(int(xs[0]), int(ys[0]))
    return w


def frozen_for(w):
    """Passes the world stays put (traffic table unchanged) after the event."""
    table = [list(e) for e in w.traffic.table]
    n = 0
    while True:
        w.tick(0)
        if [list(e) for e in w.traffic.table] != table:
            return n
        n += 1
        if n > 500:
            return n


for label, tile, setup, seconds in (("crisps in the dark", 190, lambda w: setattr(w, "dark_flag", 0), 1.279), ("dark in", 203, None, 2.375),
                                    ("dark out", 204, lambda w: setattr(w, "dark_flag", 0), 0.965),
                                    ("fuel can, 6 steps missing", 198, lambda w: setattr(w, "fuel", biker.FUEL_MAX - 6), 1.298),
                                    ("oil at full speed", 194, lambda w: setattr(w, "speed", 0), 2.643)):
    w = hit(tile, setup)
    total = w.bar.total / biker.PASS_HZ
    stalled = frozen_for(w)
    good = abs(total - seconds) < 0.12 and abs(stalled / biker.PASS_HZ - seconds) < 0.2
    ok &= good
    print(f"{label:26s}: message {total:.2f} s (original {seconds} s), game stands still for {stalled / biker.PASS_HZ:.2f} s  {good}")
w = hit(194, lambda w: setattr(w, "speed", 0))
sleep0, score0 = w.sleep, w.score
mid = w.bar.steps[4][0]
for _ in range(mid - 1):
    w.tick(0)
before = w.sleep
w.tick(0)
w.tick(0)
print(f"oil: SLEEP {sleep0} -> {before} before line 2 is in, -> {w.sleep} just after (the original takes it at {mid / biker.PASS_HZ:.2f} s)")
ok &= before == sleep0 and w.sleep == sleep0 - 1
w = hit(190, lambda w: setattr(w, "dark_flag", 0))
for _ in range(w.bar.total - 1):
    w.tick(0)
early = w.score
w.tick(0)
w.tick(0)
print(f"crisps in the dark: score {early} until the message ends, then {w.score}")
ok &= early == 0 and w.score == 2
# the spin of the bike while it skids: frame + 1 for every 34.8 ms, all the way round twice, ending on the starting frame
w = hit(194, lambda w: setattr(w, "speed", 0))
w.angle = 3
w.skid_from = 3
seen = []
class Surf:
    pass
for _ in range(w.bar.total):
    spin = w.bar.at("skid")
    if spin is not None:
        frame = (w.skid_from + 1 + min(15, int(spin / biker.PASS_HZ / biker.SKID_STEP))) % 8
        if not seen or seen[-1] != frame:
            seen.append(frame)
    w.tick(0)
print("frames shown while skidding from frame 3:", seen)
ok &= len(seen) >= 8 and seen[0] == 4 and all((b - a) % 8 in (1, 2) for a, b in zip(seen, seen[1:]))

# 4c. the crash flash inverts ink and paper of the play area for about 34 ms ($D99B) and only there (colour channels on go off, off go on)
import time   # noqa: E402
import pygame   # noqa: E402
w = biker.World()
w.intro = 0
surf = pygame.Surface((256, 192))
w.draw(surf)
normal = surf.copy()
w.flash_at = time.monotonic() - 0.040                  # 40 ms into a crash: inside the 31-65 ms window
w.draw(surf)
flashed = surf.copy()
w.flash_at = time.monotonic() - 0.100                  # long over
w.draw(surf)
after = surf.copy()
arr_n, arr_f = pygame.surfarray.array3d(normal), pygame.surfarray.array3d(flashed)
play = (slice(8, 152), slice(8, 152))
level = (arr_n[play].max(axis=2, keepdims=True) == 255) * 50 + 205
expected = ((arr_n[play] > 0) * 0 + (arr_n[play] == 0) * level).astype("uint8")
inside = bool((arr_f[play] == expected).all())
outside_same = bool((arr_f[:8] == arr_n[:8]).all() and (arr_f[:, 152:] == arr_n[:, 152:]).all())
print(f"crash flash: play area inverted {inside}, border and HUD untouched {outside_same}, normal again afterwards {pygame.image.tobytes(after, 'RGB') == pygame.image.tobytes(normal, 'RGB')}")
ok &= inside and outside_same and pygame.image.tobytes(after, "RGB") == pygame.image.tobytes(normal, "RGB")

# 5. Colin walks into the house first: 5 frames (the first four wait about 0.29 s each), the game stands still meanwhile
w = biker.World()
door = door_with(w, 1)
table_before = [list(e) for e in w.traffic.table]
w.marker = door
w.park()
frames, passes = [], 0
while w.walk:
    if not frames or frames[-1] != w.walk[0]:
        frames.append(w.walk[0])
    w.tick(0)
    passes += 1
still = [list(e) for e in w.traffic.table] == table_before and w.bar is not None and w.inside is not None
print("walk: frames shown", frames, "over", passes, "passes (expect 4 x", biker.WALK_PASSES, "+ 1);  game paused and room begun:", still)
ok &= frames == [0, 1, 2, 3, 4] and passes == 4 * biker.WALK_PASSES + 1 and still

# 6. equipment shows on the HUD bike picture: the item pictures are ORed on, only in their own cells
import numpy as np   # noqa: E402
w = biker.World()
surf = pygame.Surface((256, 192))


def hud_pixels(items):
    w.items = items
    w.draw(surf)
    return pygame.surfarray.array3d(surf).copy()


base = hud_pixels(0)
for it in w.hud_items:
    pix = hud_pixels(it["flag"])
    diff = np.argwhere((pix != base).any(axis=2))
    inside_rect = all(it["col"] * 8 <= x < (it["col"] + it["w"]) * 8 and it["row"] * 8 <= y < (it["row"] + it["h"]) * 8 for x, y in diff)
    print(f"HUD picture for item flag {it['flag']:2d}: {len(diff):3d} pixels changed, all inside its {it['w']}x{it['h']} cells at ({it['col']},{it['row']}): {inside_rect}")
    ok &= len(diff) > 0 and inside_rect

# 7. the message scrolls up from the hidden bottom row into the MIDDLE row (y 168-175) and nothing is ever visible on the other bar rows
w = biker.World()
w.say(["You find the new tyres "])
rows = {"top row 20": (160, 168), "middle row 21": (168, 176), "hidden row 22": (176, 184)}


def bar_ink():
    w.draw(surf)
    arr = pygame.surfarray.array3d(surf)
    out = {}
    for name, (y0, y1) in rows.items():
        part = arr[32:224, y0:y1]
        out[name] = int((part != arr[40, 164]).any(axis=2).sum())     # differs from the blue background
    return out


first = bar_ink()
for _ in range(biker.SCROLL_PASSES // 2):
    w.tick(0)
mid = bar_ink()
for _ in range(biker.SCROLL_PASSES // 2 + 1):
    w.tick(0)
rest = bar_ink()
for _ in range(round(biker.PAUSE_SHORT * biker.PASS_HZ) + biker.SCROLL_PASSES // 2):
    w.tick(0)
leaving = bar_ink()
print("scroll: ink per bar row at the start", first, "| half-way in", mid, "| at rest", rest, "| half-way out", leaving)
only_middle = all(v["top row 20"] == 0 and v["hidden row 22"] == 0 for v in (first, mid, rest, leaving))
ok &= only_middle and first["middle row 21"] == 0 and 0 < mid["middle row 21"] < rest["middle row 21"] and 0 < leaving["middle row 21"] < rest["middle row 21"]

# 8. anchored on a real snapshot: work/biker_house_enter.z80 was taken mid-walk (PC $F95A, the delay between frames). The cells the
#    original drew Colin on hold the bytes of walking frame 2 (top row first) with the colours of the wall and hedge beneath, which is
#    what the port draws.
snap_path = "work/biker_house_enter.z80"
if os.path.exists(snap_path):
    from skoolkit.snapshot import Snapshot   # noqa: E402
    r = bytes(Snapshot.get(snap_path).ram(1))
    col, rowb = r[0xE51C - 0x4000], r[0xE51D - 0x4000]
    top = 24 - (rowb + 2)
    cells = [(col, top), (col + 1, top), (col, top + 1), (col + 1, top + 1)]

    def screen_cell(cx, cy):
        return bytes(r[0x4000 + (((cy * 8 + k) & 0xC0) << 5) + (((cy * 8 + k) & 7) << 8) + (((cy * 8 + k) & 0x38) << 2) + cx - 0x4000]
                     for k in range(8))
    snap_chars = [screen_cell(*c) for c in cells]
    snap_attrs = [r[0x5800 + cy * 32 + cx - 0x4000] for cx, cy in cells]
    px, py = r[0xE51A - 0x4000], r[0xE51B - 0x4000]
    w = biker.World()
    port_chars = [w.colin[32 * 1 + 8 * k:32 * 1 + 8 * k + 8] for k in range(4)]          # walking frame 2
    port_attrs = [w.cell_attr(px + (k & 1), py - 2 + (k >> 1)) for k in range(4)]
    same_chars = port_chars == snap_chars
    same_attrs = port_attrs == snap_attrs
    print(f"real mid-walk snapshot: frame-2 bytes equal {same_chars}, colours equal {same_attrs} "
          f"({[hex(a) for a in snap_attrs]}), parked frame pointer {r[0xE734 - 0x4000] | r[0xE735 - 0x4000] << 8:04X} (expect 76C8 = frame 8, facing left)")
    ok &= same_chars and same_attrs and (r[0xE734 - 0x4000] | r[0xE735 - 0x4000] << 8) == 0x76C8

# 9. the dark area (no headlamp): cells that scroll into view at map y > 80 and x <= 41 are blank, cells already on screen are not;
#    the headlamp shows everything; the enter/leave markers speak once; the bike still collides with the real map
w = biker.World()
w.place(60, 95)
w.prev_cam = w.camera()
w.dark_blank[:] = False
blank_seen = []
for step in range(45):                                 # ride west along y = 95: the left edge of the view reaches x = 40 at px = 48
    w.follow(biker.LEFT)
    w.px -= 1
    w.scroll_dark()
    cam = w.camera()
    blank_seen.append((cam[0], int(w.dark_blank.sum())))
first_blank = next((c for c, n in blank_seen if n), None)
cam = w.camera()
cells_expected = sum(1 for j in range(biker.VIEW_H) for i in range(biker.VIEW_W) if cam[1] + j > 80 and cam[0] + i <= 40)
print(f"dark area: first blank cell once the camera x reached {first_blank} (expect 40); at camera x {cam[0]}: "
      f"{int(w.dark_blank.sum())} blank cells of {cells_expected} in the region")
ok &= first_blank == 40 and int(w.dark_blank.sum()) == cells_expected
# cells already on screen when you cross in stay visible for a while: after ONE step west of x = 41 only the new left column is blank
w = biker.World()
w.place(48, 95)
w.cam = (41, 87)                                       # the bike is 7 tiles from the left edge of the view, so the next step west scrolls
w.prev_cam = w.camera()
w.dark_blank[:] = False
w.follow(biker.LEFT)
w.px -= 1
w.scroll_dark()
print("one step into the dark: blank cells =", int(w.dark_blank.sum()), "(expect", biker.VIEW_H, ": just the new left column)")
ok &= int(w.dark_blank.sum()) == biker.VIEW_H
# with the headlamp nothing is blank
w = biker.World()
w.items |= 1
w.place(20, 100)
w.prev_cam = w.camera()
for _ in range(10):
    w.follow(biker.LEFT)
    w.px -= 1
    w.scroll_dark()
print("with the headlamp, blank cells in the dark area:", int(w.dark_blank.sum()), "(expect 0)")
ok &= int(w.dark_blank.sum()) == 0
# the markers
w = biker.World()
ys, xs = (w.map == 203).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
said_in = w.bar and w.bar.lines == M["dark_in"] and w.dark_flag == 0
w.bar = None
w.hit_tile(int(xs[0]), int(ys[0]))
silent_again = w.bar is None
ys, xs = (w.map == 204).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
said_out = w.bar and w.bar.lines == M["dark_out"] and w.dark_flag == 255
print("enter marker speaks once:", bool(said_in and silent_again), "  leave marker speaks:", bool(said_out))
ok &= bool(said_in and silent_again and said_out)
w = biker.World()
w.items |= 1
ys, xs = (w.map == 203).nonzero()
w.hit_tile(int(xs[0]), int(ys[0]))
print("with the headlamp the markers stay silent:", w.bar is None and w.dark_flag == 255)
ok &= w.bar is None and w.dark_flag == 255
# the bike still collides with the real (invisible) map in the dark
w = biker.World()
ys, xs = ((w.map >= 1) & (w.map <= 19)).nonzero()
inside_dark = [(int(x), int(y)) for x, y in zip(xs, ys) if y > 80 and x <= 40][0]
print("a house tile in the dark area still blocks the bike:", w.hit_tile(*inside_dark))
ok &= bool(w.hit_tile(*inside_dark))

# 10. anchored on a real snapshot taken inside the dark area (work/biker_dark_area.z80, no headlamp, viewport x 33-50): every cell at map
#     x <= 40 whose real tile is not blank is blank on screen, and no cell at x >= 41 is darkened -- which is exactly fetch_blank
snap_path = "work/biker_dark_area.z80"
if os.path.exists(snap_path):
    from skoolkit.snapshot import Snapshot   # noqa: E402,F811
    r = bytes(Snapshot.get(snap_path).ram(1))
    vx, vy = r[0xE90B - 0x4000], r[0xE90C - 0x4000]
    pxs, pys = r[0xE51A - 0x4000], r[0xE51B - 0x4000]
    w = biker.World()
    w.items = 0

    def real_nonblank(x, y):
        t = int(w.map[y, x])
        if t in (0, 69):
            return False
        if 1 <= t <= 19:
            return True
        return any(w.tile_bytes(t))

    def screen_blank(cx, cy):
        return not any(r[0x4000 + (((cy * 8 + k) & 0xC0) << 5) + (((cy * 8 + k) & 7) << 8) + (((cy * 8 + k) & 0x38) << 2) + cx - 0x4000]
                       for k in range(8))
    bad, tested = 0, 0
    for cy in range(1, 19):
        for cx in range(1, 19):
            x, y = vx + cx - 1, vy + cy - 1
            if pxs <= x <= pxs + 1 and pys <= y <= pys + 1:        # the bike
                continue
            if not real_nonblank(x, y):
                continue
            tested += 1
            if screen_blank(cx, cy) != w.fetch_blank(x, y):
                bad += 1
    print(f"real dark-area snapshot: {tested} cells with a drawn tile, {bad} disagree with fetch_blank (expect 0)")
    ok &= bad == 0 and tested > 20

# 10. every visit drawn frame by frame, parked facing each way: the walk-in, the room and riding off again (with Martin aboard the bike is
#     drawn from the second set, which has no parked frames 8 and 9: $F80C uses the first set's)
screen = pygame.Surface((256, 192))
drawn, errors = 0, []
for flag in biker.ITEM_POINTS:
    for heading in (biker.LEFT, biker.RIGHT, biker.UP, biker.DOWN):
        w = biker.World()
        w.traffic.update = lambda: None
        door = door_with(w, flag)
        x, y = w.door_cell(door)
        w.place(x, y)
        w.heading, w.angle, w.speed, w.wait = heading, biker.FRAME[heading], 10, 0
        w.marker = door
        try:
            w.park()
            while w.walk or w.inside:
                w.tick(0)
                w.draw(screen)
            for _ in range(20):
                w.tick(1)
                w.draw(screen)
            drawn += 1
        except Exception as error:
            errors.append(f"{biker.ITEM_NAMES[flag]} facing {heading}: {error!r}")
print(f"every item's visit drawn, parked facing each way: {drawn} of {4 * len(biker.ITEM_POINTS)} without an error", errors[:3])
ok &= not errors
print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
