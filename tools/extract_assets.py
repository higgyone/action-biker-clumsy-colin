"""Extract everything the pygame port needs from your own copy of the original game into assets/ (no game file needed at runtime).

Usage: python tools/extract_assets.py [GAME] [--out DIR]
  GAME  the game as a .tap or .tzx tape, or a .z80 snapshot saved at the Select Controls menu, or a .zip holding one of them
        (default: the first one found under Action-Biker_ZX-Spectrum_EN/ or game/)

The game is loaded and run in SkoolKit's Z80 simulator (tools/original.py): its own loader (for a tape), then the Select Controls menu
(the "menu" memory: the clean map, the tape's traffic table, the menu screen), then key 1 and its own start-up (the "level" memory: the
items placed in the houses, the pickups on the map, the HUD drawn). Everything below is read from those two, and the clock hands and the
speedometer needle are drawn by the game's own routines in the simulator. A .z80 has no loading screens: the port then skips them.

Writes to assets/:
  map.bin          128x128 tile ids, row-major, at the controls menu (clean: no pickups placed yet)
  objects.json     pickups/markers the game places at level start: [{"x","y","id"}] (diff of level vs menu map)
  tile_attr.bin    256 bytes, Spectrum attribute per tile id ($770A + id)
  tiles.bin        256 x 8 bytes, 1bpp chars ($79E0 + 8*id; ids 0-31 are zeroed, they are not tiles)
  buildings.bin    20 x 288 bytes of chars (index = building id, entry 0 empty) and
  building_attr.bin 20 x 36 attribute bytes; both 6x6 row-major (colours after the start-up, which completes buildings 4-8)
  player.bin       10 frames x 32 bytes ($75C8): 4 chars TL,TR,BL,BR per 16x16 frame
  vehicles.bin     3 types x 4 headings x 48 bytes ($734C): 6 chars, 3 wide x 2 tall, row-major
  houses.json      49 house doors (marker tile 205+): room contents and the $5B07 item bits each one grants
  player_water.bin 8 frames at $5B09 (bike in water, attribute $28); player_set2.bin 8 frames at $5C09 (when $5B07 bit 5)
  hud.bin          6912-byte screen (pixels + attributes) of the HUD with the live fields blanked; hud_clock.json the pixels of each clock
                   hand in each of its 60 places; hud_needle.json the speedometer needle's pixels for each speed counter; font.bin the ROM font (chars 32-127), font.png its sheet
  interior.json    the 20 house item graphics (positions, sizes, colours) and Colin's sprite for the house screen
  interiors.png    all 49 rooms (fixed furniture; the special items move every game); interior_items.png the item graphics
  traffic.json     the 20 road users as the tape loads them (menu snapshot): x, y, flags; the start-up frame updates them once
  hud_items.json   the five equipment pictures ORed onto the HUD bike picture (headlamp, tyres, snorkel, periscope, Turbo kit)
  colin_walk.bin   5 frames x 32 bytes: Colin walking into a house (shown before the room appears)
  sounds.json      the four tunes (start-up fanfare, end of game, finish, leaving a house) as [DE, HL] notes for the ROM's BEEP
  screen_cover.bin, screen_ad.bin, screen_title.bin, screen_menu.bin   the three loading screens of the tape (the Mastertronic / KP Skips / Clumsy Colin cover, the KP Skips advert, then the Action Biker title) and the
                   Select Controls screen (the menu's screen memory), each 6912 bytes: pixels then attributes (no loading screens from a .z80)
  messages.json    every on-screen message, 24 characters per line (items, pickups, dark area, endings)
  meta.json        addresses and start state (player, camera, SLEEP) for reference; source.json which game file the assets came from
  *.png            contact sheets for eyeballing (tiles, buildings, player, vehicles)
Spectrum attribute: bit 6 bright, bits 5-3 paper, bits 2-0 ink.
"""
import json
import os
import sys
import numpy as np
import skoolkit
from PIL import Image
from skoolkit.simulator import Simulator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from original import Original   # noqa: E402

MAP, TILE, BLK, BATTR, TATTR, PLAYER, VEH, TRAFFIC = 0x9858, 0x79E0, 0x80B8, 0x77E5, 0x770A, 0x75C8, 0x734C, 0x758C
args = [x for x in sys.argv[1:] if not x.startswith("--")]
out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "assets"
if "--out" in sys.argv:
    args.remove(out)
game = Original(args[0] if args else None)
menu, lvl = game.menu, game.level
os.makedirs(out, exist_ok=True)


def mem(ram, addr, n):
    return ram[addr - 0x4000:addr - 0x4000 + n]


def write(name, data):
    with open(os.path.join(out, name), "wb") as f:
        f.write(data)


def rgb(index, bright):
    level = 255 if bright else 205
    return (level if index & 2 else 0, level if index & 4 else 0, level if index & 1 else 0)


def char(data, attr):
    bright = bool(attr & 0x40)
    ink, paper = rgb(attr & 7, bright), rgb((attr >> 3) & 7, bright)
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    for y in range(8):
        for x in range(8):
            img[y, x] = ink if data[y] & (0x80 >> x) else paper
    return img


def sheet(name, items, cols, cw, ch, scale=3):
    """items: list of (w_chars, h_chars, [(chardata, attr)...] row-major)"""
    rows = (len(items) + cols - 1) // cols
    img = np.full((rows * (ch * 8 + 2), cols * (cw * 8 + 2), 3), 60, dtype=np.uint8)
    for i, (w, h, cells) in enumerate(items):
        r, c = divmod(i, cols)
        for k, (d, a) in enumerate(cells):
            cy, cx = divmod(k, w)
            y0, x0 = r * (ch * 8 + 2) + cy * 8, c * (cw * 8 + 2) + cx * 8
            img[y0:y0 + 8, x0:x0 + 8] = char(d, a)
    Image.fromarray(img).resize((img.shape[1] * scale, img.shape[0] * scale), Image.NEAREST).save(os.path.join(out, name))


# map and the objects the game adds when a level starts
m_menu = np.frombuffer(mem(menu, MAP, 16384), dtype=np.uint8).reshape(128, 128)
m_lvl = np.frombuffer(mem(lvl, MAP, 16384), dtype=np.uint8).reshape(128, 128)
write("map.bin", m_menu.tobytes())
objects = [{"x": int(x), "y": int(y), "id": int(m_lvl[y, x])}
           for y, x in zip(*np.nonzero(m_lvl != m_menu))]
json.dump(objects, open(os.path.join(out, "objects.json"), "w", newline="\n"))

# tiles (ids 32-201 real; zero the building-colour bytes that sit under ids 0-31)
tiles = bytearray(mem(menu, TILE, 256 * 8))
tiles[:32 * 8] = bytes(32 * 8)
tile_attr = bytearray(mem(menu, TATTR, 256))
write("tiles.bin", bytes(tiles))
write("tile_attr.bin", bytes(tile_attr))
sheet("tiles.png", [(1, 1, [(tiles[8 * t:8 * t + 8], tile_attr[t])]) for t in range(32, 202)], 16, 1, 1, 4)

# buildings
b_chars = bytes(288) + mem(menu, BLK + 288, 288 * 19)
b_attr = bytes(36) + mem(lvl, BATTR + 36, 36 * 19)   # the start-up fills in the colours of buildings 4-8 ($787F-$7917): not yet at the menu
write("buildings.bin", b_chars)
write("building_attr.bin", b_attr)
if any(not any(b_attr[36 * b:36 * b + 36]) or b_attr[36 * b:36 * b + 36].count(0) > 18 for b in range(4, 9)):
    print("warning: in this copy of the game the colours of buildings 4-8 ($787F-$7917) are missing, so those buildings are black on black, as "
          "this copy plays. The .tzx of the TOSEC set (or its [a] .tap) has them.")
sheet("buildings.png", [(6, 6, [(b_chars[288 * b + 8 * k:288 * b + 8 * k + 8], b_attr[36 * b + k]) for k in range(36)])
                        for b in range(1, 20)], 5, 6, 6, 2)

# player frames (drawn bright white on black, attribute $47) and vehicles (colour comes from the flags byte)
player = mem(menu, PLAYER, 320)
vehicles = mem(menu, VEH, 576)
write("player.bin", player)
water = mem(menu, 0x5B09, 256)         # sprite set used in the water (tile 65), drawn black on cyan (attribute $28)
set2 = mem(menu, 0x5C09, 256)          # second set, chosen by bit 5 of $5B07
write("player_water.bin", water)
write("player_set2.bin", set2)
write("vehicles.bin", vehicles)
sheet("player.png", [(2, 2, [(player[32 * f + 8 * k:32 * f + 8 * k + 8], 0x47) for k in range(4)]) for f in range(10)], 10, 2, 2, 4)
sheet("player_water.png", [(2, 2, [(water[32 * f + 8 * k:32 * f + 8 * k + 8], 0x28) for k in range(4)]) for f in range(8)], 8, 2, 2, 4)
sheet("player_set2.png", [(2, 2, [(set2[32 * f + 8 * k:32 * f + 8 * k + 8], 0x47) for k in range(4)]) for f in range(8)], 8, 2, 2, 4)
sheet("vehicles.png", [(3, 2, [(vehicles[48 * v + 8 * k:48 * v + 8 * k + 8], 0x47) for k in range(6)]) for v in range(12)], 4, 3, 2, 3)

# the table as the tape loads it (the menu snapshot): a new game's start-up runs one frame, which updates it once, and the port does the same
traffic = [{"x": menu[TRAFFIC - 0x4000 + 3 * i], "y": menu[TRAFFIC - 0x4000 + 3 * i + 1], "flags": menu[TRAFFIC - 0x4000 + 3 * i + 2]}
           for i in range(20)]
json.dump(traffic, open(os.path.join(out, "traffic.json"), "w", newline="\n"))

# houses: marker tile ids 205-253, 3 bytes each at $66B2 (26290). Bytes 0-1 and the top nibble of byte 2 are 20 item
# slots (bit set = item present, slot k drawn from the 7-byte record at $6626 + 7*k); the low 3 bits of byte 2 are the
# room colour. Slots 13-15 and 16-19 are the items that set $5B07 bits 4-6 and 0-3 when you visit (see $F80C).
houses = []
for i in range(49):
    b = mem(lvl, 0x66B2 + 3 * i, 3)   # level snapshot: the menu one holds a different, pre-game table
    gained = (((b[1] >> 4) << 3) & 0xF7 & 0xFF) | (b[2] >> 4)
    houses.append({"id": 205 + i, "bytes": b.hex(), "items": gained, "colour": b[2] & 7})
json.dump(houses, open(os.path.join(out, "houses.json"), "w", newline="\n"), indent=0)

# house interiors ($FA8E and $FB31): 20 item records of 7 bytes at $6626: column, "24 - row", graphics pointer, width and
# height in chars, ink colour. The graphics are width*height chars row-major, ORed over the room. Colin stands in every room
# from a record at $F89F (63647): column 14, row 8, 2x4 chars at $5DA9, white.
def item_record(addr):
    c, b, lo, hi, w, h, ink = mem(lvl, addr, 7)
    return {"x": c, "y": 24 - b, "w": w, "h": h, "ink": ink, "chars": mem(lvl, lo | hi << 8, 8 * w * h).hex()}
# The empty room (walls in perspective, the door and two windows on the right) is a stored picture: $F8CC swaps the 18x18 chars at $6748
# (8 bytes per char, row-major) and their attributes at $7168 with the play area, then the furniture is drawn over it.
interior = {"items": [item_record(0x6626 + 7 * k) for k in range(20)], "colin": item_record(63647),
            "viewport": [1, 1, 18, 18], "floor": [4, 4, 12, 12],
            "room": mem(lvl, 0x6748, 18 * 18 * 8).hex(), "room_attr": mem(lvl, 0x7168, 18 * 18).hex()}
json.dump(interior, open(os.path.join(out, "interior.json"), "w", newline="\n"))

def room(bits):
    """Render one house interior (18x18 chars) as an RGB array from a 20-bit slot mask."""
    pix, attr = {}, {}
    for cy in range(4, 16):
        for cx in range(4, 16):
            attr[(cx, cy)] = (colour << 3) | 7
    for it in [interior["items"][k] for k in range(20) if bits >> k & 1] + [interior["colin"]]:
        chars = bytes.fromhex(it["chars"])
        for j in range(it["w"] * it["h"]):
            c = (it["x"] + j % it["w"], it["y"] + j // it["w"])
            pix[c] = bytes(a | b for a, b in zip(pix.get(c, bytes(8)), chars[8 * j:8 * j + 8]))
            attr[c] = (attr.get(c, 0) & 0xF8) | (it["ink"] & 7)
    img = np.zeros((144, 144, 3), dtype=np.uint8)
    for cy in range(1, 19):
        for cx in range(1, 19):
            img[(cy - 1) * 8:(cy - 1) * 8 + 8, (cx - 1) * 8:(cx - 1) * 8 + 8] = char(pix.get((cx, cy), bytes(8)), attr.get((cx, cy), 0))
    return img


# contact sheet of all 49 rooms (fixed furniture only: no special items, which move every game), 7 x 7
sheet_img = np.full((7 * 146, 7 * 146, 3), 60, dtype=np.uint8)
for i, h in enumerate(houses):
    b = bytes.fromhex(h["bytes"])
    colour = h["colour"]
    r_, c_ = divmod(i, 7)
    sheet_img[r_ * 146:r_ * 146 + 144, c_ * 146:c_ * 146 + 144] = room(int.from_bytes(b, "little") & 0x1FFF)
Image.fromarray(sheet_img).save(os.path.join(out, "interiors.png"))
# every house item graphic on its own, in the colour the game gives it
sheet("interior_items.png", [(it["w"], it["h"], [(bytes.fromhex(it["chars"])[8 * j:8 * j + 8], it["ink"]) for j in range(it["w"] * it["h"])])
                              for it in interior["items"] + [interior["colin"]]], 7, 6, 5, 3)

# the clock hands and the speedometer needle, drawn by the game's own routines in the simulator from the level memory
ROM = list(open(os.path.join(os.path.dirname(skoolkit.__file__), "resources", "48.rom"), "rb").read())
FACE = [(x, y) for y in range(160, 184) for x in range(8, 32)]


def offset(x, y):
    return ((y & 0xC0) << 5) | ((y & 7) << 8) | ((y & 0x38) << 2) | (x >> 3)


def bit(data, a, x):
    return (data[a] >> (7 - (x & 7))) & 1


def run(memory, start, stop, a=0):
    regs = {"A": a, "F": 0, "BC": 0, "DE": 0, "HL": 0, "IX": 0, "IY": 0, "SP": 0xFF00, "I": 0, "R": 0}
    sim = Simulator(memory, regs, {"iff": 0, "im": 1}, {"fast_djnz": True, "fast_ldir": True})
    sim.registers[24] = start
    n = 0
    while sim.registers[24] != stop:
        sim.opcodes[memory[sim.registers[24]]]()
        n += 1
        assert n < 200000, "the routine did not stop"


def hand(place, store, store_end, draw, draw_end):
    """The clock routine $DC04 moves the minute hand at $DC27 and the hour hand at $DCB6; each is a line drawn by XOR with the line routine
    at $DCFB ($DC64 turns a place 0-59 into the line's offsets, table $DBE6, and quadrant signs, $DBE4; the hour hand is the same line
    scaled to (3n + 1) / 4). For one place: blank the clock face, store the new line, draw it, and return the pixels that came on."""
    memory = ROM + list(lvl)
    for x, y in FACE:
        memory[0x4000 + offset(x, y)] = 0
    run(memory, store, store_end, place)
    run(memory, draw, draw_end)
    return [[x, y] for x, y in FACE if bit(memory, 0x4000 + offset(x, y), x)]


clock = {"minute": [hand(p, 56392, 56407, 56410, 56419) for p in range(60)],   # $DC48-$DC57, then $DC5A-$DC63
         "hour": [hand(p, 56525, 56558, 56561, 56570) for p in range(60)]}     # $DCCD-$DCEE, then $DCF1-$DCFA
json.dump(clock, open(os.path.join(out, "hud_clock.json"), "w", newline="\n"))

# HUD: the screen furniture (red border, title, magenta score panel, speedometer dial, bike picture, clock face, FUEL box,
# blue message bar) is drawn once into screen memory by the start-up. Take the level's screen and remove the moving parts: the
# needle at rest and the two clock hands (XORed off again), and blank the fields the game fills in: the play area, the score/high/sleep
# digits and the message row. The fuel gauge is full at the start, so it has no lines yet.
hud = bytearray(lvl[:6912])


def cell_pixels(cx, cy):
    return [((cy * 8 + r & 0xC0) << 5) + ((cy * 8 + r & 7) << 8) + ((cy * 8 + r & 0x38) << 2) + cx for r in range(8)]


def blank(cx0, cy0, w, h, attr=None):
    for cy in range(cy0, cy0 + h):
        for cx in range(cx0, cx0 + w):
            for a in cell_pixels(cx, cy):
                hud[a] = 0
            if attr is not None:
                hud[6144 + cy * 32 + cx] = attr


for x in range(171, 203):              # the speedometer needle at rest (a 32-pixel line along the dial's base, y = 110)
    hud[offset(x, 110)] &= ~(0x80 >> (x & 7)) & 0xFF
blank(1, 1, 18, 18, 0)                 # play area (x 8-151, y 8-151)
for x, y in {tuple(p) for p in clock["minute"][lvl[0xDBD2 - 0x4000]]} ^ {tuple(p) for p in clock["hour"][lvl[0xDBD3 - 0x4000]]}:
    hud[offset(x, y)] ^= 0x80 >> (x & 7)


def blank_lines(cx0, y0, ncols, nlines):
    """Zero pixel lines y0..y0+nlines-1 for ncols chars from column cx0 (the digit fields start mid-char-row)."""
    for y in range(y0, y0 + nlines):
        for cx in range(cx0, cx0 + ncols):
            hud[((y & 0xC0) << 5) + ((y & 7) << 8) + ((y & 0x38) << 2) + cx] = 0


blank_lines(26, 44, 4, 8)              # HIGH digits ($44BA), SCORE ($44FA), SLEEP ($4C3A): 8 lines each
blank_lines(26, 60, 4, 8)
blank_lines(26, 76, 2, 8)
blank(4, 22, 24, 1)                    # message row
write("hud.bin", bytes(hud))


def needle(speed):
    """$D9BC (55740) sets the needle value 200 - 19 * speed counter ($E517) and draws it with the line routine at $DB3E (old one erased,
    new one drawn, both by XOR). Returns the pixels it sets and the panel pixels it clears, in the dial (x 165-240, y 70-111)."""
    memory = ROM + list(lvl)
    memory[58647] = speed
    run(memory, 55740, 55776)
    on, off = [], []
    for y in range(70, 112):
        for x in range(165, 241):
            now, panel = bit(memory, 0x4000 + offset(x, y), x), bit(hud, offset(x, y), x)
            if now != panel:
                (on if now else off).append([x, y])
    return on, off


needles = {sp: needle(sp) for sp in range(11)}
common_on = set.intersection(*[{tuple(p) for p in on} for on, _ in needles.values()])     # what every speed shares is the SLEEP digits
common_off = set.intersection(*[{tuple(p) for p in off} for _, off in needles.values()])
json.dump({str(sp): {"set": [p for p in on if tuple(p) not in common_on], "clear": [p for p in off if tuple(p) not in common_off]}
           for sp, (on, off) in needles.items()}, open(os.path.join(out, "hud_needle.json"), "w", newline="\n"))
font = bytes(ROM)[0x3D00:0x3D00 + 96 * 8]
write("font.bin", font)   # the ROM font, chars 32-127: the game prints all its text with it
sheet("font.png", [(1, 1, [(font[8 * c:8 * c + 8], 0x47)]) for c in range(96)], 16, 1, 1, 4)

r = lambda a: lvl[a - 0x4000]
json.dump({"map": MAP, "tiles": TILE, "tile_attr": TATTR, "buildings": BLK, "building_attr": BATTR,
           "player_frames": PLAYER, "vehicles": VEH, "traffic": TRAFFIC,
           "player_start": [r(0xE51A), r(0xE51B)], "camera_start": [r(0xE90B), r(0xE90C)],
           "heading": r(0xE519), "sleep": r(0x5B04),
           "traffic_seed": menu[0xF2B7 - 0x4000],   # $F2B7: the traffic generator's seed as the tape loads it (0); the start-up frame moves it on
           "note": "start values are read from the level snapshot"}, open(os.path.join(out, "meta.json"), "w", newline="\n"), indent=1)
# the game's messages: every one is 24 characters per line, shown in the blue bar at the bottom of the screen
def text(addr, n=24):
    return mem(lvl, addr, n).decode("latin1")


messages = {
    "items": [[text(0xFB9C + 57 * k + 2), text(0xFB9C + 57 * k + 26)] for k in range(7)],   # item records: 2 header bytes, 2 lines
    "crisps": [text(0xEF08)],                      # 61192 "Packet of KP Skips"
    "oil": [text(0xEF6C), text(0xEF84)],           # 61292 "Hit oil much too fast!" / "You need special wheels"
    "fuel": [text(0xEFBE)],                        # 61374 "Fill up with petrol"
    "dark_in": [text(0xF040), text(0xF058)],       # 61504 "You enter the dark area" / "You need a headlamp"
    "dark_out": [text(0xF09A)],                    # 61594 "You leave the dark area"
    "no_items": [text(0xF8A6)],                    # 63654 "No items in this house"
    "ending": [text(0xE306 + 24 * k) for k in range(6)],   # 58118: eight o'clock, get up, woken yourself up, clumsy, fuel, wake up
    "finish": [text(0xE422), text(0xE43A)],        # 58402 "You're here just in time" / "WELL DONE, COLIN"
}
json.dump(messages, open(os.path.join(out, "messages.json"), "w", newline="\n"), indent=1)

# the three tunes: the tune player ($FE08, 65032) reads notes of 4 bytes, DE (length in cycles) then HL (pitch), see port/sound.py
def notes(addr, n):
    raw = mem(lvl, addr, 4 * n)
    return [[raw[4 * k] | raw[4 * k + 1] << 8, raw[4 * k + 2] | raw[4 * k + 3] << 8] for k in range(n)]


json.dump({"start": notes(65071, 5),      # $E2BB: the fanfare before every game
           "end": notes(65091, 14),       # $E36B: after the message of every ending
           "win": notes(65147, 28),       # $E452: after the finish messages (reaching the airport with Martin)
           "house": notes(65259, 19)},    # $F863: when you leave a house
          open(os.path.join(out, "sounds.json"), "w", newline="\n"))

# the five equipment items each draw a small picture onto the HUD's picture of the bike when found (ORed over it; $FD63 with the
# 7-byte tail of each item record at $FB9C: column, 24 - row, pointer, width, height, ink)
hud_items = []
for k in range(5):
    col, rowb, pl, ph, w, h, ink = mem(lvl, 0xFB9C + 57 * k + 50, 7)
    hud_items.append({"flag": 1 << k, "col": col, "row": 24 - rowb, "w": w, "h": h, "chars": mem(lvl, pl | ph << 8, w * h * 8).hex()})
json.dump(hud_items, open(os.path.join(out, "hud_items.json"), "w", newline="\n"), indent=1)
# Colin walking into a house: 5 frames of 2x2 chars (top row first, 32 bytes each) at $72AC, drawn by $F860 over the door cells
open(os.path.join(out, "colin_walk.bin"), "wb").write(mem(lvl, 0x72AC, 160))
print("objects", len(objects), "traffic", len(traffic))

# the screens before the game: the tape's three loading screens (1: the cover, from the loader's 7020-byte block; 2: KP Skips advert; 3: title); the controls menu is
# drawn by the game itself, so it is the menu's screen memory. A .z80 has no loading screens (the port skips them when the files are missing).
for name, screen in zip(("screen_cover.bin", "screen_ad.bin", "screen_title.bin"), game.screens):
    write(name, screen)
write("screen_menu.bin", menu[:6912])
json.dump({"game": os.path.basename(game.path), "loading_screens": len(game.screens)}, open(os.path.join(out, "source.json"), "w", newline="\n"), indent=1)
