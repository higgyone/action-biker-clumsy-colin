"""Action Biker port, skeleton: scrolling map, player with 4-way movement, scrolling traffic.

Run from the repo root:  .venv/Scripts/python port/biker.py      (needs assets/ from tools/extract_assets.py)
The two loading screens and the Select Controls menu come first (1-5 picks Keyboard N M A Z Space, Kempston, Sinclair 6 7 9 8 0, Fuller, Cursor 5 8 7 6 Space;
the arrow keys and Space always work too); Esc quits. Options: --fixes, --fix NAME, --list-fixes, --no-intro, --controls NAME. The pass rate (PASS_HZ) is the original's measured speed (notes/03); the traffic follows the
original's movement rules (port/traffic.py).
"""
import json
import os
import time
import numpy as np
import pygame
from traffic import Traffic
from sound import Sound   # noqa: F401  (main() builds one)
import controls
import options

A = os.path.join(os.path.dirname(__file__), "..", "assets")
CAM_MAX = 128 - 18                 # the camera stops here (the move handlers compare it with 110)
VIEW_W, VIEW_H = 18, 18          # viewport in tiles: 18x18 chars at char (1,1) of the 32x24 screen ($DF61 clears it)
VIEW_X, VIEW_Y = 1, 1
SCALE = 4
PASS_HZ = 19.5                   # game passes per second, measured: a frame (two passes) takes about 102 ms (357,000 T-states at 3.5 MHz) in the original,
                                 # stopped or at full speed; nothing syncs it to the 50 Hz interrupt
FUEL_CANS = [(111, 19), (103, 51), (23, 76)]   # fixed fuel can spots ($E46D); they come back every 300 passes
SLOT_OF_FLAG = {32: 14, 4: 18, 1: 16, 2: 17, 8: 19, 16: 13, 64: 15}   # $5B07 flag -> house item slot
# The game's seed is the return address of its caller, so it is the same on every load. Twelve start values give exactly
# the layout in the level snapshot (they differ only by draws the placement throws away); any of them will do.
START_SEED = 0x1356
# The port plays the game as the original does. Anything that changes the game on purpose is a named *fix*, off by default: `python port/biker.py --fixes`
# turns them all on, `--fix NAME` one at a time, `--list-fixes` shows them. World(fixes=...) takes a collection of names.
FIXES = {
    "infinite_sleep": "SLEEP never goes down (crashes, oil and water cost nothing)",
    "infinite_fuel": "the fuel never runs out",
    "infinite_time": "eight o'clock never ends the day (the clock still runs)",
    "easy_parking": "the house stop fix: Space enters a house whenever a door is under the bike or just ahead of it, even when the bike has stopped "
                    "(the original needs Space on a pass where the moving bike's front touches the door); the bike then stands on the door's marker, so Colin "
                    "always walks up the path",
    "turn_assist": "turns onto side roads are forgiving: if the way you ask for is blocked but one or two tiles further along (or one tile to the side) it is "
                   "open, the bike carries on or nudges across and turns, so a turn pressed a little early or late still works",
    "quick_start": "no wait to get going: the bike moves on the pass a key is pressed from a standstill and speeds up twice as fast",
    "quick_turns": "the bike turns on the spot at any speed: a turn step never waits for the slow-speed delay between moves",
    "map_view": "press Tab to show the whole map with where you are (a blinking red dot), where you have been (the orange trail) and the part of the town on screen; the game waits while it is up",
    "breadcrumbs": "press B to show or hide a trail of dots along every tile the bike has ridden through this game, so you can see where you have been; "
                   "where you stopped to go into a house the crumb is bigger, with a white ring (on the Tab map too)",
    "item_markers": "press I to show or hide a marker above every house that still holds items (and the friend's mum)",
}
ITEM_POINTS = {1: 10, 2: 10, 4: 10, 8: 10, 16: 10, 32: 100, 64: 0}   # $FD63: byte 0 of each item record (Martin 100, mum 0)
ITEM_NAMES = {1: "Headlamp", 2: "New tyres", 4: "Snorkel", 8: "Periscope", 16: "Turbo DIY kit", 32: "Martin",
              64: "Friend's mum: tea"}   # the Turbo kit has no effect at all: nothing in the program reads bit 4
ITEM_INDEX = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5, 64: 6}   # flag -> record in the item table ($FB9C), also in messages.json
WALK_PASSES = round(0.29 * PASS_HZ)   # passes each walking frame stays up: $F860 waits 64000 loops (about 0.29 s) after frames 1-4
SCROLL_PASSES = round(0.40 * PASS_HZ)   # a line takes 0.40-0.42 s to scroll in or out ($E008 + $E01F measured in a simulator)
PAUSE_ITEM = 2.46                # seconds: the pause routine $FDC9 (64969) used before and after each line of an item message
CRASH_SECONDS = 0.0759            # seconds the crash routine $D95D (55645) holds the game up: two 27 ms beeps with a 7 ms flash after each, then SLEEP and score reprinted (measured)
# the crash routine $D95D (measured): beep 0-27 ms, flash routine 27-34 ms (it inverts the play area's ink and paper), second beep 34-62 ms,
# flash routine again 62-69 ms (inverts back), then SLEEP and the score. So the play area is inverted from about 31 ms to 65 ms.
FLASH_ON, FLASH_OFF = 0.031, 0.065
PAUSE_UNIT = 0.1486              # seconds: one call of the short pause $F12C (61740), 20000 loops (measured)
PAUSE_SHORT = 3 * PAUSE_UNIT     # three calls of it, as after a crisp packet or fuel can line
SKID_STEP = 0.0348               # seconds between the 16 redraws of the bike spinning on oil ($F139: 35 x 256 loops, measured)
REFILL_STEP = 0.0028             # seconds per step of the fuel gauge while a can refills the tank ($F0F3 calling $D9FA, measured)
DARK_X, DARK_Y = 40, 80          # the dark area: tiles fetched as the view scrolls are blank for map x <= 40 and y > 80 unless $5B07 bit 0 (headlamp).
                                 # $F0B4 tests the column number plus one against 41, so x <= 40 (checked by running the original's scroll routine and
                                 # against work/biker_dark_area.z80); the vehicle-background routine $F7B5 tests x <= 41 itself (not modelled)
MUM = 64                         # $5B07 bit 6: tea with the friend's mum ($FD45)
TEA_SECONDS = 0.838              # the tea routine $FD45: 600 clock passes with a delay after each, run after the mum's last pause, before the line goes (measured)
FUEL_MAX = 18                    # gauge steps in a full tank ($E28F/$E290 pair walks (4,4) -> (2,3))
UP, RIGHT, DOWN, LEFT = 3, 2, 1, 0   # heading = bits 7-6 of $E519
FRAME = {LEFT: 0, RIGHT: 4, DOWN: 6, UP: 2}   # player sprite frame per heading
# frames 0-7 are eight compass poses in this order, so the odd frames are the 45-degree turning poses
STEP = {LEFT: (-1, 0), RIGHT: (1, 0), DOWN: (0, 1), UP: (0, -1)}
# which way each move handler turns the sprite (+1 = $EDBA next frame, -1 = $EDDF previous frame) for the bike's current heading variable ($E538, $E5E5, $E689, $E736)
ROTATE = {RIGHT: {DOWN: -1, UP: 1, LEFT: 1}, UP: {RIGHT: -1, LEFT: 1, DOWN: 1}, DOWN: {LEFT: -1, RIGHT: 1, UP: 1}, LEFT: {UP: -1, RIGHT: 1, DOWN: 1}}


def load(name):
    with open(os.path.join(A, name), "rb") as f:
        return f.read()


def rgb(index, bright):
    level = 255 if bright else 205
    return (level if index & 2 else 0, level if index & 4 else 0, level if index & 1 else 0)


def char_surface(data, attr):
    """8x8 pygame surface from 8 bytes + a Spectrum attribute."""
    bright = bool(attr & 0x40)
    ink, paper = rgb(attr & 7, bright), rgb((attr >> 3) & 7, bright)
    s = pygame.Surface((8, 8))
    for y in range(8):
        for x in range(8):
            s.set_at((x, y), ink if data[y] & (0x80 >> x) else paper)
    return s


def sprite(chars, w, h, attr):
    s = pygame.Surface((w * 8, h * 8))
    for k in range(w * h):
        s.blit(char_surface(chars[8 * k:8 * k + 8], attr), ((k % w) * 8, (k // w) * 8))
    return s


class Bar:
    """The message bar: three blue rows (20-22) of which only the middle one shows text. $E008 prints a 24-character line on the
    hidden bottom row (blue ink on blue paper) and $E01F scrolls it up into the middle row in 8 pixel steps, pushing whatever was
    there off the top. So lines come one at a time; a message ends by scrolling the last line up and out ($E01F again).
    steps: ("in", line), ("pause", None), ("out", None), each with its length in passes."""

    def __init__(self, lines, lead=0.0, gap=PAUSE_SHORT, between=False, hold=False, tail=0.0, script=None):
        """`script` (instead of lines/lead/gap/between/tail) is a list of ("in", line), ("pause", seconds[, tag]) and ("out", None) steps."""
        if script is None:
            raw = [("pause", lead)] if lead else []
            for i, line in enumerate(lines):
                raw.append(("in", line))
                raw.append(("pause", gap))
                if between and i < len(lines) - 1:
                    raw.append(("out", None))
            if not hold:
                raw.append(("out", None))
                if tail:                                   # a pause after the last line has gone (the endings: 2.46 s, then the tune)
                    raw.append(("pause", tail))
        else:
            raw, lines = list(script), [step[1] for step in script if step[0] == "in"]
        self.lines, self.hold, self.t = list(lines), hold, 0
        self.steps, shown, start = [], None, 0
        for step in raw:
            kind, arg = step[0], step[1]
            n = SCROLL_PASSES if kind in ("in", "out") else max(1, round(arg * PASS_HZ))
            new = arg if kind == "in" else None if kind == "out" else shown
            self.steps.append((start, n, kind, shown, new, step[2] if len(step) > 2 else None))   # (first pass, length, kind, text before, text after, tag)
            shown, start = new, start + n
        self.total = start

    def at(self, tag):
        """Passes into the step carrying `tag` (see script), or None when the bar is not in it."""
        for start, n, kind, before, after, t in self.steps:
            if t == tag and start <= self.t < start + n:
                return self.t - start
        return None

    def passes_before(self, tag):
        """Pass on which the step carrying `tag` starts."""
        return next(start for start, n, kind, before, after, t in self.steps if t == tag)

    def frame(self):
        """[(text, y)] to draw now: y = 168 is rest on the middle row, 176 is the hidden bottom row, 160 is off the top."""
        t = self.t
        for start, n, kind, before, after, tag in self.steps:
            if start <= t < start + n:
                p = (t - start) / n
                if kind == "in":
                    return [(before, 168 - round(8 * p))] * (before is not None) + [(after, 176 - round(8 * p))]
                if kind == "out":
                    return [(before, 168 - round(8 * p))]
                return [(before, 168)] if before is not None else []
        last = self.steps[-1]
        return [(last[4], 168)] if last[4] is not None else []        # a held message keeps its last line


class World:
    def __init__(self, sound=None, fixes=()):
        self.base_map = np.frombuffer(load("map.bin"), dtype=np.uint8).reshape(128, 128).copy()
        self.map = self.base_map.copy()
        tiles, tattr = load("tiles.bin"), load("tile_attr.bin")
        bchars, battr = load("buildings.bin"), load("building_attr.bin")
        self.tattr, self.battr = tattr, battr
        self.tile_raw = tiles
        self.tile_img = {t: char_surface(tiles[8 * t:8 * t + 8], tattr[t]) for t in range(32, 256)}
        self.bchar = {(b, k): char_surface(bchars[288 * b + 8 * k:288 * b + 8 * k + 8], battr[36 * b + k])
                      for b in range(1, 20) for k in range(36)}
        self.map_clean = self.base_map.copy()
        self.pre_clean = self.render_map()
        player = load("player.bin")
        self.player_img = {f: sprite(player[32 * f:32 * f + 32], 2, 2, 0x47) for f in range(10)}
        veh = load("vehicles.bin")
        self.veh_chars = {(t, h): veh[192 * t + 48 * h:192 * t + 48 * h + 48] for t in range(3) for h in range(4)}
        meta = json.load(open(os.path.join(A, "meta.json")))
        start = json.load(open(os.path.join(A, "traffic.json")))
        # the 20 road users and their generator carry on from game to game, as in the original (the table is data, not reset)
        self.traffic = Traffic([[v["x"], v["y"], v["flags"]] for v in start], meta.get("traffic_seed", 253))
        self.veh_img = {}
        pw, p2 = load("player_water.bin"), load("player_set2.bin")
        self.water_img = {f: sprite(pw[32 * f:32 * f + 32], 2, 2, 0x28) for f in range(8)}
        self.set2_img = {f: sprite(p2[32 * f:32 * f + 32], 2, 2, 0x47) for f in range(8)}
        self.interior_data = json.load(open(os.path.join(A, "interior.json")))
        self.house_bits = {h["id"]: int.from_bytes(bytes.fromhex(h["bytes"]), "little") & 0x1FFF for h in json.load(open(os.path.join(A, "houses.json")))}
        self.house_colour = {h["id"]: h["colour"] for h in json.load(open(os.path.join(A, "houses.json")))}
        raw = load("hud.bin")
        self.hud = pygame.Surface((256, 192))
        self.hud_attr = raw[6144:]
        for cy in range(24):
            for cx in range(32):
                a = raw[6144 + cy * 32 + cx]
                bright = bool(a & 0x40)
                ink, paper = rgb(a & 7, bright), rgb((a >> 3) & 7, bright)
                for r in range(8):
                    y = cy * 8 + r
                    byte = raw[((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + cx]
                    for b in range(8):
                        self.hud.set_at((cx * 8 + b, y), ink if byte & (0x80 >> b) else paper)
        self.font = load("font.bin")
        self.hud_items = json.load(open(os.path.join(A, "hud_items.json")))   # item pictures ORed onto the HUD bike picture
        self.needle = json.load(open(os.path.join(A, "hud_needle.json")))      # the pixels of the speedometer needle for each speed counter ($DB3E)
        clock = json.load(open(os.path.join(A, "hud_clock.json")))             # the pixels of each clock hand in each of its 60 places ($DCFB)
        self.clock_hands = {k: [{tuple(p) for p in place} for place in clock[k]] for k in ("minute", "hour")}
        self.colin = load("colin_walk.bin")                                    # 5 frames of Colin walking into a house, 32 bytes each
        self.msgs = json.load(open(os.path.join(A, "messages.json")))   # every on-screen message, 24 characters per line
        self.high = 0
        self.dark_flag = 255            # $F005: 255 = outside the dark area, 0 = inside; only changes at the 203/204 markers without the headlamp
                                        # and, like the original, is not reset by a new game
        self.seed = START_SEED
        self.fixes = set(fixes)          # names from FIXES that are on; empty = the original game
        self.sound = sound               # a sound.Sound (or anything with play/play_seq/seconds); None = silent and no waiting for tunes
        self.new_game()

    def put_object(self, x, y, first):
        """Place a 2x2 object (ids first..first+3, laid out a b / c d) at map cell (x, y)."""
        for k in range(4):
            cx, cy = x + (k & 1), y + (k >> 1)
            self.map[cy, cx] = first + k
            self.pre.blit(self.tile_img[first + k], (cx * 8, cy * 8))

    def clear_object(self, x, y):
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            self.map[y + dy, x + dx] = 0
            self.pre.fill((0, 0, 0), ((x + dx) * 8, (y + dy) * 8, 8, 8))

    def rng(self):
        """$E292 (58002): seed = (seed + 1) * 75 mod 65537 - 1; returns the low byte. Only the start-up placement uses it,
        and the seed carries over from game to game within a session."""
        self.seed = ((self.seed + 1) * 75 % 65537 - 1) & 0xFFFF
        return self.seed & 0xFF

    def cell(self, idx):
        return int(self.map[idx >> 7, idx & 127]) if 0 <= idx < 16384 else 1

    def place_random(self, first, count):
        """$E239/$E0D1: `count` 2x2 objects. A random address 0x99xx-0xD7xx must hold an empty cell; then it is nudged
        (left one if the cell to the right is taken, up a row if the one below is) and all four cells must be empty."""
        done = 0
        while done < count:
            hi = (self.rng() >> 2) + 152
            if hi == 152:
                hi = 153
            idx = (hi << 8 | self.rng()) - 39000
            if self.cell(idx):
                continue
            idx += 1
            idx -= 1 if self.cell(idx) == 0 else 2
            idx += 128
            idx -= 128 if self.cell(idx) == 0 else 256
            if any(self.cell(idx + o) for o in (0, 1, 128, 129)):
                continue
            self.put_object(idx & 127, idx >> 7, first)
            done += 1

    def place_items(self):
        """$E0FD (57597): scatter the items over the 50 house doors. 12 distinct houses from the generator, in this order:
        passenger (house 242 when the first draw is below 170), special tyres bit 2, headlamp (houses 0-37 only), wheels,
        tyres bit 3, item 4, then six houses with item 6."""
        flags = [32, 4, 1, 2, 8, 16] + [64] * 6
        slots = []

        def pick(avoid=()):
            while True:
                a = self.rng()
                if a < 50 and a not in slots and a not in avoid:
                    return a
        if self.rng() < 170:
            slots.append(37)                   # house 242 is index 37
        while len(slots) < 12:
            slots.append(pick())
        while slots[1] == 37:                  # $E131: slot 1 may not be the passenger's house
            slots[1] = pick()
        while slots[2] >= 38:                  # $E150: the headlamp is in the first 38 houses
            slots[2] = pick()
        self.houses = {205 + h: f for h, f in zip(slots, flags)}

    def new_game(self):
        """$D858 start-up plus the reset at $DA97: everything back to the start, the high score stays."""
        self.map = self.map_clean.copy()
        self.pre = self.pre_clean.copy()
        self.place_items()
        self.place_random(190, 30)
        self.place_random(194, 20)
        for cx, cy in FUEL_CANS:               # the cans go in last ($E46D, from the reset at $DA97)
            self.put_object(cx, cy, 198)
        meta = json.load(open(os.path.join(A, "meta.json")))
        self.px, self.py = meta["player_start"]
        self.cam = (min(max(self.px - 8, 0), CAM_MAX), min(max(self.py - 8, 0), CAM_MAX))   # $E90B: starts 8 tiles left of and above the bike ($D858)
        self.heading = meta["heading"] >> 6
        self.angle = FRAME[self.heading]   # sprite frame currently shown (0-7)
        self.sleep = 50
        self.score = 0
        self.speed = 10                # $E517: 10 = stopped, counts down to 0 = full speed while a key is held
        self.wait = 10                 # $D8C8: passes to skip before the player is processed again (the start-up sets 10)
        self.last_keys = 0             # $E518: last direction keys, used to coast after release
        self.fuel = FUEL_MAX
        self.fuel_acc = 0              # $D9E2: fuel burn accumulator
        self.over = None
        self.inside = None
        self.over_timer = 0
        self.items = 0                 # $5B07: bit 0 headlamp, 1 special wheels, 2+3 water, 5 passenger, 4 and 6 unknown
        self.marker = 0                # $E516: house door tile touched this pass (205+), else 0
        self.in_water = False
        self.message = ""
        self.bar = None                # message bar: a Bar, or None
        self.walk = None               # Colin walking into the house: [frame 0-4, passes in this frame]
        self.visit = None              # what the room will show once Colin is inside: (door, message lines, passes)
        self.tea_done = None           # clock passes of the tea run so far (0-600) while a visit to the friend's mum is under way, else None
        self.traffic.map = self.map          # vehicles are not reset by a new game, only their view of the map
        self.trail = {}                # the breadcrumbs fix: every tile the bike has been on this game (in order of first visit)
        self.stops = set()             # the breadcrumbs fix: where the bike stood when it went into a house (drawn as a bigger, white-ringed crumb)
        self.show_trail = False
        self.show_map = False          # the map_view fix: the whole-town map is up and the game is paused
        self.show_items = False        # the item_markers fix: markers above houses that still hold items (toggled with I)
        self.take = None               # (door, item flags) to remove from the room when the visit ends
        self.phase = 0                 # the traffic moves on every other pass: once per frame, the player gets two passes
        self.flash_at = -1.0           # when the crash routine last started (time.monotonic()); its flash is drawn from that
        self.tick_pass, self.tick5, self.second, self.hour = 1, 1, 0, 40
        self.prev_cam = self.camera()
        self.traffic_cam = self.prev_cam   # the view at the last traffic pass, set every frame by tick()
        self.dark_blank = np.zeros((VIEW_H, VIEW_W), dtype=bool)   # viewport cells that were fetched blank (the dark area, no headlamp)
        self.over_limit = 0            # passes the ending lasts before a new game (set by end_game)
        self.tune_at, self.tune = 0, "end"   # the pass the end tune starts on, and which tune
        self.jingle = 0                # passes of the leaving-a-house jingle at the end of a visit (with sound)
        self.later = []                # (passes left, action) pairs: effects the original has in the middle of a blocking message
        self.skid_from = None          # sprite frame the bike had when it hit oil: it then spins through all eight, twice
        self.stall = 0.0               # passes still owed to a crash routine, which stops the game for 76 ms each time it runs
        self.intro = 0
        sound, self.sound = self.sound, None     # the start-up ($D858) ends by running one frame (two passes: traffic, clock) before the fanfare and the main loop
        for _ in range(2):
            self.tick(0)
        self.sound = sound
        if self.sound:                 # $E2BB: the fanfare plays before every game and the game waits until it is over
            self.intro = round(self.sound.seconds("start") * PASS_HZ)
            self.sound.play("start")   # $DBD4/$DBD5/$DBD2/$DBD3 after the reset

    def say(self, lines, lead=0.0, gap=PAUSE_SHORT, between=False, hold=False, tail=0.0, script=None, block=False):
        """Show 24-character lines one at a time in the middle row of the blue bar at the bottom of the screen ($E008, $E01F).
        block=True: the original's message routines do their scrolling and waiting themselves, so everything else stands still until the message is over."""
        self.bar = Bar(lines, lead, gap, between, hold, tail, script)
        if block:
            self.stall += self.bar.total

    def after(self, passes, action):
        """Do `action` after `passes` more passes (the original does some things in the middle of a blocking message routine)."""
        if passes <= 0:
            action()
        else:
            self.later.append([passes, action])

    def crisp_done(self):
        """What follows a pickup of a crisp packet ($EEF3 -> $E0D1): a new packet is placed at a random free spot (the same generator and placement as at the start of a game), +2."""
        self.place_random(190, 1)
        self.score += 2

    def lose_sleep(self):
        if "infinite_sleep" not in self.fixes:
            self.sleep = max(self.sleep - 1, 0)

    def crash(self):
        """$D95D: two beeps with the play-area flash after each, then SLEEP and the score reprinted. It runs on every pass of an overlap and
        blocks for 76 ms, so each such pass lasts about 127 ms instead of 51 ms: the game stands still for the rest of the crash."""
        self.snd("crash")
        self.flash_at = time.monotonic()
        self.stall += CRASH_SECONDS * PASS_HZ

    def snd(self, name):
        if self.sound:
            self.sound.play(name)

    def snd_seq(self, name, count, gap, lead=0.0):
        if self.sound:
            self.sound.play_seq(name, count, gap, lead)

    def end_game(self, message, bonus=0, lines=None, tune="end"):
        """$E3A3 (58275), shared by every ending: line 1 scrolls in, 2.46 s, line 2 scrolls in, 2.46 s, the bar scrolls empty, 2.46 s,
        then the end tune ($FE08, 7.3 s; the finish has its own tune of 28 notes, 7.2 s); then the play area is cleared, the fuel gauge refills at once and a new game starts (measured in a simulator)."""
        self.score += bonus
        self.high = max(self.high, self.score)
        self.over, self.message, self.over_timer = message, message, 0
        self.say(lines or [message], gap=PAUSE_ITEM, tail=PAUSE_ITEM)
        self.tune_at, self.tune = self.bar.total, tune
        self.over_limit = self.tune_at + (round(self.sound.seconds(tune) * PASS_HZ) if self.sound else 0)

    def interior(self, house_id):
        """The room shown when you park at a house ($F80C): the stored picture of the empty room ($F8CC swaps it in: walls in perspective,
        the door and two windows, bright white on black), a 12x12 floor patch in the house's colour, then each item present drawn over it,
        and Colin. Items are chars ORed in; only their ink is set (paper stays)."""
        data = self.interior_data
        bits = self.house_bits.get(house_id, 0)             # slots 0-12: fixed furniture
        for flag, slot in SLOT_OF_FLAG.items():             # slots 13-19: the items, wherever this game put them
            if self.houses.get(house_id, 0) & flag:
                bits |= 1 << slot
        vx, vy, vw, vh = data["viewport"]
        room, room_attr = bytes.fromhex(data["room"]), bytes.fromhex(data["room_attr"])
        pix = {(vx + k % vw, vy + k // vw): room[8 * k:8 * k + 8] for k in range(vw * vh)}
        attr = {(vx + k % vw, vy + k // vw): room_attr[k] for k in range(vw * vh)}
        fx, fy, fw, fh = data["floor"]
        for cy in range(fy, fy + fh):
            for cx in range(fx, fx + fw):
                attr[(cx, cy)] = (self.house_colour.get(house_id, 0) << 3) | 7
        slots = [data["items"][k] for k in range(20) if bits >> k & 1] + [data["colin"]]
        for it in slots:
            chars = bytes.fromhex(it["chars"])
            for j in range(it["w"] * it["h"]):
                c = (it["x"] + j % it["w"], it["y"] + j // it["w"])
                old = pix.get(c, bytes(8))
                pix[c] = bytes(a | b for a, b in zip(old, chars[8 * j:8 * j + 8]))
                attr[c] = (attr.get(c, 0) & 0xF8) | (it["ink"] & 7)
        surf = pygame.Surface((256, 192))
        for cy in range(vy, vy + vh):
            for cx in range(vx, vx + vw):
                surf.blit(char_surface(pix.get((cx, cy), bytes(8)), attr.get((cx, cy), 0)), (cx * 8, cy * 8))
        return surf

    def render_map(self):
        """Whole level as one 1024x1024 surface. Building ids mark 6x6 footprints; cell = 6*row + col from top-left."""
        surf = pygame.Surface((1024, 1024))
        m = self.map
        for y in range(128):
            for x in range(128):
                t = int(m[y, x])
                if 1 <= t <= 19:
                    # top-left of this footprint: walk up/left while the same id continues (footprints are 6x6)
                    oy = y
                    while oy > 0 and m[oy - 1, x] == t and y - oy < 5:
                        oy -= 1
                    ox = x
                    while ox > 0 and m[y, ox - 1] == t and x - ox < 5:
                        ox -= 1
                    surf.blit(self.bchar[(t, 6 * (y - oy) + (x - ox))], (x * 8, y * 8))
                elif t >= 32:
                    surf.blit(self.tile_img[t], (x * 8, y * 8))
        return surf

    def toggle_map(self):
        self.show_map = not self.show_map

    def draw_map(self, screen):
        """The map_view fix: the whole town on one screen (1.5 pixels a tile) with the part you can see boxed, the tiles you have been on in orange and you as a
        blinking red dot; houses that still hold items are marked as well when the item_markers fix is on."""
        screen.fill((0, 0, 0))
        scale = 192 / 128
        screen.blit(pygame.transform.smoothscale(self.pre, (192, 192)), (0, 0))
        cx, cy = self.camera()
        for x, y in self.trail:
            screen.fill((255, 140, 0), (int(x * scale), int(y * scale), 2, 2))
        for x, y in self.stops:                       # the houses visited: a white square with the orange in the middle
            screen.fill((255, 255, 255), (int(x * scale), int(y * scale) - 1, 4, 4))
            screen.fill((255, 140, 0), (int(x * scale) + 1, int(y * scale), 2, 2))
        if "item_markers" in self.fixes:
            for door, flags in self.houses.items():
                for cell in self.door_cells(door) if flags else ():
                    screen.fill((255, 0, 0) if flags & 32 else (255, 255, 0), (int(cell[0] * scale) - 1, int(cell[1] * scale) - 1, 4, 4))
        pygame.draw.rect(screen, (255, 255, 255), (int(cx * scale), int(cy * scale), int(VIEW_W * scale) + 1, int(VIEW_H * scale) + 1), 1)
        if int(time.monotonic() * 3) % 2 == 0:
            pygame.draw.circle(screen, (0, 0, 0), (int(self.px * scale) + 1, int(self.py * scale) + 1), 4)
            pygame.draw.circle(screen, (255, 0, 0), (int(self.px * scale) + 1, int(self.py * scale) + 1), 3)
        for i, line in enumerate(("MAP", "", "RED:you", "ORANGE:", " been", "WHITE:", " screen", "SQUARE:", " house", "", f"X {self.px}", f"Y {self.py}", "", "TAB:back")):
            self.draw_text(screen, line, 196, 8 + 8 * i, (255, 255, 255), (0, 0, 0))

    def toggle_trail(self):
        self.show_trail = not self.show_trail

    def draw_trail(self, screen, cx, cy):
        """The breadcrumbs fix: a dot at the middle of the bike for every tile it has been on, in the colour of a crumb, outlined to show on any ground."""
        for x, y in self.trail:
            sx, sy = (x + 1 - cx + VIEW_X) * 8, (y + 1 - cy + VIEW_Y) * 8
            if VIEW_X * 8 + 2 < sx < (VIEW_X + VIEW_W) * 8 - 2 and VIEW_Y * 8 + 2 < sy < (VIEW_Y + VIEW_H) * 8 - 2:
                if (x, y) in self.stops:            # a house visit: a bigger crumb with a white ring
                    pygame.draw.circle(screen, (0, 0, 0), (sx, sy), 5)
                    pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 4)
                    pygame.draw.circle(screen, (255, 140, 0), (sx, sy), 3)
                else:
                    pygame.draw.circle(screen, (0, 0, 0), (sx, sy), 3)
                    pygame.draw.circle(screen, (255, 140, 0), (sx, sy), 2)

    def toggle_markers(self):
        self.show_items = not self.show_items

    def door_cells(self, door):
        """The top cell of every door marker with this id (where the bike stops). Usually one, but two houses can share a door id and so
        a room: 232 is at (89, 68) and at (118, 108)."""
        cache = self.__dict__.setdefault("_door_cells", {})
        if door not in cache:
            ys, xs = (self.map == door).nonzero()
            cache[door] = [(int(x), int(y)) for x, y in zip(xs, ys) if y == 0 or self.map[y - 1, x] != door]
        return cache[door]

    def door_cell(self, door, near=None):
        """The door marker of this id nearest to `near` (the first on the map without it), or None."""
        cells = self.door_cells(door)
        if not cells:
            return None
        return min(cells, key=lambda c: abs(c[0] - near[0]) + abs(c[1] - near[1])) if near else cells[0]

    def draw_item_markers(self, screen, cx, cy):
        """The item_markers fix: a blinking diamond on the door cell of every house that still holds items (red: Martin, cyan: the friend's mum, yellow: the rest)."""
        if int(time.monotonic() * 2) % 2:
            return
        for door, flags in self.houses.items():
            for cell in self.door_cells(door) if flags else ():
                if not (cx <= cell[0] < cx + VIEW_W and cy <= cell[1] < cy + VIEW_H):
                    continue
                x, y = (cell[0] - cx + VIEW_X) * 8, (cell[1] - cy + VIEW_Y) * 8
                colour = (255, 0, 0) if flags & 32 else (0, 255, 255) if flags & MUM and not flags & ~MUM else (255, 255, 0)
                pygame.draw.polygon(screen, (0, 0, 0), [(x + 4, y - 1), (x + 9, y + 4), (x + 4, y + 9), (x - 1, y + 4)])
                pygame.draw.polygon(screen, colour, [(x + 4, y), (x + 8, y + 4), (x + 4, y + 8), (x, y + 4)])

    def blocked(self, x, y):
        """Would the tile at (x, y) stop the bike? The same rule as hit_tile($EE75), without any of its effects."""
        if not (0 <= x < 128 and 0 <= y < 128):
            return True
        t = int(self.map[y, x])
        if t == 65:
            return self.items & 12 != 12
        return not (t in (0, 69) or 190 <= t <= 204 or t >= 205)

    def can_go(self, x, y, direction):
        """Is the step from (x, y) in `direction` free for the 2x2 bike (its two leading-edge tiles)?"""
        dx, dy = STEP[direction]
        return not any(self.blocked(x + (2 if dx > 0 else -1 if dx < 0 else k), y + (2 if dy > 0 else -1 if dy < 0 else k)) for k in (0, 1))

    def hit_tile(self, x, y):
        """Port of the tile check at $EE75 (61045). Returns True if the tile blocks the bike.
        Passable: 0 (road), 69, pickups 190-201, markers 203/204 and 205+. Everything else (buildings, grass,
        fences, water 65, ...) blocks. Only the top-left tile of a pickup acts: 190 crisps, 194 oil, 198 fuel."""
        if not (0 <= x < 128 and 0 <= y < 128):
            return True
        t = int(self.map[y, x])
        if t >= 205:                         # house door marker: remember it, the trigger key enters the house
            self.marker = t
        if t == 65:                          # water: only with both items 2 and 3 ($5B07 bits 2 and 3), else it blocks
            if self.items & 12 == 12:
                self.in_water = True
                return False
            if not self.items & 4:           # without item 2 the water also costs SLEEP ($EF9F); with only item 2 it just blocks
                self.lose_sleep()
                self.crash()                          # $EF9C calls the crash routine $D95D
            return True
        if t == 190:                         # packet of KP Skips: +2 score, object removed ($EECA)
            self.clear_object(x, y)
            self.snd("crisp")
            if self.dark_flag == 0:          # the message only appears inside the dark area ($F005 = 0), where you cannot see the packet; then a new packet
                self.say(self.msgs["crisps"], block=True)           # is put down at random and the score goes up ($EEF3: placement $E0D1, +2)
                self.after(self.bar.total, self.crisp_done)
            else:
                self.crisp_done()
        elif t == 194 and self.speed == 0 and not self.items & 2:   # oil, only at full speed and without special wheels ($F0F9)
            a, b = self.msgs["oil"]          # line 1, the bike spins 16 redraws, line 1 goes, line 2, SLEEP - 1, a pause, line 2 goes ($F0F9-$F11A)
            self.say([a, b], block=True, script=[("in", a), ("pause", 16 * SKID_STEP, "skid"), ("out", None), ("in", b), ("pause", PAUSE_SHORT), ("out", None)])
            self.skid_from = self.angle
            self.after(self.bar.steps[4][0], self.lose_sleep)
            self.snd_seq("tick", 16, SKID_STEP, self.bar.steps[1][0] / PASS_HZ)   # every redraw of the bike clicks
        elif t == 198:                       # fuel can: the message, the gauge refills a click at a time, a pause, off ($F0D7)
            missing = FUEL_MAX - self.fuel
            self.fuel = FUEL_MAX
            self.clear_object(x, y)
            self.say(self.msgs["fuel"], gap=PAUSE_SHORT + missing * REFILL_STEP, block=True)
            self.snd_seq("step", missing, REFILL_STEP, SCROLL_PASSES / PASS_HZ)
        elif t == 203 and not self.items & 1 and self.dark_flag:          # $F006: going in without the headlamp, announced once
            self.dark_flag = 0
            a, b = self.msgs["dark_in"]
            self.say([a, b], block=True, script=[("in", a), ("pause", PAUSE_SHORT), ("out", None), ("in", b), ("pause", 2 * PAUSE_UNIT), ("out", None)])
        elif t == 204 and not self.items & 1 and self.dark_flag != 255:   # $F070: coming out again
            self.dark_flag = 255
            self.say(self.msgs["dark_out"], gap=PAUSE_UNIT, block=True)
        return not (t in (0, 69) or 190 <= t <= 204 or t >= 205)

    def footprint_free(self, x, y):
        return not any(self.blocked(x + i, y + j) for i in (0, 1) for j in (0, 1))

    def assist_carry_on(self, direction):
        """turn_assist: `direction` was pressed a tile or two early. If keeping on the way the bike faces for one or two tiles reaches a place where
        `direction` is open, return the direction to carry on in (else None)."""
        if direction == self.heading or self.angle != FRAME[self.heading] or self.can_go(self.px, self.py, direction):
            return None
        hx, hy = STEP[self.heading]
        for k in (1, 2):
            x, y = self.px + k * hx, self.py + k * hy
            if not all(self.can_go(self.px + i * hx, self.py + i * hy, self.heading) for i in range(k)):
                return None
            if self.can_go(x, y, direction):
                return self.heading
        return None

    def assist_nudge(self, direction):
        """turn_assist: `direction` is blocked by a tile because the bike is a tile off the side road. If one tile to either side is open, return that direction."""
        for side in (RIGHT, LEFT) if direction in (UP, DOWN) else (DOWN, UP):
            sx, sy = STEP[side]
            x, y = self.px + sx, self.py + sy
            if self.footprint_free(x, y) and self.can_go(x, y, direction):
                return side
        return None

    def move(self, direction):
        if self.angle != FRAME[direction]:     # a bike turns first (in 45-degree steps), then moves
            if "turn_assist" in self.fixes:
                carry = self.assist_carry_on(direction)
                if carry is not None:          # a turn asked for early: carry on to the junction first
                    return self.move(carry)
            diff = (FRAME[direction] - self.angle) % 8
            if self.heading == direction:          # a turn in progress ($E519 bit 5) back towards the way it came from: the handler snaps to that frame
                self.angle = FRAME[direction]
            else:                                  # which way round is the handler's choice, by the heading variable, not always the short way ($E538 etc.)
                self.angle = (self.angle + ROTATE[direction][self.heading]) % 8
            for d, f in FRAME.items():             # $E519 bits 7-6 follow the sprite frame: every time the turn passes a straight-on frame the heading is that way
                if f == self.angle:
                    self.heading = d
            return
        if "turn_assist" in self.fixes and not self.can_go(self.px, self.py, direction):
            side = self.assist_nudge(direction)
            if side is not None:               # a tile off the side road: slide across (the view follows as for any step) and turn in next
                sx, sy = STEP[side]
                self.follow(side)
                self.px += sx
                self.py += sy
                return
        self.step(direction)

    def step(self, direction):
        """The handler's move once the bike faces `direction`: test the two leading-edge tiles, then move the bike or scroll the view."""
        dx, dy = STEP[direction]
        # the two tiles on the leading edge of the 2x2 sprite
        edge = [(self.px + (2 if dx > 0 else -1 if dx < 0 else k), self.py + (2 if dy > 0 else -1 if dy < 0 else j))
                for k, j in ((0, 0), (1, 1))]
        self.in_water = False
        if not any(self.hit_tile(*e) for e in edge):   # first blocking tile ends the test, as in the original
            self.follow(direction)
            self.px += dx
            self.py += dy

    def follow_to(self, x, y):
        """Move the bike to (x, y) a tile at a time, the view following as it does for any move (the easy_parking fix's last nudge)."""
        while (self.px, self.py) != (x, y):
            d = RIGHT if x > self.px else LEFT if x < self.px else DOWN if y > self.py else UP
            self.follow(d)
            dx, dy = STEP[d]
            self.px += dx
            self.py += dy
            if "breadcrumbs" in self.fixes or "map_view" in self.fixes:   # the trail goes along the nudge too, with no gap to the door
                self.trail.setdefault((self.px, self.py), len(self.trail))

    def place(self, x, y):
        """Put the bike at (x, y) with the view as a new game would have it (8 tiles left of and above the bike, kept inside the map)."""
        self.px, self.py = x, y
        self.cam = (min(max(x - 8, 0), CAM_MAX), min(max(y - 8, 0), CAM_MAX))
        self.prev_cam = self.cam

    def follow(self, direction):
        """How the camera follows the bike ($E538, $E5E5, $E689, $E736): each handler either moves the bike on the screen or scrolls the view
        one tile instead. The bike's screen position has a dead zone, kept by the counters $E51C (column) and $E51D: moving right the view scrolls
        once the bike is 8 tiles or more from the left edge of the view, moving left once it is 7 or fewer; moving down at 8 or more tiles below
        the top, moving up at 6 or fewer (so after turning round the bike first travels a tile or two across the screen). Never beyond the map:
        the view stops at 0 and at 128 - 18 = 110 and the bike then moves on screen instead."""
        cx, cy = self.cam
        ox, oy = self.px - cx, self.py - cy
        if direction == RIGHT and cx < CAM_MAX and ox >= 8:
            self.cam = (cx + 1, cy)
        elif direction == LEFT and cx > 0 and ox <= 7:
            self.cam = (cx - 1, cy)
        elif direction == DOWN and cy < CAM_MAX and oy >= 8:
            self.cam = (cx, cy + 1)
        elif direction == UP and cy > 0 and oy <= 6:
            self.cam = (cx, cy - 1)

    def key_direction(self, keys):
        """The direction the handler dispatcher picks for these keys: bits 0 left, 1 right, 2 up, 3 down tested in the order 0, 2, 1, 3 ($E5A6)."""
        for bit, d in ((0, LEFT), (2, UP), (1, RIGHT), (3, DOWN)):
            if keys & (1 << bit):
                return d

    def dispatch(self, keys):
        """$E5A6 (58660): one handler call."""
        d = self.key_direction(keys)
        if d is not None:
            self.move(d)

    def door_near(self):
        """The easy_parking fix (not in the original): a door marker under the bike or just ahead of it counts, even when the bike has
        stopped. The original only sees a marker on a pass where the bike's leading edge tests it while moving."""
        dx, dy = STEP[self.heading]
        cells = [(self.px + i, self.py + j) for i in (0, 1) for j in (0, 1)]
        cells += [(self.px + (2 if dx > 0 else -1 if dx < 0 else k), self.py + (2 if dy > 0 else -1 if dy < 0 else k))
                  for k in (0, 1)]
        for x, y in cells:
            if 0 <= x < 128 and 0 <= y < 128 and self.map[y, x] >= 205:
                return int(self.map[y, x])
        return 0

    def park(self):
        """Trigger key on a house door ($F80C): stop dead and visit the house. Each item in the room is announced ($FD63): its
        points go to the score (10 each, Martin 100, the mum 0) and it is ORed into $5B07; the room then loses it (the mum stays).
        The friend's mum also means tea ($FD45). Every visit adds 3."""
        self.speed = 10
        door = self.marker
        if self.heading == RIGHT and self.angle == FRAME[RIGHT]:   # $F81A: facing right it calls the move-right handler ($E538) first, so the bike
            self.step(RIGHT)                           # parks a tile further on (or the view scrolls) and Colin walks in from there
        self.marker = door
        cell = self.door_cell(door, near=(self.px, self.py)) if "easy_parking" in self.fixes else None   # this door, not another with its id
        if cell and (self.px, self.py) != cell and self.footprint_free(*cell):
            self.follow_to(*cell)                      # easy parking: the bike stands on the door marker, so Colin walks up the path to the door
        if "breadcrumbs" in self.fixes or "map_view" in self.fixes:
            self.stops.add((self.px, self.py))
        here = self.houses.get(self.marker, 0)
        found = [ITEM_NAMES[f] for f in ITEM_POINTS if here & f]
        self.score += 3 + sum(pts for f, pts in ITEM_POINTS.items() if here & f)
        self.message = ", ".join(found) if found else "No items in this house"
        lines = [ln for f in ITEM_POINTS if here & f for ln in self.msgs["items"][ITEM_INDEX[f]]] or list(self.msgs["no_items"])
        self.items |= here
        self.take = (self.marker, here & ~MUM)         # removed from the room when the visit ends
        # an item message: a pause, line 1 scrolls in, a pause, line 2 scrolls in, a pause, then it scrolls out ($FD63); "No items" has
        # one line and one pause ($F8BE). The room stays up for the whole message. The friend's mum's message is followed by the tea
        # ($FD45) before its line scrolls out: 0.84 s in which 600 passes of the clock go by, the hands whirling on the HUD.
        if here & MUM:
            script = [("pause", PAUSE_ITEM)] + [s for ln in lines for s in (("in", ln), ("pause", PAUSE_ITEM))] + [("pause", TEA_SECONDS, "tea"), ("out", None)]
            self.visit = (self.marker, Bar(lines, script=script))
            self.tea_done = 0
        else:
            self.visit = (self.marker, Bar(lines, lead=PAUSE_ITEM if found else 0.0, gap=PAUSE_ITEM))
        self.walk = [0, 0]                             # $F860 first shows Colin walking in, then the room is swapped in ($F7C0)

    def begin_room(self):
        door, bar = self.visit
        self.bar = bar                                 # two 24-character lines per item, as the item table holds them ($FB9C)
        self.jingle = round(self.sound.seconds("house") * PASS_HZ) if self.sound else 0   # $F863 plays it when you leave
        self.inside = (door, bar.total + self.jingle)

    def tick(self, keys, trigger=False):
        if self.show_map:                              # the map_view fix: the game waits while the map is up
            return
        self.high = max(self.high, self.score)         # $E0B1: the high score follows the score
        """One game pass ($D899 body). The player is processed only when `wait` has run out; after that it waits
        `speed` passes, so a tile step takes speed+1 passes: slow when starting, one per pass at full speed."""
        if self.bar:
            self.bar.t += 1
            if not self.bar.hold and self.bar.t >= self.bar.total:
                self.bar = None
        for item in self.later:                        # effects waiting in the middle of a message
            item[0] -= 1
        for item in [i for i in self.later if i[0] <= 0]:
            self.later.remove(item)
            item[1]()
        if self.stall >= 1:                            # a message routine or the crash routine is still running
            self.stall -= 1
            return
        if self.intro:                                 # waiting for the fanfare
            self.intro -= 1
            return
        if self.walk:                                  # frames 1-4 each wait about 0.29 s, frame 5 goes straight to the room
            self.walk[1] += 1
            if self.walk[0] == 4 or self.walk[1] >= WALK_PASSES:
                self.walk[1] = 0
                self.walk[0] += 1
                if self.walk[0] >= 5:
                    self.walk = None
                    self.begin_room()
            return
        if self.inside:
            house, left = self.inside
            if self.tea_done is not None and self.bar:    # the tea: the clock catches up with the share of 600 passes due by now
                t = self.bar.at("tea")
                if t is not None:
                    self.tea(round(600 * (t + 1) / max(1, round(TEA_SECONDS * PASS_HZ))))
                elif self.bar.t > self.bar.passes_before("tea"):
                    self.tea()
            if self.jingle and left == self.jingle:     # the message is over: the jingle plays, then the room closes
                self.snd("house")
            self.inside = (house, left - 1) if left > 1 else None
            if self.inside is None and self.take:       # the room closes: what was taken is gone for good
                door, flags = self.take
                if flags and door in self.houses:   # a door with nothing in it has no entry
                    self.houses[door] &= ~flags
                self.take = None
            return
        if self.over:
            self.over_timer += 1
            if self.over_timer == self.tune_at:    # the messages are over: the end tune plays (the game stands still for it)
                self.snd(self.tune)
            if self.over_timer > self.over_limit:  # then the play area is cleared, the gauge refills at once and a new game starts
                self.new_game()
            return
        self.snd("tick")                              # $E82F: a click every time the bike is drawn, i.e. every pass
        if self.phase == 0:                        # $D899 calls the traffic update ($F1CC) once, then runs two player passes
            self.traffic.update()
            self.vehicle_trails()
            self.traffic_cam = self.camera()      # the view the vehicles were drawn in (a scroll later in the frame shifts them with the screen)
        self.phase ^= 1
        if keys & 15 and self.wait:
            if "quick_start" in self.fixes and self.speed == 10:                    # from a standstill there is nothing to wait for
                self.wait = 0
            elif "quick_turns" in self.fixes and self.angle != FRAME[self.key_direction(keys)]:   # a turn step does not wait for the slow-speed delay
                self.wait = 0
        moved = not self.wait                      # $D89E-$D8A9: the player is moved on a pass where the wait ($D8C8) has run out
        if self.wait:
            self.wait -= 1
        elif keys & 15:                            # $E4E8: key held, accelerate and move
            self.speed = max(self.speed - (2 if "quick_start" in self.fixes else 1), 0)
            self.last_keys = keys & 15
            self.dispatch(self.last_keys)
        elif self.speed != 10:                     # key released: slow down but keep coasting the same way
            self.speed += 1
            self.dispatch(self.last_keys)
        # $D8AC: straight after the move ($E4E8), a door marker the move touched ($E516, cleared at the end of every pass) and the trigger key enter the house
        if trigger and not self.marker and "easy_parking" in self.fixes:
            self.marker = self.door_near()
        if self.marker and trigger:
            self.park()
        if "breadcrumbs" in self.fixes or "map_view" in self.fixes:
            self.trail.setdefault((self.px, self.py), len(self.trail))
        self.scroll_dark()
        if self.traffic.hits(self.px, self.py):    # $D8F9: overlapping a vehicle is a crash: SLEEP -1 ($D95D), beep, flash
            self.crash()                              # two beeps and a flash ($D95D) on every pass of an overlap
            self.lose_sleep()
        if self.speed != 10:                       # $DA03: fuel burns with speed, none at a standstill
            self.fuel_acc += (10 - self.speed) >> 1
            if self.fuel_acc > 255:
                self.fuel_acc &= 255
                if "infinite_fuel" not in self.fixes:
                    self.fuel -= 1
                self.snd("step")
        if moved:                                  # $D8C0: the wait for the next move is the speed counter, read after a parking set it to 10
            self.wait = self.speed
        self.clock_pass()
        self.marker = 0                            # $D8F0: the marker only counts on the pass that touched it
        if self.items & 32 and (self.px, self.py) == (105, 27):
            self.end_game("You're here just in time", 50, self.msgs["finish"], "win")   # then WELL DONE, COLIN: the same routine ($E452 -> $E3A3)
        elif self.sleep == 0:
            self.end_game("You've woken yourself up", 0, self.msgs["ending"][2:4])
        elif self.hour == 40 and self.second == 0 and "infinite_time" not in self.fixes:
            self.end_game("It's eight o'clock", 0, self.msgs["ending"][0:2])
        elif self.fuel <= 0:
            self.end_game("You've run out of fuel", 0, self.msgs["ending"][4:6])

    def clock_pass(self):
        """One pass of the clock ($DC04, 56324): a tick every 5 passes; the hour hand every 12 ticks; when the seconds counter
        wraps at 60 (every 300 passes) SLEEP +5 (max 50) and the fuel cans are put back."""
        self.tick_pass -= 1
        if self.tick_pass == 0:
            self.tick_pass = 5
            self.tick5 -= 1
            if self.tick5 == 0:
                self.tick5 = 12
                self.hour = (self.hour + 1) % 60
            self.second += 1
            if self.second == 60:
                self.second = 0
                for cx, cy in FUEL_CANS:
                    self.put_object(cx, cy, 198)
                self.sleep = min(self.sleep + 5, 50)

    def tea(self, upto=600):
        """The friend's mum ($FD45): the clock routine runs 600 times (6 x 100), so 600 passes of game time go by in 0.84 s: the
        seconds counter wraps twice (SLEEP +10, cans back), the hour hand moves 10 places. No fuel is used and the end-of-day
        test is not made in here, only by the main loop afterwards. upto: run the clock until this many of the 600 have gone by
        (the visit calls it every pass of the tea step, so the hands whirl on the HUD as they do in the original)."""
        while self.tea_done is not None and self.tea_done < min(upto, 600):
            self.clock_pass()
            self.tea_done += 1
        if self.tea_done is not None and self.tea_done >= 600:
            self.tea_done = None

    def cell_attr(self, x, y):
        """Spectrum attribute of the map cell (x, y) as render_map draws it: the colour the walking figure inherits."""
        t = int(self.map[y, x])
        if 1 <= t <= 19:
            oy = y
            while oy > 0 and self.map[oy - 1, x] == t and y - oy < 5:
                oy -= 1
            ox = x
            while ox > 0 and self.map[y, ox - 1] == t and x - ox < 5:
                ox -= 1
            return self.battr[36 * t + 6 * (y - oy) + (x - ox)]
        return self.tattr[t]

    def tile_bytes(self, t):
        return self.tile_raw[8 * t:8 * t + 8]

    def fetch_blank(self, x, y):
        """$F0B4 / $F7B5: a tile fetched for drawing comes back as the blank tile 205 in the dark area unless the headlamp is on."""
        return not self.items & 1 and y > DARK_Y and x <= DARK_X

    # the two cells just behind a vehicle, by heading (0 left, 1 down, 2 right, 3 up): the strip its drawing routine restores from the map every frame
    # ($F551 left, $F677 down, $F5D0 right, $F625 up, each calling the cell restore $F595)
    TRAIL = {0: ((3, 0), (3, 1)), 1: ((0, -1), (1, -1)), 2: ((-1, 0), (-1, 1)), 3: ((0, 2), (1, 2))}

    def vehicle_trails(self):
        """Every frame each vehicle on screen is drawn and then the two cells it has just left are restored from the map ($F595 asks $F6D3,
        which asks $F7B5, for the tile). In the dark area without the headlamp that tile is blank, and with the headlamp it is the real one,
        so a vehicle blanks the cells it passes over (x <= 41 here: $F7B5 tests the map x itself, the scroll fetch tests x + 1)."""
        cx, cy = self.prev_cam
        for x, y, f in self.traffic.table:
            for dx, dy in self.TRAIL[(f >> 6) & 3]:
                i, j = x + dx - cx, y + dy - cy
                if 0 <= i < VIEW_W and 0 <= j < VIEW_H:
                    self.dark_blank[j, i] = not self.items & 1 and y + dy > DARK_Y and x + dx <= DARK_X + 1

    def scroll_dark(self):
        """The original scrolls the screen and fetches only the newly exposed row or column ($E90D), so cells that were already on
        screen keep what they showed until they scroll off. Track which viewport cells were fetched blank."""
        cam = self.camera()
        dx, dy = cam[0] - self.prev_cam[0], cam[1] - self.prev_cam[1]
        if (dx, dy) == (0, 0):
            return
        old = self.dark_blank
        new = np.zeros_like(old)
        for j in range(VIEW_H):
            for i in range(VIEW_W):
                oi, oj = i + dx, j + dy
                if 0 <= oi < VIEW_W and 0 <= oj < VIEW_H:
                    new[j, i] = old[oj, oi]
                else:
                    new[j, i] = self.fetch_blank(cam[0] + i, cam[1] + j)
        self.dark_blank, self.prev_cam = new, cam

    def camera(self):
        return self.cam

    def draw_text(self, screen, text, x, y, ink, paper):
        """Print with the ROM font ($3D00, the game's own text routine at $DEFE)."""
        for i, ch in enumerate(text):
            code = ord(ch) - 32
            if 0 <= code < 96:
                glyph = self.font[8 * code:8 * code + 8]
                for row in range(8):
                    for bit in range(8):
                        screen.set_at((x + 8 * i + bit, y + row), ink if glyph[row] & (0x80 >> bit) else paper)

    def field_colours(self, cx, cy):
        a = self.hud_attr[cy * 32 + cx]
        bright = bool(a & 0x40)
        return rgb(a & 7, bright), rgb((a >> 3) & 7, bright)

    def draw_paused(self, screen):
        """The port's pause (not in the original): a box over the middle of the play area, in the ROM font."""
        white, blue, yellow = rgb(7, True), rgb(1, False), rgb(6, True)
        for row, (text, ink) in enumerate((("                ", white), ("     PAUSED     ", white), ("                ", white),
                                           (" P or ESC: play ", yellow), ("     Q: quit    ", yellow), ("                ", white))):
            self.draw_text(screen, text, (VIEW_X + 1) * 8, (VIEW_Y + 6 + row) * 8, ink, blue)

    def draw_hud(self, screen):
        """Live HUD parts over the static panel (assets/hud.bin)."""
        ink, paper = self.field_colours(26, 5)
        self.draw_text(screen, f"{self.high % 10000:04d}", 208, 44, ink, paper)      # HIGH   $44BA
        self.draw_text(screen, f"{self.score % 10000:04d}", 208, 60, ink, paper)     # SCORE  $44FA
        self.draw_text(screen, f"{self.sleep:02d}", 208, 76, ink, paper)             # SLEEP  $4C3A
        for it in self.hud_items:                    # found equipment is drawn onto the picture of the bike (ORed, black ink)
            if self.items & it["flag"]:
                chars = bytes.fromhex(it["chars"])
                for j in range(it["w"] * it["h"]):
                    cx, cy = it["col"] + j % it["w"], it["row"] + j // it["w"]
                    ink, _paper = self.field_colours(cx, cy)
                    for r in range(8):
                        for bit in range(8):
                            if chars[8 * j + r] & (0x80 >> bit):
                                screen.set_at((cx * 8 + bit, cy * 8 + r), ink)
        if self.bar:
            ink, paper = self.field_colours(4, 22)
            screen.set_clip(pygame.Rect(32, 168, 192, 8))          # the middle row: row 22 is blue on blue and row 20 is never used
            for text, y in self.bar.frame():
                self.draw_text(screen, text.ljust(24), 32, y, ink, paper)
            screen.set_clip(None)
        # speedometer: the original's needle for each speed counter, exactly as its line routine ($DB3E) draws it (made by tools/extract_assets.py)
        needle = self.needle[str(self.speed)]
        for x, y in needle["set"]:
            screen.set_at((x, y), self.field_colours(x >> 3, y >> 3)[0])
        for x, y in needle["clear"]:                 # a panel pixel the XOR turns off
            screen.set_at((x, y), self.field_colours(x >> 3, y >> 3)[1])
        # clock face at chars (1..3, 20..22): minute hand = $DBD2 seconds counter, hour hand = $DBD3 (40 = eight o'clock), each XORed onto
        # the face as the original's line routine draws it (made by tools/extract_assets.py), so where the two hands overlap the face shows through
        for x, y in self.clock_hands["minute"][self.second] ^ self.clock_hands["hour"][self.hour]:
            ink, paper = self.field_colours(x >> 3, y >> 3)
            screen.set_at((x, y), paper if tuple(screen.get_at((x, y)))[:3] == ink else ink)
        # fuel gauge: every step used XORs one more line over the FUEL box ($DA67), and the lines stay, so the box is inverted from the
        # top (y 163) down to the level: full shows nothing, empty has 18 lines inverted (y 163..180)
        for y in range(163, 163 + FUEL_MAX - max(self.fuel, 0)):
            for x in range(228, 246):
                screen.set_at((x, y), tuple(255 - c for c in screen.get_at((x, y))[:3]))

    def draw(self, screen):
        if "map_view" in self.fixes and self.show_map:
            self.draw_map(screen)
            return
        if self.inside:                      # $F80C redraws only the play area, so the HUD and the message bar stay
            screen.blit(self.hud, (0, 0))
            room = pygame.Rect(VIEW_X * 8, VIEW_Y * 8, VIEW_W * 8, VIEW_H * 8)
            screen.blit(self.interior(self.inside[0]), room.topleft, room)
            self.draw_hud(screen)
            return
        screen.blit(self.hud, (0, 0))
        cx, cy = self.camera()
        screen.blit(self.pre, (VIEW_X * 8, VIEW_Y * 8), (cx * 8, cy * 8, VIEW_W * 8, VIEW_H * 8))
        clip = pygame.Rect(VIEW_X * 8, VIEW_Y * 8, VIEW_W * 8, VIEW_H * 8)
        screen.set_clip(clip)
        for j in range(VIEW_H):                       # the dark area without the headlamp: blank tile 205 (black)
            for i in range(VIEW_W):
                if self.dark_blank[j, i]:
                    screen.fill((0, 0, 0), ((VIEW_X + i) * 8, (VIEW_Y + j) * 8, 8, 8))
        if "breadcrumbs" in self.fixes and self.show_trail:
            self.draw_trail(screen, cx, cy)
        for x, y, f in self.traffic.table:
            key = ((f >> 4) & 3, (f >> 6) & 3, f & 7)
            if key not in self.veh_img:          # drawn in bright ink on black, as on the screen ($45, $42, $43 seen)
                chars = self.veh_chars[key[:2]]
                if f & 0x40:                     # up or down: 2x2 cells from the x tile, using the last two of each row's three graphics ($F625, $F677)
                    self.veh_img[key] = sprite(chars[8:24] + chars[32:48], 2, 2, 0x40 | key[2])
                else:                            # left or right: 3x2 ($F551, $F5D0)
                    self.veh_img[key] = sprite(chars, 3, 2, 0x40 | key[2])
            # The original draws the vehicles once a frame ($F42F) and the scroll then moves the screen with them; the edge it scrolls in comes
            # from the map, without vehicles. So only the cells that were in the view at the traffic pass as well as now show a vehicle.
            tx, ty = self.traffic_cam
            w, h = (2 if f & 0x40 else 3), 2
            for j in range(h):
                for i in range(w):
                    if 0 <= x + i - tx < VIEW_W and 0 <= y + j - ty < VIEW_H:
                        screen.blit(self.veh_img[key], ((x + i - cx + VIEW_X) * 8, (y + j - cy + VIEW_Y) * 8), (i * 8, j * 8, 8, 8))
        img = self.water_img if self.in_water else self.set2_img if self.items & 32 else self.player_img
        angle = self.angle
        spin = self.bar.at("skid") if self.bar else None
        if spin is not None and self.skid_from is not None:   # the oil: $F139 turns the bike one frame and redraws it, 16 times, 35 ms apart
            angle = (self.skid_from + 1 + min(15, int(spin / PASS_HZ / SKID_STEP))) % 8
        if self.walk and self.heading in (LEFT, RIGHT):   # parked on its stand: frame 8 facing left, 9 facing right ($F80C)
            angle = 8 if self.heading == LEFT else 9
            img = self.player_img                        # $F80C points at $76C8/$76E8 in the first set, even with Martin aboard (the other sets have 8 frames)
        screen.blit(img[angle], ((self.px - cx + VIEW_X) * 8, (self.py - cy + VIEW_Y) * 8))
        if self.walk:                                    # Colin: 2x2 chars two rows above the bike, over the door cells
            frame = self.colin[32 * self.walk[0]:32 * self.walk[0] + 32]
            for k in range(4):
                mx, my = self.px + (k & 1), self.py - 2 + (k >> 1)
                if 0 <= my < 128:
                    screen.blit(char_surface(frame[8 * k:8 * k + 8], self.cell_attr(mx, my)), ((mx - cx + VIEW_X) * 8, (my - cy + VIEW_Y) * 8))
        if "item_markers" in self.fixes and self.show_items:
            self.draw_item_markers(screen, cx, cy)
        if FLASH_ON <= time.monotonic() - self.flash_at < FLASH_OFF:   # the crash routine's flash: ink and paper of the play area inverted ($D99B)
            invert_colours(screen, clip)
        screen.set_clip(None)
        self.draw_hud(screen)


def invert_colours(screen, rect):
    """$D99B: every attribute of the play area has its ink and paper bits inverted (AND 63, CPL, AND 63), brightness kept. On the finished picture:
    each colour channel that is on goes off and one that is off goes on."""
    pix = pygame.surfarray.pixels3d(screen)
    sub = pix[rect.x:rect.right, rect.y:rect.bottom]
    level = np.where(sub.max(axis=2, keepdims=True) == 255, 255, 205)
    sub[:] = np.where(sub > 0, 0, level).astype(np.uint8)
    del pix


def screen_surface(data):
    """A 256x192 surface from a 6912-byte Spectrum screen (pixels then attributes; FLASH is ignored)."""
    s = pygame.Surface((256, 192))
    for cy in range(24):
        for cx in range(32):
            attr = data[6144 + cy * 32 + cx]
            ink, paper = rgb(attr & 7, bool(attr & 0x40)), rgb((attr >> 3) & 7, bool(attr & 0x40))
            for r in range(8):
                y = cy * 8 + r
                byte = data[((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + cx]
                for bit in range(8):
                    s.set_at((cx * 8 + bit, y), ink if byte & (0x80 >> bit) else paper)
    return s


class _NoKeys:
    def __getitem__(self, key):
        return False


NO_KEYS = _NoKeys()              # a key state with nothing pressed: Controls.read() then reports the joystick alone


SCREEN_SECONDS = 4.0             # how long each loading screen stays up before the next one (any key skips it)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Action Biker, rebuilt from the original's code. Default: the game as the original plays it.")
    parser.add_argument("--fixes", action="store_true", help="play the version with every fix on")
    parser.add_argument("--fix", action="append", default=[], metavar="NAME", choices=sorted(FIXES), help="turn one fix on (repeatable)")
    parser.add_argument("--list-fixes", action="store_true", help="list the fixes and exit")
    parser.add_argument("--no-intro", action="store_true", help="skip the setup screen, the two loading screens and Select Controls (keyboard controls)")
    parser.add_argument("--controls", choices=sorted(controls.SCHEMES), help="choose the control scheme without the menu (skips the setup screen too)")
    parser.add_argument("--no-sound-effects", action="store_true", help="no sound effects (the setup screen starts with them unticked)")
    parser.add_argument("--no-music", action="store_true", help="no music (the setup screen starts with it unticked)")
    args = parser.parse_args(argv)
    if args.list_fixes:
        for name, text in FIXES.items():
            print(f"{name}: {text}")
        return
    if not os.path.exists(os.path.join(A, "map.bin")):
        raise SystemExit("The game's graphics, map and sounds are not here yet. They come from your own copy of the original game:\n"
                         "    python tools/extract_assets.py PATH/TO/ActionBiker.tap      (or .tzx, or a .z80 saved at the Select Controls menu)\n"
                         "See README.md.")
    fixes = set(FIXES) if args.fixes else set(args.fix)
    quiet = {name for name, off in (("sound_effects", args.no_sound_effects), ("music", args.no_music)) if off}
    asked = args.fixes or bool(args.fix) or bool(quiet)   # given on the command line: the setup screen starts from that, else from last time
    pygame.init()
    screen = pygame.Surface((256, 192))
    window = pygame.display.set_mode((256 * SCALE, 192 * SCALE))
    pygame.display.set_caption("Action Biker")
    try:
        sound = Sound(json.load(open(os.path.join(A, "sounds.json"))))
    except Exception as error:                     # no sound card: play silently
        print("no sound:", error)
        sound = None
    # The port starts with a screen the original does not have, a setup screen (port/options.py) where the trainer, the fixes and the sound are
    # turned on or off. Then, as the tape does: two loading screens (the KP Skips advert, then the title), Select Controls ($DD77), and the game.
    scheme = args.controls or ("KEYBOARD" if args.no_intro else None)
    menu = None if scheme else options.OptionsScreen(FIXES, load("font.bin"), *((fixes, set(options.SOUND) - quiet) if asked else (None, None)))
    stick = controls.Controls("KEYBOARD") if menu else None      # only its joystick is read on the setup screen; keys come as key presses
    shots = [] if args.no_intro or args.controls else [screen_surface(load(n)) for n in ("screen_ad.bin", "screen_title.bin")
                                                         if os.path.exists(os.path.join(A, n))]   # assets made from a .z80 have no loading screens
    menu_screen = screen_surface(load("screen_menu.bin"))
    world, pad, shown = None, None, 0.0
    clock = pygame.time.Clock()
    acc, running, paused = 0.0, True, False

    def start_sound(on):
        if sound:
            sound.mute(effects="sound_effects" not in on, music="music" not in on)
    start_sound(set(options.SOUND) - quiet)
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and world is not None and (e.key in (pygame.K_p, pygame.K_ESCAPE) or (paused and e.key == pygame.K_q)):
                if paused and e.key == pygame.K_q:        # paused: Q quits, P or Esc carries on
                    running = False
                else:
                    paused = not paused
                    if sound:
                        (pygame.mixer.pause if paused else pygame.mixer.unpause)()
                    clock.tick()                          # the time spent paused is not caught up afterwards
                    acc = 0.0
            elif paused:
                pass                                      # nothing else while paused
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:   # before the game (setup, loading screens, controls): Esc quits
                running = False
            elif e.type == pygame.KEYDOWN and menu is not None:
                if menu.key(e.key):                       # Enter: the setup is done, on to the tape's screens
                    fixes = menu.fixes
                    start_sound(menu.sound)
                    options.save(menu.fixes, menu.sound)
                    menu = None
                    shown = 0.0
                    clock.tick()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_TAB and world is not None and "map_view" in fixes:
                world.toggle_map()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_b and world is not None:
                world.toggle_trail()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_i and world is not None:
                world.toggle_markers()
            elif e.type == pygame.KEYDOWN and shots:      # any key moves on to the next screen
                shots.pop(0)
                shown = 0.0
            elif e.type == pygame.KEYDOWN and scheme is None and pygame.K_1 <= e.key <= pygame.K_5:
                scheme = controls.BY_MENU[e.key - pygame.K_0]
        if menu is not None:                               # the setup screen
            if stick.joystick:
                menu.pad(*stick.read(NO_KEYS))
            clock.tick(50)
            menu.draw(screen)
            pygame.transform.scale(screen, window.get_size(), window)
            pygame.display.set_caption("Action Biker (setup)")
            pygame.display.flip()
            continue
        mode = "original" if not fixes else "fixes: " + ", ".join(sorted(fixes))
        if scheme is not None and world is None:           # the choice is made: a new game (its fanfare plays first)
            pad = controls.Controls(scheme)
            world = World(sound, fixes)
            acc = 0.0
            clock.tick()
        if world is None:
            if shots:
                shown += clock.tick(50) / 1000
                if shown >= SCREEN_SECONDS:
                    shots.pop(0)
                    shown = 0.0
            else:
                clock.tick(50)
            screen.blit(shots[0] if shots else menu_screen, (0, 0))
            pygame.display.set_caption(f"Action Biker ({mode})")
        else:
            mask, fire = pad.read(pygame.key.get_pressed())
            acc += clock.tick(50) / 1000 * PASS_HZ
            while acc >= 1 and not paused:
                world.tick(mask, fire)
                acc -= 1
            world.draw(screen)
            if paused:                                    # not in the original: the port's pause (P or Esc)
                world.draw_paused(screen)
            pygame.display.set_caption(f"Action Biker ({mode}, {pad.name.lower()}){'  [I] item markers' if 'item_markers' in fixes else ''}{'  [B] breadcrumbs' if 'breadcrumbs' in fixes else ''}{'  [Tab] map' if 'map_view' in fixes else ''}  speed {10 - world.speed}  fuel {world.fuel}  sleep {world.sleep}  "
                                       f"items {world.items:07b}  score {world.score}  {world.message}" + (f"  - {world.over}" if world.over else ""))
        pygame.transform.scale(screen, window.get_size(), window)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
