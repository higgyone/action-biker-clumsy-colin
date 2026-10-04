# Level map and first gameplay findings

Source: three snapshots saved from ZEsarUX (all local, gitignored):
`biker.z80` (controls menu), `biker_level.z80` (early level, score 0), `biker_level_later.z80`
(later, score 0016, bike moved). Findings were made by diffing them. Recorded in `work/biker.ctl`.

## Correction to earlier notes
The game is **top-down**, not side-scrolling (see the screen render: houses, gardens, road seen from
above, HUD panel on the right). The scenery strips at `$5B00+` are tile art for that view.

## Method
Only about 6% of RAM differs between the menu and gameplay (3008 of 49152 bytes), and only 188 bytes
outside screen and attributes differ between the two gameplay snapshots. Diff two snapshots of the
same game state and the changed bytes are the live data.

## Level map: `$9858-$D857`
- 128 x 128 tiles, 1 byte per tile, row-major, **128-byte stride**. 128 x 128 = `$4000` bytes.
- Rows start at addresses = `$58` mod `$80`, **not** at `$xx00` / `$xx80`. A first image drawn from
  `$9800` came out wrapped by 88 columns; the correct start was found from the data:
  - `$9780-$9857` is 216 zero bytes of padding, and the first tile band begins at `$9858`.
  - The last band ends at `$D857`, and `$D858` is code (`CD 77 DD` = `CALL $DD77`).
- Evidence for the 128 stride: in the later snapshot, 2x2 blocks of tile ids `BE BF` / `C0 C1`
  appear and vanish at addresses exactly `$80` apart (e.g. `$AA2B` and `$AAAB`). They look like
  moving or removable objects placed on the map.
- Drawn as a 128-wide greyscale image (`work/map_level.png`, local) it shows a framed grid with road
  and building blocks. The edges carry repeating tile bands: ids 32-35 (random), 37-40 and 52-55 / 58-61
  (period-4 patterns), and 82 (a long bar).
- Map extent is exact (both ends confirmed). The tile ids index the 8-byte graphics at `$79E0` (next section).

## Score: `$5B05` (16-bit), high score `$5B02` (16-bit)
The score is a 16-bit binary number at `$5B05` and the high score one at `$5B02` (little-endian). Checked with the
snapshot that showed HIGH 0016 and SCORE 0016: both held 16. The routine at `$E08D` prints them (see below).
`$E04B-$E04F` is only a temporary ASCII digit buffer used while converting a number to print (it read
`30 30 30 31 36`, "00016", in that snapshot), and the number-to-decimal routine follows it at `$E050`. An
earlier version of this note called that buffer the score; it is not.

## Tile graphics: `$79E0 + 8 * id`, ids 32-201 (confirmed)
`tools/tile_test.py` slides the 20 x 18 play area over the map and votes for the base address that
makes the map ids reproduce the on-screen character cells. One answer stands out: window x=50, y=91,
base `$79E0` scores 74 matching cells against 34 for the runner-up.
- A tile is **one 8x8 character, 8 bytes**, pixel rows top to bottom, MSB = leftmost pixel. Tile `t`
  is at `$79E0 + 8*t`. Every tile id that could be checked on screen matches byte for byte.
- Ids 32-201 are tiles (last non-zero byte `$802D` = tile 201). Ids 0-19 are not tiles (0 is blank,
  1-19 are buildings, below) and 20-31 do not occur. The bytes that sit under tile ids 0-31 are the
  building colour blocks, which is why "tile 0" looks like a few stray dots.
- The early level screen is the map window with top-left tile (50, 91) (187 of 191 non-blank cells
  match). The later snapshot's window could not be pinned down: ids 1-5 look identical, so a wrong
  window still matches. Treat any later camera position as unknown.
- The outer ring of the 20 x 18 test window is a 1-pixel frame drawn around the play area, so the real
  viewport is smaller; that ring caused the early "mismatches".

## Buildings: ids 1-19 are 6 x 6 character blocks at `$80B8 + 288 * id`
First clue: on screen, map ids 6 and 16 showed a different pattern in every cell. Every connected
region of ids 1-19 in the whole map is an exact solid **6 x 6 rectangle** (about 130 of them), i.e. the
map only marks a footprint. The picture comes from a block of 36 consecutive 8-byte chars, row-major,
6 per row: cell (row, col) of the footprint, counted from its top-left, shows char `6*row + col`.
- House (id 16) matched at `$92B8` (34 of 34 non-blank cells), the id 6 block at `$8778` (35 of 35).
  They are exactly 10 blocks (10 x 288 bytes) apart, giving the formula `block(id) = $80B8 + 288*id`.
  The formula then predicted ids 1 and 13 correctly (all 10 visible cells matched).
- 19 blocks run from `$81D8` (id 1) to `$9737`; id 0 has no block. `$9738-$9857` is zero padding.
- From `work/blocks_80b8.png`: 1-3 the same house, 4-5 the same house again, 6 half-timbered house,
  7 cafe, 8 police station, 9 bistro, 10 baker, 11 butcher, 12 church, 13 fire station, 14 school,
  15 house with fence, 16 house, 17 airport terminal (control tower and flags), 18 works/factory, 19 petrol station.
  (An earlier note here guessed that id 6 was a garden with a tree; that was wrong.)

### Building colours: `$77E5 + 36 * id`
Each building also has 36 Spectrum attribute bytes (flash/bright/paper/ink), one per char cell, 6 rows
of 6, at `$77E5 + 36*id` (ids 1-19 run `$7809-$7AB4`). They were found by searching RAM for the attribute
rows seen under the two id-16 houses on screen (roof `00 42 42 42 42 00`, walls `07 38 38 38 38 38`).
- Ids 1-5 draw the same pixels in different colours: roof `50` (bright red) and base `20` (green) in
  all, walls `30` yellow (id 1), `18` magenta (id 2), `28` cyan (id 3), `38` white (id 4), and a
  green-walled variant (id 5). That is why the map has several ids for one picture.
- In the level snapshot ids 4-8 are partly or wholly zero (black on black = invisible); the menu
  snapshot holds the complete set. **Solved: it is the copy of the game, not the game.** Loading each copy of the TOSEC set in
  the simulator (`tools/original.py`) shows the plain `.tap` and the `[a]` `.tzx` load with the 142 bytes at `$787F-$7917` zeroed
  (that tape was the one played for the level snapshot), while the `.tzx`, the `[a]` `.tap`, the `[a2]` `.tzx` and every `.z80`
  have the colours, and keep them through the start-up. `tools/extract_assets.py` warns when a copy lacks them.
- Colours of the ordinary tiles are in a separate table, below.

### Tile colours: `$770A + id`
One attribute byte per tile id. Found by reading the attribute under every tile id visible in the early
level screen: all 38 ids showed a single attribute each, and a search for a table that reproduces
them gave exactly one base, `$770A`, with 38 of 38 matches (next best 24). The table is the same in the
menu and level snapshots.
- Only ids 32-201 are tile ids, so the usable part is `$772A-$77D3` (170 bytes). The 32 bytes below it
  (`$770A-$7729`) look like pixel data, not attributes, and belong to something else.
- Grass is green, roads black, fences and lamp posts white, the walled central block cyan (water?)
  with a yellow edge and an island with two houses. The colour render now draws everything in colour.
- Trees: the tree sprites are part of the same tile table (red trunk, green leaves), so they come out
  right. Still not found: sprite data for the bike, cars and pedestrians.

### Objects placed at game start (tile ids 184-204)
The map in the controls-menu snapshot has none of these; the game places them when a level starts. Each
pickup is a 2x2 object using four consecutive tile ids laid out `a b / c d`, drawn from the ordinary
tile set (view them as 2x2: side by side the shapes look scrambled):

| Tile ids | Layout | Colour | Placed | Object |
|---|---|---|---|---|
| 190-193 | 2x2 | yellow (`46`) | 30 | crisp packet (the game's sponsor is KP Skips; see the first loading screen) |
| 194-197 | 2x2 | blue (`41`) | 20 | oil slick |
| 198-201 | 2x2 | red (`42`) | 3 | fuel can |
| 184-189 | 3x2 (`184 185 186 / 187 188 189`) | red (`42`) | 1 | aeroplane |

- The fuel can was named by the user; crisp packets and oil slicks are from shape, colour and the user's
  knowledge of the game. Only the yellow one was on screen to confirm its colour (`46`, matching the table).
- **Aeroplane (184-189):** a red propeller plane, 3x2 tiles, one in the whole map at (116..118, 30..31). It is
  parked on a black strip beside the airport terminal (building id 17, footprint at (109, 24): a control
  tower, flags and a long window) in the top-right of the map (`work/airport.png`, a crop of the colour
  render). It was never on screen in a snapshot, so the colour is not checked against the screen, but the table
  colours it red and the scene fits. An earlier note called it a "helicopter or aeroplane" and wondered if it
  was white; the airport settles the object as an aeroplane. Whether the game does anything with it is unknown.
- Some of the 30 yellow positions differ between the two level snapshots, so objects are moved,
  picked up or re-placed as the game runs. Early positions start at map (85, 3), (107, 4), (30, 11),
  (72, 19) and so on.
- Tile ids 176-183 are the lake shore (yellow and cyan edge tiles), not objects.
- Tile ids 203 and 204 appear 12 times each in every snapshot (at (3|4|27|28, 78) and (3|4|27|28, 81) for
  the ones seen) but their graphics are blank, so they may be invisible markers.
- Not in the map or tile data: the bike, the rider and other moving sprites. The 32 bytes at
  `$770A-$7729` look like part of a small figure but do not form a clear 2x2 picture in either order,
  so they may belong to something larger that starts earlier.

### Player sprite (the bike): 16x16, frames at `$75C8`
Found by drawing the map under the early level screen with the rules above and comparing: every cell
matched except a 2x2 block of chars at the centre of the play area (screen cells (9..10, 9..10)), which
is the player, drawn with attribute `47` (bright white on black). Searching RAM for those 32 bytes
(four chars in the order top-left, top-right, bottom-left, bottom-right) found them at `$7608`.
- **Set 1: 10 frames x 32 bytes at `$75C8-$7707`.** Frame n is at `$75C8 + 32*n`. Frame 2 (`$7608`) is the
  bike from above, riding straight; the others lean and turn (frames 0, 8 and 9 show the wheels from the
  side). Pictures: `work/player_sprites.png` (local).
- **Set 2: 8 frames at `$5C09-$5D08`.** Frames 2 and 6 equal set 1's frames 2 and 6 exactly; the other six
  are close but not identical (235-241 of 256 pixels), so they may be in-between angles. Relation not
  established. A working copy is also possible.
- No mask: the sprite is drawn over a black background. How the game chooses a frame (heading? lean?) and
  how it gets onto the screen is not known yet.
- Position: the bike stays near the middle of the view and the camera mostly moves, not the sprite (the exact rule is the "Camera" section below).
  In the early snapshot the camera's top-left is map tile (50, 91), putting the player at about
  map tile (59..60, 100..101).
- The 32 bytes at `$770A` are not this sprite: they are the first 32 entries of the tile colour table (`$770A + id`), for ids 0-31,
  which no tile uses (ids 1-19 are buildings with their own colours at `$77E5`).

### Camera: how the view follows the bike (decoded)
Each move handler (`$E538` right, `$E5E5` up, `$E689` down, `$E736` left) tests the tiles ahead, and if the way is free does **one of two things**: moves the
bike across the screen (`$E51A`/`$E51B` change, so do the counters at `$E51C` = column + 1 and `$E51D` = 23 - row) or scrolls the view one tile (`$E90D`; the bike's map
position changes but its place on the screen does not). The choice, with the bike's offset (ox, oy) from the view's top-left tile, is:

| moving | scrolls when | else |
|---|---|---|
| right | camera x < 110 and ox >= 8 | the bike moves right on the screen |
| left | camera x > 0 and ox <= 7 | the bike moves left on the screen |
| down | camera y < 110 and oy >= 8 | the bike moves down |
| up | camera y > 0 and oy <= 6 | the bike moves up |

(code: right `$E538` compares the camera with 110 and the column counter with 8; down compares the row counter with 15 and up with 16, left the column with 8.) So the view
has a **dead zone**: sideways the bike sits at offset 8 after riding right and 7 after riding left (one tile of slack); vertically at 8 after riding down and 6 after
riding up (two tiles). After turning round the bike first travels that far across the screen before the view follows. At the edges of the map the camera stops at 0 and
110 (= 128 - 18) and the bike rides on to the edge of the screen. A new game starts with the camera at (51, 92) and the bike at offset (8, 8).
In the port: `World.follow()` is this rule and `World.cam` the camera, `tools/check_camera.py` runs the original's four handlers in the simulator for 1357 random moves
(scrolling and not, near the map edges too) and finds 0 differences in the bike's position, the camera and the counters.

### Game state variables: player, camera, heading (found and checked on 5 snapshots)
Found by searching two snapshots for values that changed in step with the camera, then read straight out of
the start-up routine at `$D858` (55384), whose first lines store the initial values.

| Address | Meaning | Start | After riding 6 tiles south |
|---|---|---|---|
| `$E51A`, `$E51B` | player map tile x, y (top-left of the 2x2 sprite) | (59, 100) | (59, 106) |
| `$E90B`, `$E90C` | camera: top-left map tile of the visible 18 x 18 viewport | (51, 92) | (51, 98) |
| `$EB36` | the same viewport as a pointer: `$9858 + 128*y + x` | `$C68B` | `$C98B` |
| `$EB38` | the map address of the cell being fetched for drawing: the scroll routines step it down the new edge column (from `$EB36 + 17`) or along the new row, and `$E83B` points it at the cells the bike has just left; `$EB3C` reads the tile there | `$C69D` | `$CD14` |
| `$E734` | pointer to the sprite frame being drawn (frame table at `$E732` = `$75C8`) | `$7608` (frame 2) | `$7688` (frame 6) |
| `$E519` | bits 7-6 look like the heading | `$C0` | `$40` |
| `$E51C`, `$E51D` | the bike's place in the view: column + 1 and 23 - row (the camera's dead zone, see below) | (9, 15) | (9, 15) |

- The start-up routine stores the camera as (51, 111) and then scrolls it 19 rows up to (51, 92) with the
  routine at `$E90D`; that is why the first screen is at y = 92.
- The player is drawn 8 tiles right and 8 down from the camera in the early snapshots. In the later
  snapshot the player is at (120, 60) and the camera at (110, 54), so the camera does not always sit that
  way: see the camera rule below (decoded).
- **Four orientations, confirmed in the code** (the user suggested it; the movement routines show it). Bits 7-6
  of `$E519` are the heading and the sprite frame follows from it:

  | Heading `$E519 & $C0` | Direction | Move | Sprite frame | Seen |
  |---|---|---|---|---|
  | `$C0` | up | y-1 | base + 64 = frame 2 (`$7608`) | at game start |
  | `$80` | right | x+1 | base + 128 = frame 4 (`$7648`) | in the later level snapshot |
  | `$40` | down | y+1 | base + 192 = frame 6 (`$7688`) | after riding south |
  | `$00` | left | x-1 | base + 0 = frame 0 (`$75C8`) | in the left-facing snapshot |

  The input byte at `$DFA7` has bit 0 = left, bit 1 = right, bit 2 = up, bit 3 = down. The dispatcher at
  `$E51E` calls one handler per bit (`$E538` right, `$E5E5` up, `$E689` down, `$E736` left). The odd frames
  (1, 3, 5, 7, 9) look like leaning poses; bit 5 of `$E519` seems to flag a turn in progress (it is tested
  and cleared when the bike finishes turning). A bike facing a new direction first turns, then moves.
- Each handler tests the tiles just ahead of the sprite (the two tiles on the leading edge) with the routine
  at `$EE75` before moving; a solid tile stops the move. That is where buildings and fences block the bike.
- **Camera (decoded, below):** the pair `$E51C`, `$E51D` holds the bike's place in the view (column + 1, 23 - row); the four handlers use it as a dead zone.
- **Traffic table, `$758C-$75C7`: 20 other road users, 3 bytes each = x, y, flags.** Walked by three routines:
  `$D8F9` (does the player overlap one? see SLEEP below), `$F1CC` (moves them) and `$F42F` (draws them). The
  entries inside the viewport match what is on screen.

  | Seen on screen | Entry | Position | Flags | Type | Heading |
  |---|---|---|---|---|---|
  | cyan bike (attribute `$45`) | 16 | (52,108) then (58,115) | `$95` then `$15` | 1 | right, then left |
  | red bike (`$42`) | 19 | (59,108) | `$92` | 1 | right |
  | magenta car (`$43`) | 14 | (52,108) | `$A3` | 2 | right |

  **Flags byte:** bits 7-6 = heading (0 left, 1 down, 2 right, 3 up, same as the player), bits 5-4 = vehicle
  type (0 van, 1 motorbike, 2 saloon car), bits 2-0 = the colour it is drawn in; **bit 3 is never used** (every reader masks it away or leaves it alone; `tools/check_traffic_bit3.py` runs 60 frames with it set and clear and gets identical vehicles and screens).
  This is now backed by the drawing code, not just the examples (see the sprites below).
- The vehicles are drawn over the map, and a rider just past the bottom edge of the viewport can show as a
  sliver in the row below the frame (see the bakery chimney below).

### Tile check `$EE75` (61045): what blocks the bike (decoded)
Called by each move handler with A = the tile id under one of the two leading-edge cells (HL = its map pointer).
It returns A = 0 to let the bike through and A != 0 to block; a handler stops at the first non-zero result.
- **Passable:** id 0 (road, 3302 cells), id 69 (blank black, 88 cells), pickups 190-201, markers 203 and 204, and
  every id 205+ (invisible zone markers, 2 cells each; the id is stored in `$E516`).
- **Blocked:** everything else, so buildings (1-19), grass, fences, lamp posts and water (id 65, blank cyan, 1874 cells)
  all stop the bike. The bike is road-only. Id 65 passes only if `$5B07` bits 2 and 3 are both set (unknown meaning);
  otherwise it costs a SLEEP point via `$D962` and blocks.
- Only the **top-left** cell of a pickup acts: 190 crisps (score +2 at `$5B05`, the 2x2 cleared by `$E1D0`),
  194 oil (unless `$5B07` bit 1 = "special wheels" or `$E517` is non-zero: message "Hit oil much too fast! You need
  special wheels", SLEEP -1, the object stays), 198 fuel can ("Fill up with petrol", loops until fuel state is (4,4)).
- 203/204 are the dark-area markers: unless `$5B07` bit 0 (headlamp) is set, a message says "You enter the dark area / You
  need a headlamp"; `$F005` (61445) tracks inside/outside.
- `$F056` (61782) resets the player sprite pointer from the heading and **the player's attribute lives at `$E731` (59185)**:
  71 (`$47`, bright white) normally. The only other value written is 40 (`$28`, black on cyan) in the water branch of `$EE75`
  (tile 65, see above), with the sprite pointer set to `$5B09` (a different, unextracted sprite set), so that is a rider in
  the water, not petrol. The petrol handler (`$EFD7`) does not change the colour. Bit 5 of `$5B07` selects sprite set 2 at `$5C09`.
- **Checked on the whole map:** a flood fill from the player's start using exactly this passable set reaches 3,480 of the
  3,514 free cells, and they are the roads and pavements (`work/walkable_map.png`).
- **Handlers** (entry addresses): 190 crisps `$EECA`, 194 oil `$EF20`, 65 water `$EF9C`, 198 fuel can `$EFD6`, 203 and 204 the
  dark-area markers `$F006` and `$F070`. Water is tile 65 (attribute `$28`, cyan), a lake at x 16-63, y 16-63 with an
  island in it (two houses); with both the snorkel and periscope the bike swims there.
- **Dark area:** the routine at `$F7B5` returns the real tile if `$5B07` bit 0 (headlamp) is set. Without it, tiles with map
  y above 80 and x up to 40 (41 for the vehicle routine) come back as tile 205 (blank), so the map there is invisible without the headlamp. The markers
  sit on its borders: 203 (enter) at (3,81), (4,81), (27,81), (28,81), and along x = 39; 204 (leave) at (3,78), (4,78),
  (27,78), (28,78), and along x = 42.
- Sprite frames 0-7 are eight compass poses (left, up-left, up, up-right, right, down-right, down, down-left); 8 and 9 are side
  views. The port steps the angle by 45 degrees per tick when turning. The real turning timing is not decoded.

- **Frames 8 and 9 are the bike parked on its stand, with no rider** (the user's reading of the pictures): the rider has
  gone into a house. Parking is the routine at `$F80C` (63500), called from `$D8BA` and `$D8E2` when the player touches a
  205+ marker tile this pass (`$E516` non-zero) and the **trigger key, Space** (bit 4 of `$DFA7`), is down. It sets the speed
  counter `$E517` to 10 (dead stop), shows frame 8 (facing left) or 9 (facing right) and runs the house visit below.
  Keys (`$DFA8`, 57256): N left, M right, A up, Z down, Space trigger.
  **How to park:** the marker is two invisible road tiles (one above the other) in front of a house door. The original only sees
  it on a pass where the *moving* bike's two leading-edge tiles touch it (the tile check sets `$E516`, and `$E516` is cleared at
  the end of every pass), so Space has to be held as the bike's front reaches the door; tapping it after stopping does nothing.
  The port does exactly this by default (`tools/check_parking.py` runs the original's pass routine from 584 start positions and finds the same pass and
  position in the port every time); the forgiving version (Space also works when a marker is under or just ahead of the stopped bike) is the optional
  fix `easy_parking` (`python port/biker.py --fix easy_parking`).

### Houses (marker tiles 205-253) and the items byte `$5B07`
The 49 marker ids are the doors of 49 houses. The routine at `$F80C` (63500-63650) draws the inside of the house you park at, a
12x12-char room (`$FB03`, colour from the table), furniture and items, and then grants items.
- **Table at `$66B2` (26290), 3 bytes per door** (id 205 first). Bytes 0-1 and the top nibble of byte 2 are 20 slots; a set bit
  draws item `k` from the 7-byte record at `$6626 + 7*k` (x, y, graphics pointer, size, colour; not decoded). The low 3 bits of
  byte 2 are the room's paper colour.
- Slots 16-19 (byte 2 bits 4-7) set `$5B07` bits 0-3 and slots 13-15 (byte 1 bits 5-7) set bits 4-6. The rest are furniture.
  Entering ORs the new bits into `$5B07`. If nothing new was gained the message "No items in this house" is shown. Each visit
  then adds **3 to the score** (even with no items), and the bike is drawn parked facing left (`$E519` = 0) or right.
- **`$5B07` bits, with the item names** (from the seven 57-byte item records at `$FB9C`, each holding the two-line message
  shown when the item is found): 0 **headlamp** ("You can see in the dark"; dark areas), 1 **new tyres** = special wheels
  ("Good for oily roads"; oil), 2 **snorkel** ("That may come in handy") and 3 **periscope** ("Can you go in the water?"),
  both needed to ride into water (bit 2 alone blocks without a SLEEP penalty), 4 **Turbo DIY kit** ("It is very easy to
  fit"; **does nothing**: no code ever tests bit 4, so it is only a 10-point pickup), 5 **Martin**, the passenger ("You've found Martin. Get him to the airport
  quick"; the user's reading of set 2 as two people on the bike is right): selects sprite set 2 (`$5C09`) and is needed on
  the finish tile (105,27) beside the airport terminal at (109,24), 6 **the friend's mum** ("Your friends mum is in. Stay for
  some tea please"; five houses; **a tea break**: the routine at `$FD45` runs the clock 600 passes, see below). See
  `notes/04-how-the-game-works.md` for how these fit together.
- Doors that give an item (level table, see `assets/houses.json`): 226 headlamp, 246 wheels, 227 bit 2, 231 bit 3, 214 bit 4,
  242 bit 5, and 207, 233, 234, 236, 247 bit 6 (five houses). **The menu snapshot holds a different table** (205, 220, 226, 229,
  241, 245, 247, 253), so the game reshuffles it when a game starts; all gameplay snapshots agree, so a fixed seed or a fixed
  layout per level. The port uses the level table.
- **Water set:** `$5B09`, 8 frames of 16x16 in the same order as the player set, drawn black on cyan (`$28`): the bike with
  spray and a wake. It is shown while the bike is on a water tile (65) with the items for it.

- **`$E517` (58647) is the speed counter:** 10 = stopped, 0 = full speed. The per-pass logic is in `$D899`'s body
  (55458-55543) and `$E4E8` (58600):
  - The player is only processed when the wait counter `$D8C8` (55496) is 0. After each processed pass it is reloaded
    with the speed counter, so a tile step takes **speed + 1 passes**. Pressing a key from a standstill (10) lowers the
    counter by 1 per processed pass: 10, 9, 8 ... 0 passes between steps, about 55 passes to reach full speed.
  - Key held: counter -1 (to 0), save the keys at `$E518` (58648), call the handler. Key released: counter +1 (to 10) and the
    handler is called with the **saved** keys, so the bike coasts and slows. At 10 it only redraws.
  - Dispatch (`$E5A6`, 58660) tests input bits in the order 0 left, 2 up, 1 right, 3 down.
  - The loop body runs twice per frame call (`$D8C9` = 2). **The pass rate was measured by running the original's frame routine in a simulator**
    (3.5 MHz T-states): a frame takes about **102 ms** (357,000 T-states) whether the bike is stopped or at full speed, so there are
    **19.5 passes per second** (the port's `PASS_HZ`). Nothing syncs it to the 50 Hz interrupt, and the earlier claim that a beeper routine sets the
    pace was a misreading: `$DB3E` draws the speedometer needle.
- **Correction: `$E28F`/`$E290` is the fuel gauge, not a clock.** `$DA03` (55779) adds `(10 - speed) >> 1` to an 8-bit
  accumulator at `$D9E2` (55778) every pass (nothing at a standstill); each carry moves the gauge one step, drawn as a bar on
  screen (`$DA67`, XOR on the HUD). The gauge walks (C,B) = (4,4) -> (4,1) -> (3,8)..(3,1) -> (2,8)..(2,2): **18 steps**, and
  (B,C) = (2,3) is "out of fuel". A full tank lasts about 512 passes at full speed, longer when slower. The fuel can refills it
  to (4,4). The clock is decoded in the next section.
- Oil only costs SLEEP when the counter is 0 (full speed) and there are no special wheels.

### What each item is worth, the Turbo kit and the friend's mum (decoded from `$FD63` and `$FD45`)
Every read of `$5B07` in the program was found by searching the raw bytes for its address (`07 5B`): the tests are bit 5 (`$E2C1`
finish, `$F157` sprite set), bit 0 (`$F006`, `$F070`, `$F0B4`, `$F7B5` dark area), bit 1 (`$EF20` oil), bits 2 and 3 (`$EF9C` water),
and the item routine ORs bits in (`$F865`) and clears bit 6 (`$FD59`). **Nothing ever tests bit 4.**
- **Turbo DIY kit (bit 4) does nothing.** It is a 10-point pickup with a message, and no speed or fuel logic looks at it.
- **Points per item** (byte 0 of each 57-byte record at `$FB9C`, bit 7 masked off, added to the score by `$FD63`): headlamp, tyres,
  snorkel, periscope and Turbo kit **10 each**, **Martin 100**, the friend's mum 0. Byte 1 of the record is a mask that removes the
  item from the room's item bytes, so each can be taken once; the mum is not removed. A visit itself adds 3.
- **The friend's mum is a tea break** (`$FD45`, 64837, called when her slot is set in the room after the item messages): it calls
  the clock routine `$DC04` 600 times (6 x 100, each with a 256-step delay loop), so **600 passes of game time go by** in
  0.84 s of real time (measured), after her message's last pause and before its line scrolls out; the port runs them over that time so the hands whirl. That is 120 clock ticks: the seconds counter `$DBD2` wraps twice, so **SLEEP +5 twice**
  (capped at 50) and the three fuel cans are put back, the hour hand moves 10 places (a sixth of the 60-place day), and
  the clock hands whirl. Fuel is not used during the tea. Then bit 6 of `$5B07` is cleared; it is set again when the visit ends, so
  she can be visited again (five houses: 207, 233, 234, 236, 247 in the first game).
- So the mum is a trade: SLEEP back and the cans back, in return for 600 of the 3,600 passes in the day. The eight-o'clock test
  (`hour = 40` and `second = 0`) is only made by the main loop, not inside the tea, so as far as the code reads a tea that spans
  that exact moment would step over it; not tested in a running game.

- **In the port:** `ITEM_POINTS` and `ITEM_NAMES` in `port/biker.py` hold the points; a visit adds 3 plus the item's points and the item leaves the
  room when the visit ends (the mum stays); `tea()` runs `clock_pass()` 600 times; `tools/check_port_items.py` checks all of it headlessly.
  Messages come from `assets/messages.json` (extracted by `tools/extract_assets.py`: the items, pickups, endings and the finish, 24 characters per
  line as in the game). The port plays each message as a timeline in the middle row of the bar (class `Bar`: lines scroll in one at a time, with the
  original's measured pauses, see "Message bar" below), and draws a room inside the play area so the HUD and the bar stay on screen.

### Equipment shows on the HUD bike picture (correcting an earlier note)
I first said no indicator exists, because no code *reads* `$5B07` to draw one. The pictures are drawn **once, when the item is found**
(the announce routine `$FD63` uses the 7-byte descriptor at the end of the item record: column, 24 - row, pointer, width, height, ink),
and the screen then keeps them. A snapshot taken with the new tyres (`work/biker_tyres.z80`, `$5B07` = 2) showed it: the HUD cells at
(28..30, 16..18) equal the no-item cells **ORed** with the picture at `$609E` (9 of 9 cells), and nothing else on the HUD changed apart from the
live parts (score, clock hands, message bar). The five equipment pictures, all black ink on the white panel:

| Item | Picture | Size | HUD cell | What it draws on the bike |
|---|---|---|---|---|
| headlamp | `$6056` | 3x3 | (20,14) | a dotted beam of light in front of the bike |
| new tyres | `$609E` | 3x3 | (28,16) | fatter wheels |
| snorkel | `$60F6` | 2x2 | (29,14) | a pipe at the top right |
| periscope | `$6156` | 2x2 | (29,17) | a pipe at the bottom right |
| Turbo DIY kit | `$60E6` | 2x1 | (29,16) | a small badge (the kit does nothing else) |

Martin (`$5D09`, 2x4) and the friend's mum (`$5D49`, 3x4) use the same descriptor but are drawn at the room's centre. The picture of all
five on the bike is `work/hud_items.png` (local). The bike sprite itself only changes for the passenger (sprite set 2) and the water.

### Colin walks into the house (`$F860`, 63776)
When the bike parks at a door, before the room appears, **five frames of Colin walking in** are drawn: 32 bytes each from `$72AC`
(frame n at `$72AC + 32*n`; 2x2 chars, top row first), copied over the 2x2 cells two rows above the bike's cells (column `$E51C`, row
`24 - ($E51D + 2)`), so the figure takes the colour of the door cells under it. Each of frames 1-4 is followed by a 64000-step delay
(about 0.29 s), frame 5 is followed by the room at once. Colin shrinks over the frames as he walks away into the doorway. The bike is
first redrawn as the parked bike (frame 8 facing left, 9 facing right) and the game is paused for the whole animation. Seen in the
user's play; frames reproduced in `work/colin_walk_pixels.png` (pixels only) and `work/port_walk_in.png` (in the port, at a real door).
**Verified on a real snapshot** (`work/biker_house_enter.z80`, taken during the delay between frames, PC `$F95A`): the four cells at column `$E51C`,
rows 24 - (`$E51D` + 2) and the next hold the bytes of frame 2 exactly (4 of 4 chars, top row first), their attributes are `28 28 / 20 20`, which are the colours of
the wall and hedge underneath (the figure inherits them: black ink on cyan and green there), and the bike is parked facing left (frame pointer `$76C8`, frame 8).

### The message bar: one line at a time in the middle row (`$E008` print, `$E01F` scroll)
The bar is three blue rows (20-22) but only the **middle row (21)** shows text. `$E008` (57352) sets row 22's attribute to `$49` (blue ink on blue
paper, invisible), prints a 24-character line there, and falls into `$E01F` (57375), which shifts the pixel lines of rows 21-22 up 8 times, so the text
**scrolls up from the hidden bottom row into the middle row** and stops there. Whatever was in the middle row is pushed off the top of that row, so it is
**one line at a time**; row 20 is never used. A message ends with another `$E01F`, which scrolls the last line up and out and leaves the bar empty.
Checked by running the routines in a simulator (the text ink moves from row 22 to row 21 in 8 steps) and on real snapshots: the text of
`biker_sleep0.z80` and `biker_dark_area.z80` is entirely on row 21 (ink counts rows 20/21/22 = 0/229/0 and 0/204/0).

Durations, from the routines' T-states at 3.5 MHz: print and scroll in **0.42 s**, scroll out **0.40 s**. Pauses: `$FDC9` (64969) **2.46 s**, used before the first
line, after each line, and after the last line of an item message; "No items in this house" is line, 2.46 s, out; a crisp packet or fuel can line is in, three
calls of `$F12C` (61740, 0.15 s each), out. So an item message is 2.46 + 0.42 + 2.46 + 0.42 + 2.46 + 0.40 = **8.6 s** with the room on screen the whole time (and tea,
if the mum is there, runs after that last pause and before the line scrolls out: **0.84 s**, measured, so her visit is 9.47 s from the room to the end). The dark-area message is line 1 in, 0.45 s, out, line 2 in, 0.3 s, out. The two ending lines are shown in turn
and the last is held.

### In the port: HUD pictures, the walk and the scroll
`assets/hud_items.json` and `assets/colin_walk.bin` come from `tools/extract_assets.py`. `World.draw_hud` ORs the item pictures onto the bike picture
(`self.items & flag`), `World.park` starts a walk (`self.walk`, `WALK_PASSES` = 7 passes per frame, game paused) and the room and its
messages begin when it ends (`begin_room`), and the bar (`Bar`) scrolls each line up from the hidden row into the middle row over `SCROLL_PASSES` = 10 passes (0.4 s). `tools/check_port_items.py` checks all three.

### The dark area, in the original and in the port
The dark area is **only a drawing effect**: the tile check for the bike (`$EE75`) reads the real map, so walls in the dark still stop the bike.
- **Where:** map x <= 40 and y > 80 for tiles fetched as the view scrolls (the bottom-left, 41 x 47 tiles). The routine tests the column number *plus one*
  against 41, so the border is x = 40/41, not 41/42 as I first read it: found by running the original's own scroll routine in a simulator in all four
  directions (new cells at x <= 40 and y >= 81 are blank, x = 41 and y = 80 are not) and confirmed by the real snapshot `work/biker_dark_area.z80`,
  where every drawn tile at x <= 40 is blank and none at x >= 41 is (229 cells, 0 exceptions). The rule is in two tile-fetch routines: `$F0B4` (61620), used when the
  screen scrolls and a new row or column of the play area is filled, and `$F7B5` (63413), used when a vehicle's old cell is redrawn
  (`$F595` restores the background behind a moving vehicle). Without `$5B07` bit 0 (headlamp) both return the blank tile 205 for cells in the area.
  The vehicle one tests the map x itself against 41, so around a vehicle the border is x <= 41 (the scroll fetch is x <= 40).
- **The vehicle trail (decoded and in the port):** the vehicle loop at `$F42F` (62511) draws every vehicle that is on screen each frame, then restores
  the **two cells just behind it** from the map with `$F595` (62869): to the right of a vehicle going left (`$F551`, cells x+3, y and x+3, y+1), above one going
  down (`$F677`: x, y-1 and x+1, y-1), to the left of one going right (`$F5D0`: x-1, y and x-1, y+1), below one going up (`$F625`: x, y+2 and x+1, y+2).
  The tile comes from `$F6D3` -> `$F7B5`, so in the dark (map x <= 41, y >= 81, no headlamp) the restored cell is blank. A vehicle therefore
  **blanks every cell it passes over in the dark**, including cells that were still showing the map when you rode in. With the headlamp the cell gets its real tile
  again (so picking the lamp up and meeting a vehicle redraws the cells it passes). Checked with `tools/check_dark_trail.py`: the original's vehicle loop run
  in the simulator for every position and heading around the corner (422 trailing cells with and without the headlamp) gives the same blank cells as the port's
  `World.vehicle_trails()`, 0 differences. The port keeps the blank cells in the same per-cell mask as the scroll fetch (`dark_blank`).
- **Only newly exposed cells are fetched** (the screen is scrolled by `$E90D`, which fetches just the new row or column), so cells already on
  screen when you cross the border stay visible until they scroll off, and a row or column of blank appears at the edge as you ride in.
  If you pick up the headlamp inside, the blank cells stay blank until they scroll off and come back.
- **Vehicles and the bike are still drawn** in the dark (they are sprites over the map); what disappears is the map: roads, houses, pickups.
- **Markers:** tile 203 (going in) and 204 (coming out) at the border, e.g. (3,81), (4,81), (27,81), (28,81) in and (3,78), (4,78), (27,78), (28,78) out,
  and along x = 39 (in) and x = 42 (out). Without the headlamp, crossing 203 shows "You enter the dark area" / "You need a headlamp" once
  and sets the flag `$F005` to 0; crossing 204 shows "You leave the dark area" and sets it to 255. The flag is not reset by a new game.
  With the headlamp neither marker does anything.
- **In the port:** `World.fetch_blank` is the rule, `World.scroll_dark` keeps a per-cell blank flag for the 18 x 18 viewport and shifts it as the camera
  moves (new cells are fetched with the rule), `draw` fills flagged cells black, `hit_tile` does the two markers with `dark_flag`.
  `tools/check_port_items.py` checks it, including against the real dark-area snapshot.
  Picture: `work/port_dark_area.png` (no headlamp on the left, headlamp on the right).

### Speedometer needle (decoded)
`$D9BC` (55740) turns the speed counter (`$E517`: 10 = stopped, 0 = full speed) into a needle value `200 - 19 * counter` (200, 181 ... 0, stored
at `$DB91`) and calls `$DB3E` (56126). That routine erases the old needle and draws the new one, both by XOR, with the line routine at `$DCFB`
(56571), from a descriptor at `$DB8A` (56202) that it fills from a table of (length, step) pairs at `$DBD0` (56272). Needle values of 128 or more
(counters 0-3) take one branch (needle to the right of the pivot), the others another (up to vertical at counter 4, then to the left).
So the speedometer is not a smooth arc but 11 fixed lines.

The needle pixels were not worked out by hand: `tools/extract_assets.py` runs the original's own routine in the simulator for every counter and compares the
screen with the bare panel, writing `assets/hud_needle.json` (the port draws exactly those pixels). Tip of the needle by counter:

| counter | 10 (stopped) | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 (full speed) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tip (x, y) | 171,110 | 172,107 | 175,104 | 180,101 | 186,99 | 194,98 | 202,98 | 207,99 | 215,99 | 222,100 | 228,102 |

The shape is a fan from straight left, up to near vertical at counter 4, down again to the right, with the longest lines at the ends (32 and about 25 pixels).
Check: `tools/check_port_needle.py` (the port draws exactly the extracted pixels, and the real snapshots with counters 1, 4 and 10 show identical needles).

### The port against the original, frame by frame
`tools/compare_original.py` starts the real tape in the simulator (through the controls menu, keyboard) and the port (default mode) and gives both the same random
key presses; after every frame it compares the bike's tile, the view, speed counter, heading and sprite frame, SLEEP, score, items, clock, traffic seed and all
20 vehicles. Findings that fixed the port: the original's **start-up runs one frame (two passes) before the main loop**, so the traffic table of a new game is the
tape's table updated once (`assets/traffic.json` is now the menu snapshot's table, seed 0, and `new_game` runs that frame) and the clock starts at 41:01; the wait
between player moves starts at 10 ($D8C8); and **the heading bits of `$E519` follow the sprite frame during a turn** (every straight-on frame the turn passes sets
that heading), not only when the turn ends. With those the port and the original agree on every field for every frame compared.
Longer runs (450 frames, several scripts) then found two more: **a picked-up crisp packet is replaced by a new one at a random free spot** (`$EEF3` calls the
placement routine `$E0D1` after the message, with the same generator as the start-up placement, so there are always 30 packets) and **which way the sprite turns is
decided by the heading variable, not by the shortest way round**: the four handlers each rotate +1 (`$EDBA`) or -1 (`$EDDF`) frames depending on `$E519`
(to turn right: from down -1, from up +1, from left +1; up: from right -1, from left +1, from down +1; down: from left -1, from right +1, from up +1; left: from up -1,
from right +1, from down +1), and when the heading already is the asked-for way (a turn in progress, bit 5) the handler snaps to that frame. Bike at frame 7 having
come from facing left, asked to go right: it goes the long way round through 0, 1, 2, 3 to 4.

### Title screens and the Select Controls menu (decoded)
Before the game the tape shows **two loading screens** (the 6912-byte blocks 3 and 5: the KP Skips advert, then the Action Biker / M J CHILD title) and the game
then asks for the controls with the menu routine at `$DD77` (56695): it draws "Select Controls" and the five lines (`$DF20`, 57120; the original spells the last one
"CURSER") and waits for key 1-5 (row `$F7FE`, bits 0-4). The menu screen is ordinary screen memory, so the port stores it as `assets/screen_menu.bin` (with
`screen_ad.bin` and `screen_title.bin`, all written by `tools/extract_assets.py`).

The choice **patches the key-reading routine** `$DFA8` (57256), which tests five inputs in the order left, right, up, down, fire with
`LD A,row / IN A,($FE) / AND mask / CALL Z`: key 1 Keyboard writes the rows and masks of N, M, A, Z, Space; 2 Kempston changes the IN port to 31 and the CALLs to `CALL NZ`
(active high; masks 2, 1, 8, 4, 16 for left, right, up, down, fire); 3 Sinclair uses row `$EFFE` and the keys 6, 7, 9, 8, 0; 4 Fuller reads port 127 (masks 4, 8, 1, 2, 128);
5 Cursor patches nothing, because the code on the tape is already Cursor: 5 left, 8 right, 7 up, 6 down, Space. After the choice the game sets up the HUD
screen (`$DDA4`, 56996) and starts. In the port: `port/controls.py` holds the tables, `port/biker.py` shows the screens (each loading screen 4 s, any key skips) and
the menu, then starts the game; `tools/check_controls.py` runs the original's menu in the simulator for each key and compares the patched routine with the
tables (masks, rows, IN port, CALL Z / NZ), 5 of 5 identical.

### Sound: a beeper, four tunes and four short noises
The game has only the 48K beeper. Every noise goes through the game's routine `$D987` (55687), which calls the ROM's BEEP (`$03B5`) with
HL = pitch and DE = length in cycles: **frequency = 437500 / (HL + 30.125) Hz, length = DE / frequency seconds**, a square wave.

| Sound | Made by | HL, DE | What you hear |
|---|---|---|---|
| crash | `$D95D` (also `$EF9C`, water) | 16, 261 twice | two 27 ms beeps at 9.5 kHz, each followed by a 7 ms flash of the play area, then SLEEP and the score reprinted: **76 ms in all** (measured), on every pass of an overlap |
| fuel step | `$D9FA` | 75, 10 | a 2.4 ms click at 4.2 kHz for every step of the fuel gauge; a fuel can refills the tank at **2.8 ms a step** (measured), straight after its message has scrolled in |
| crisp packet | `$EECA` | 150, 16 | a 6.6 ms blip at 2.4 kHz |
| tick | `$E82F`, in the routine that draws the bike | 1, 1 | one 70 microsecond click **every pass** (the engine's putt-putt, about 19.5 per second) |
| oil skid | `$F139` (61753) | the tick | the bike is turned one frame and redrawn 16 times, **34.8 ms apart** (measured), so it spins through its 8 frames twice and ends where it began; 16 ticks |

The tune player `$FE08` (65032) takes B notes of 4 bytes (DE = length, HL = pitch), plays each with `$D987`, leaves 11 ms after each and 0.24 s after the last. Four
tunes (decoded from the snapshot, `assets/sounds.json`; `tools/export_sounds.py` writes them as WAV files):
- **start-up fanfare**, `$FE2F`, 5 notes (514, 575, 641, 514, 757 Hz), **3.0 s**, before every game, which waits for it;
- **end of game**, `$FE43`, 14 notes (262 to 411 Hz), **7.3 s**, after the messages of the eight o'clock, SLEEP and fuel endings, then a new game;
- **finish**, `$FE7B` (65147), 28 notes (328 to 575 Hz), **7.2 s**, after the two finish messages (`$E452` loads this table instead of the end tune);
- **leaving a house**, `$FEEB`, 19 notes (347 to 575 Hz), **4.1 s**, after the message when the visit ends and before the room is cleared.

The routines block, so the game stands still during each tune. In the port: `port/sound.py` builds every sound from these numbers (`samples`) and plays them
with pygame's mixer; `World(sound)` plays them at the matching moments and waits for the tunes (with no sound object the port is silent and does not wait).
`tools/check_port_sound.py` checks the synthesis against the ROM formula and every trigger. **The crash runs on every pass of an overlap and holds the game up
for its 76 ms** (the pass is 51 ms, so an overlap pass takes about 127 ms and the game stands still for the rest of each beep pair); the port does the same
(`World.crash()` plays the sound and owes 1.48 passes of waiting, `CRASH_SECONDS`), so SLEEP falls about 7.9 points a second while the bike sits on a vehicle.
The note timing (the gaps between notes) is still an estimate.

### Messages block the game; the pickup messages (measured, in the port)
Every message routine does its own scrolling and waiting, so **the whole game stands still (traffic, clock, fuel) until the message is over**; the port does the same
(`say(..., block=True)`). Times measured by running each handler in the simulator: the short pause `$F12C` is 148.6 ms (a "line" pause is three of them, 0.446 s).
- **Crisp packet** (`$EECA`): the blip and the packet removed at once; **the message "Packet of KP Skips" is only shown inside the dark area** (`$F005` = 0,
  where you cannot see the packet) and outside nothing is said and the 2 points come at once. Inside: in 0.42 s, three pauses, out 0.40 s, then the +2 (1.28 s in all).
- **Dark area in** (`$F006`): line 1 in, three pauses, out, line 2 in, **two** pauses, out (2.38 s). **Out** (`$F070`): in, one pause, out (0.97 s).
- **Fuel can** (`$F0D7`): "Fill up with petrol" in, the gauge refills (2.8 ms a step), three pauses, out (1.3 s with 6 steps missing).
- **Oil** (`$F0F9`): line 1 in, the bike spins (0.557 s), line 1 out, line 2 in, **SLEEP - 1 now** (1.79 s after the hit), one pause trio, out (2.64 s in all).
- **Crash flash** (`$D99B`): the play area's ink and paper are inverted after the first beep and back after the second, so it is inverted for about 34 ms (31-65 ms
  into each 76 ms crash). The port inverts the colours of the play area for that window.
Checks: `tools/check_port_items.py` (lengths, stand-still time, the delayed SLEEP and score, the spin, the flash) and `tools/check_port_sound.py`.

### Finish, the clock, game start and the end-of-game sequence (decoded)
- **Finish (`$E452`, 58450):** the main loop (`$E2AE`) jumps there each pass when `$5B07` bit 5 (passenger) is set and the player
  is exactly at tile (105,27), beside the airport. It adds **50** to the score, shows "You're here just in time" and
  "WELL DONE, COLIN" (`$E422`, 24 chars each), then runs the same sequence as every ending, with its own tune.
- **Every ending is the same sequence** (`$E3A3`, 58275, then `$E3E3`, 58339): **two messages**, then a tune, then a new game (`JP $E2B3`, 58035). The
  messages come in pairs because the routine prints the 24 characters at HL and then the 24 after them: eight o'clock = "It's eight o'clock" +
  "Time to get up Colin" (messages 0, 1); SLEEP 0 = "You've woken yourself up" + "You are so clumsy, Colin" (2, 3); out of fuel = "You've run
  out of fuel" + "Time to wake up colin" (4, 5); the finish = "You're here just in time" + "WELL DONE, COLIN". So the three messages that looked unlinked
  are simply the second lines. **Timeline, measured in the simulator** (identical for all four endings): line 1 scrolls in (0.42 s), 2.46 s pause,
  line 2 scrolls in and line 1 goes up off the top, 2.46 s pause, the bar scrolls empty (0.40 s), 2.46 s pause (8.6 s from the start), then the tune
  (`$FE08`; 7.3 s, 7.2 s for the finish), then `$DF67` clears the play area and the fuel gauge refills at once (about 1 ms a step, with the click),
  and the new game starts with its fanfare. Nothing moves meanwhile. The high score `$5B02` survives.
- **New game start-up (`$D858`):** the reset routine at `$DA97` (55959) sets SLEEP 50, score 0, **items `$5B07` = 0**, and
  the clock to hour 40, second 0. `$E1FD` (57597) then scatters the items (below), and the map's crisps and oil are cleared and
  placed again.
- **The clock** (`$DC04`, 56324, once per pass): `$DBD4` counts 5 passes = one tick; every tick `$DBD2` (seconds) +1; every
  12 ticks `$DBD3` (the hand) +1, wrapping at 60. When `$DBD2` wraps at 60 (every **300 passes**) SLEEP gains 5 (max 50) and the
  three fuel cans are put back. The day ends ("It's eight o'clock") when `$DBD3` = 40 and `$DBD2` = 0: that is **3600 passes**
  after the start (the port's idle test ended at 3596). A tank at full speed lasts 512 passes, so fuel cans matter.
- **Fuel cans:** fixed at (111,19), (103,51), (23,76), placed by `$E46D` (58477) at the start and every 300 passes.
- **Items are placed by a seeded generator, so a fresh load gives the same layout every time** (the user's observation, now
  proved). `$E0FD` clears the item bits of all 50 table entries, then picks 12 distinct houses with the generator at `$E292`:
  `seed = (seed + 1) * 75 mod 65537 - 1`, result = low byte, seed held at `$5B00` and set from the caller's return address when
  the game is entered (so it is constant per load and carries on from game to game in a session). In order the 12 houses get:
  passenger (bit 5; house 242 when the first draw is below 170), bit 2, headlamp (index below 38), wheels (bit 1), bit 3,
  bit 4, then six houses with bit 6. Index 49 (marker 254) has no door on the map, so one bit-6 house is unreachable.
  **Checked against the snapshot:** a search over all 65536 seeds finds twelve (`0x0`, `0x1356`, `0x33AF`, `0x44E9`, ...; they only
  differ by draws the placement throws away) that reproduce the level snapshot's house table, and each also reproduces all 30
  crisp packets and all 20 oil slicks exactly. The menu snapshot's table is the stale pre-game one.
- **Crisps and oil:** 30 packets and 20 oil slicks at generator-chosen spots (`$E239`: a random address `$99xx-$D7xx` whose cell is
  empty, nudged left if the cell to its right is taken and up a row if the one below is, then all four cells must be empty), then
  the three fuel cans. The port uses the same generator and reproduces all 212 pickup cells of the real first game.
- Still open: what `$5B07` bits 4 and 6 do (they are given by 1 and 6 houses), the item graphics in the houses, and
  the real pass rate.

### House interiors (`$F80C`, room drawn by `$FA8E`, items by `$FB31`): furniture assets (extracted to `assets/interior.json`)
Every house shows the **same kind of room**, built from the table entry: an 18x18-char black viewport, a 12x12 floor patch at
(4,4) in the house's colour (low 3 bits of byte 2 as paper, white ink), then each item present drawn over it, then Colin
(a 2x4 white figure at (14,8), record at `$F89F`).
- **20 item records at `$6626`, 7 bytes each:** column, `24 - row` (the ROM's screen-row convention), graphics pointer, width,
  height, ink colour. The graphics are `width * height` chars, row-major, ORed over the floor; only the ink of the cell
  changes, so the paper stays the floor colour. Slots 0-3 are 4x2 pieces at the four edges (rugs or window frames), 4-12 are
  furniture (3x3, 3x4, 6x3, 3x5; they look like chairs, a settee, a TV and so on, drawn at an angle), 13-19 are the special items.
- The special items all sit at the room's centre (9,9): 13 = item 4, 14 = **the passenger (a person with a drink)**, 15 = item 6,
  16 = headlamp, 17 = **a wheel**, 18 and 19 the two water items. Only slots 13-19 change between games; slots 0-12 and the colour
  belong to the house for good, so **each house always looks the same** and **differs from the others**.
- The port draws this when you park (`World.interior`), for two seconds, then carries on.

### The screen and the HUD (assets: `hud.bin`, `font.bin`)
- **The play area is 18 x 18 chars at char (1,1)** (pixels 8-151 x 8-151), not 18 x 16 as an earlier note said; the routine at
  `$DF67` (57191) fills its attributes and clears its 144 pixel lines. The camera clamp is 128 - 18 = 110 on both axes.
- Everything outside it is drawn once into screen memory: red border, title box, magenta panel (HIGH / SCORE / SLEEP), speedometer
  dial, bike picture, and the bottom row (clock icon at chars 1-3, blue message bar at chars 4-27, FUEL box at chars 28-30).
  `assets/hud.bin` is that screen with the live parts blanked (the clock hands, needle and fuel marker are moving parts, removed
  by taking the per-byte majority over all gameplay snapshots).
- **All text is the ROM font** (`$3D00`, copied to `assets/font.bin`): the text routine at `$DEFE` (57086) draws 8 pixel lines
  per char straight to screen addresses. HIGH digits at (208,44) (`$44BA`), SCORE (208,60) (`$44FA`), SLEEP (208,76) (`$4C3A`, 2
  digits); each is a 4-digit zero-padded number converted by `$E05A`. The message row is chars (4..27, 22), 24 characters, with
  a scroll effect in `$E008` (57352) that the port skips.
- **Fuel gauge:** a one-pixel line, 18 chars-and-bits wide (`$0F`, `$FF`, `$FC` XORed over chars 28-30), that drops one pixel
  per step from y = 164 (full) to 181 (empty). Clock: two hands, the fast one is `$DBD2` and the slow one `$DBD3`, 60 positions
  each; hour hand at 40 = eight o'clock. The speedometer needle is a line from a pivot at (203,110): at rest it lies 32 pixels along the
  base of the dial to the left (so it is baked into every stationary snapshot and `extract_assets.py` removes it from `hud.bin`),
  and the snapshot with the bike moving shows it near vertical. **The 11 needle positions are decoded** (next section); the clock hand
  shapes are still approximated.
- The high score follows the score as it passes it (`$E0B1`).

### Vehicle sprites: `$734C`, 3 types x 4 headings, 24 x 16 pixels
Found by reading the draw routine rather than searching for pixels: the routine at `$F4B3` builds the sprite
address from the flags byte as **`$734C + 192 * type + 48 * heading`**. A sprite is six 8x8 chars (8 bytes each),
3 wide and 2 tall, stored row-major, so 48 bytes per heading and 192 per type. Types 0-2 fill `$734C-$758B`,
ending exactly where the traffic table starts; type 3 would overlap it, so only three types exist.
- Verified on three vehicles in the traffic snapshot: all six chars matched the screen for each.
- Type 0 is a boxy van or estate car, type 1 a motorbike with rider, type 2 a low saloon car. Left and right are
  side views, down and up are front and rear views. Picture: `work/vehicle_sprites.png` (local).
- This explains the earlier puzzle: the other riders did not match our 16x16 player frames because their sprites
  are 24 pixels wide (3 chars), not 16.

### Traffic movement (`$F1CC`, decoded and verified by simulation)
The 20 vehicles are updated once per frame (the routine at `$F1CC` is called from `$D899` before the player's two passes), so
each vehicle moves at most **one tile per frame**, whether or not it is on screen. For each entry (x, y, flags):
- **Move:** by heading (flags bits 7-6) test the two tiles on the leading edge: left (x-1, y) and (x-1, y+1); right (x+3, y)
  and (x+3, y+1); down (x, y+2) and (x+1, y+2); up (x, y-1) and (x+1, y-1). If both are free the vehicle steps one tile.
  Horizontal vehicles are 3 tiles long and vertical ones 2 wide.
- **Free tile for a vehicle** (`$F796`, 63382): id 0, every id from 190 up (so vehicles drive over crisps, oil, markers), and id
  69 half the time (a random gate: probably junctions). Ids 1-189 (except 69) block: buildings, grass, fences, water, lamp posts.
- **When blocked** it turns (`$F2D2`, 62162) using one byte `r` from the traffic generator. The Z80 test `CP k / JP M` is a
  *signed* test, which makes three bins: `r` 85-212 (about 50%) the main turn, `r` 42-84 (about 17%) a U-turn, `r` 0-41 or
  213-255 (about 33%) the other turn.

  | Heading | main turn (50%) | U-turn (17%) | other turn (33%) |
  |---|---|---|---|
  | left | up | right | down |
  | right | down | left | up |
  | down | right | up | left |
  | up | left | down | right |

  A turn only takes effect if the tiles in the new direction are free (left and right check them; up and down do not), and
  turning between horizontal and vertical shifts the vehicle's x by one so its footprint stays on the road.
- **Generator** (`$F2B8`, seed at `$F2B7`): `seed' = (L - H)` of `254 * (seed + 1)`, minus 1 when there is no borrow. Each turn
  decision consumes one value, and each tile-69 test one more.
- **Start positions** are not generated: the table is plain data in the game (`$758C`, 20 entries) and just carries on from where
  the vehicles were; a new game does not reset it. The controls-menu snapshot holds the original start table.
- **Verified** (`tools/traffic_sim.py`): one update of the menu snapshot's table reproduces all 20 entries of the early level
  snapshot (including one vehicle that turned from up to right) and ends on the same seed, 253. And in all 160 samples
  (20 vehicles x 8 snapshots) no vehicle's footprint is on a blocked tile. Flag bit 3 is never read by this code and was
  zero in every sample.
- Vehicles do not look at the player here; the player's own routine (`$D8F9`) tests the overlap and costs a SLEEP point.
- **In the port:** `port/traffic.py` holds this model (`Traffic`), `port/biker.py` calls `update()` on every other pass (the original
  runs the traffic once per frame and the player twice) and `hits()` every pass, and `tools/check_port_traffic.py` checks it
  headlessly: the port's first update equals two model updates from the menu table, no vehicle ever stands on a blocked tile in
  3,000 passes, and a vehicle on the player costs a SLEEP point. The traffic table is not reset by a new game, as in the original.

### SLEEP counter: `$5B04`, and the game loop
The number shown after SLEEP is a plain binary byte at `$5B04`: 50 at the start, 28 in one snapshot, 3 and 0 in
the last two. **SLEEP falls when the bike hits another vehicle or an oil slick** (the user's observation,
confirmed by the code): the routine at `$D95D` (55645) is entered when the player overlaps a traffic table
vehicle (the collision test at `$D8F9`) and from the water handler at `$EF9C` (the oil slick handler has its own SLEEP decrement). It beeps through the ROM, flashes
the play area, does `LD A,($5B04) / AND A / RET Z / DEC A / LD ($5B04),A` and calls `$E08D`, which reprints
the score, SLEEP and high score.

When SLEEP is 0 the text "You've woken yourself up" appears in the blue bar at the bottom (seen in the
`sleep 0` snapshot). It comes from the **main game loop at `$E2AE` (58030)**, which saves the return address
at `$5B00`, runs the start-up routine at `$D858`, then loops: it calls the frame routine at `$D899`
(movement, traffic, drawing) and checks the end-of-game conditions each pass:

| Condition | Message |
|---|---|
| `$5B04` (SLEEP) = 0 | "You've woken yourself up" (message 2, routine `$E39B`) |
| clock bytes `$DBD3` = 40 and `$DBD2` = 0 | "It's eight o'clock" (message 0, routine `$E3A0`) |
| fuel state `$E290`,`$E28F` = 2,3 | "You've run out of fuel" (message 4, entry `$E396`) |
| player on tile (105, 27) with bit 5 of `$5B07` set | the finish at `$E452`: score +50, "You're here just in time" and "WELL DONE, COLIN" |

The six 24-character messages are at `$E306` (`0` It's eight o'clock, `1` Time to get up Colin, `2` You've
woken yourself up, `3` You are so clumsy, Colin, `4` You've run out of fuel, `5` Time to wake up colin). Messages
are shown in pairs, 0+1, 2+3 and 4+5 (see the finish section). The clock
(`$DBD2`/`$DBD3`) and the fuel gauge (`$E28F`/`$E290`) are decoded in the sections around this one.

### The "dog" in the bottom right is the top of the Baker's chimney
In the traffic snapshot there is a small red shape in the row just below the frame at the bottom right. Its
two 8x8 cells are the bytes at `$8C08` and `$8C10`, which are chars 2 and 3 of the Baker's block
(building id 10, block start `$8BF8`), and the map has a Baker footprint at (62,117), the next row of
buildings below the viewport. So it is the top of the Baker's shop, drawn one row past the frame. The user
identified the shape as the top of the bakery's chimney (at first I took it for a figure on the roof); it is red
in the attribute row `00 00 02 02 00 00`. It is not a moving animal and not a traffic-table entry. The map
holds several Baker shops, at (56,70), (62,117), (84,86), (101,54) and (109,37).

### Renders (local only, `work/*.png` is gitignored)
`tools/render_map.py SNAPSHOT OUT.png [--colour] [--attr-snapshot MENU.z80] [--blocks SHEET.png]`
draws the whole town (a walled block in the middle holding two houses). Use the menu snapshot for the
colour blocks so ids 4-8 are not blank. `map_render.png` is the plain version; `map_render_colour.png`
has everything in colour; `blocks_80b8.png` is the sheet of 19 buildings.

## Other changed regions (identified)
Every byte that changes between the Select Controls menu and the start of a game was listed (both moments made in the simulator by
`tools/original.py`), and the code that writes each one found by running the start-up with a write trace.

| Range | What it is |
|---|---|
| `$DB8A` (7 bytes) | the speedometer needle's line descriptor, built by `$DB3E` |
| `$DD48` (7 bytes) | the line routine's (`$DCFB`) working copy of the line being drawn, copied by `$DB35` from the needle's descriptor or a clock hand's (`$DBD6`, `$DBDD`): that is why it matched `$DB8A` |
| `$FFDD-$FFFE` | the machine stack: the game never sets SP, so it stays where the loader left it, just below `$FFFF` |
| `$5DE9-$5FA0` (the 418 bytes that differ) | a saved copy of the HUD's bike picture, 40 pixel lines of 11 bytes from screen `$48D4` (x 160-247, y 112-151): `$E493` saves it at every start-up before any equipment picture is ORed on, and `$E4AF` puts it back at the end of a game |
| `$DFAE-$DFCD` | the control scheme: ports and masks the Select Controls menu patches into `$DFA8` (see `port/controls.py`) |
| `$E277-$E28E` | the item placement's (`$E0FD`) list of the 12 houses drawn; `$E28F`/`$E290` after it are the fuel gauge |
| `$F0B2`/`$F0B3` | the screen cell of the tile being fetched during a scroll; the dark-area test (`$F0C5`, `$F0D8`) reads it |
| `$F29B`/`$F29C` | traffic: the map (x, y) of the cell a vehicle is about to enter, tested by `$F2AD` |
| `$F46D-$F475` | traffic drawing's working variables (the disassembly called them "unused"): the entry pointer, the count, the visibility bits of the cell (`$F476`), the row and column loop counters, the cell's screen column and row |
| `$5B00`/`$5B01` | the item generator's seed (0 after a fresh load), `$5B04` SLEEP, `$5B07` the items |

The variables the port depends on (bike tile `$E51A`, view `$E90B`, speed counter `$E517`, heading `$E519`, sprite frame `$E734`, SLEEP,
score, items, clock `$DBD2`/`$DBD3`, fuel accumulator `$D9E2`, traffic table `$758C` and seed `$F2B7`) are read from the original's memory
after every frame by `tools/compare_original.py` and agree with the port.

(`$758C` is the traffic table, `$787F-$7917` the building colour blocks for ids 4-8, `$E517`/`$E518` the speed
counter and saved keys, `$5B04` SLEEP, `$5B05`/`$5B02` score and high score.)

## Next steps
1. ~~What `$5B07` bit 4 and bit 6 do~~ done: the Turbo kit does nothing; the friend's mum is a 600-pass tea break.
2. ~~Traffic in the port~~ done: `port/traffic.py` is the model of `$F1CC` and the port runs it (one update per two passes, crash = SLEEP -1 on overlap). Still open: the real speed of a pass, the exact crash beep and flash, and whether vehicles ever respawn.
   (The dark area is in the port and checked against a real snapshot taken inside it.)
   (The camera dead zone is decoded and in the port, checked against the original's move handlers.)
5. Which houses hold the items in a *fresh* game is solved by the seeded generator; check the port against more snapshots.

## Reproducing on another PC
The private repository holds everything: the original game files (`Action-Biker_ZX-Spectrum_EN/`), the ZEsarUX snapshots in
`work/*.z80` (menu, start, 5 tiles south, left-facing with traffic, traffic with the bakery chimney, SLEEP 3 and SLEEP 0, and two level
snapshots), the flat dumps and `.skool` files, and the pictures; it is copyrighted data, so that repository stays private. The public
copy (`tools/make_public.py`) holds none of it, and everything below works from your own copy of the game instead:

1. `git clone`, then `python -m venv .venv` and `pip install -r requirements.txt` (see note 01).
2. `python tools/extract_assets.py [GAME]` loads your copy in the simulator and rebuilds `assets/` (and `work/_tmp/menu.z80`,
   `level.z80`, `original.z80` for the checks); `python port/biker.py` runs the pygame port.
3. Regenerate the disassembly from a snapshot: `python .venv/Scripts/sna2skool.py -c work/biker.ctl work/_tmp/level.z80 > work/biker.skool`
   (or `work/biker_sleep0.z80` in the private repository).
4. Redraw pictures with `tools/render_map.py` and `tools/tap_screens.py`.

ZEsarUX itself is not in the repo (it is a third-party download); the snapshots load into it.
