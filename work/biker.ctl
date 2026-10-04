@ 16384 start
@ 16384 org
b 16384
c 16470
b 16472
c 16595
b 16601
c 16726
b 16728
c 16758
b 16762
c 16790
b 16794
c 16862
b 16870
t 17035
b 17039
t 17130
b 17136
c 17363
b 17369
t 17388
b 17392
c 17494
b 17496
c 17526
b 17535
c 17619
b 17625
c 17647
b 17656
c 17750
b 17752
t 17803
b 17806
c 17875
b 17881
t 17899
b 17904
c 18006
b 18008
c 18038
b 18043
t 18059
b 18062
c 18099
b 18105
t 18156
b 18160
c 18355
b 18361
c 18419
b 18424
c 18451
b 18456
t 18792
b 18796
c 19091
b 19110
t 19176
b 19179
c 19219
b 19224
t 19242
b 19245
c 19251
b 19256
t 19433
b 19436
t 19944
b 19948
t 20072
b 20076
t 20077
b 20080
t 20200
b 20204
c 20789
b 20798
t 21045
b 21048
t 21557
b 21560
; --- Score, high score and SLEEP ($5B00-$5B0C) ---
; $5B04 is the number shown after SLEEP: 50 at the start, falling by 1 each time the bike hits another vehicle or
; an oil slick (routine at $D95D); at 0 the game ends with "You've woken yourself up". $5B05 and $5B02 are the
; score and the high score as 16-bit binary values (checked: a snapshot showing HIGH 0016 SCORE 0016 held 16 in
; both). $5B00 holds the return address saved when the game loop starts ($5D06).
b 23296 Game variables: return address, high score, SLEEP, score
D 23296 $5B00 saved return address; $5B02 high score; $5B04 SLEEP; $5B05 score; $5B07 flags (bit 5 is tested by the game loop together with the player tile (105,27)). The rest is unknown.
N 23298 High score (16-bit).
N 23300 SLEEP counter, plain binary. 0 ends the game.
N 23301 Score (16-bit binary; the ASCII digits at $E04B are only a temporary buffer for printing).
B 23296,2,2
B 23298,2,2
B 23300,1,1
B 23301,2,2
B 23303,1,1
B 23304,5,1
c 23309
b 23311
c 23439
b 23447
c 23470
b 23480
t 23491
b 23494
c 23527
b 23536
; --- Player sprite, set 2: 8 frames x 32 bytes at $5C09-$5D08 ---
; Same format as set 1. Frames 2 ($5C49) and 6 ($5CC9) are byte-identical to set 1 frames 2 and 6;
; the other six are close (about 235-241 of 256 pixels equal) but not the same, perhaps in-between angles.
b 23561 Player (bike) sprite frames, set 2 (8 x 32 bytes)
D 23561 Frame n is at $5C09 + 32*n. Relation to set 1 not yet established.
B 23561,256,8
; --- House room pictures: Martin, the friend's mum and Colin standing ---
; Sprite descriptors are 7 bytes: column, 24 - row, pointer, width, height, ink (the item records at $FB9C end with one; Colin's
; is at $F89F). The room items are drawn at the room's centre; Colin stands at (14,8), white.
b 23817 Martin (2 x 4 chars, white ink 7)
B 23817,64,8
b 23881 The friend's mum (3 x 4 chars, yellow ink 6)
B 23881,96,8
b 23977 Colin standing in the room (2 x 4 chars, white ink 7)
B 23977,64,8
b 24041 Saved copy of the HUD's bike picture: 40 pixel lines of 11 bytes from screen $48D4 (x 160-247, y 112-151). $E493 saves it at every start-up, before any equipment picture is ORed on; $E4AF puts it back at the end of a game
; --- Equipment pictures ORed onto the HUD picture of the bike when an item is found ---
; Each is a sprite descriptor (see above): headlamp $6056 3x3 at HUD cell (20,14), new tyres $609E 3x3 at (28,16), Turbo DIY kit
; $60E6 2x1 at (29,16), snorkel $60F6 2x2 at (29,14), periscope $6156 2x2 at (29,17). Black ink on the white panel. Seen in a snapshot taken
; with the new tyres: the 9 HUD cells at (28..30, 16..18) equal the old cells ORed with this graphic.
b 24662 HUD picture: headlamp, a beam of light in front of the bike (3 x 3 chars)
B 24662,72,8
b 24734 HUD picture: new tyres, fatter wheels (3 x 3 chars)
B 24734,72,8
b 24806 HUD picture: Turbo DIY kit, a small badge (2 x 1 chars)
B 24806,16,8
b 24822 HUD picture: snorkel, a pipe at the top right (2 x 2 chars)
B 24822,32,8
b 24854 Unknown (64 bytes)
b 24918 HUD picture: periscope, a pipe at the bottom right (2 x 2 chars)
B 24918,32,8
b 24950
c 25267
b 25276
t 25431
b 25435
t 25985
b 25988
t 26104
b 26107
t 27721
b 27728
t 27864
b 27871
t 29032
; --- Colin walking into a house: 5 frames x 32 bytes at $72AC-$734B (2 x 2 chars, top row first) ---
b 29356 Colin walking in, 5 frames of 32 bytes (see $F860)
B 29356,160,32
; --- Other vehicles' sprites: 3 types x 4 headings x 48 bytes ($734C-$758B) ---
; Each sprite is 24 x 16 pixels = six 8x8 chars, 3 wide and 2 tall, stored row-major (8 bytes per char). The routine at
; $F4B3 (62643) works out the address from the traffic table flags: $734C + 192*type + 48*heading, with type =
; flags bits 5-4 (0 van, 1 motorbike, 2 saloon car) and heading = flags bits 7-6 (0 left, 1 down, 2 right,
; 3 up). Verified: all six chars matched the screen for a car, a red bike and a cyan bike. The colour is the
; low three bits of the flags (ink).
b 29516 Vehicle sprites (12 x 48 bytes)
D 29516 Sprite for flags F is at $734C + 192*((F>>4)&3) + 48*(F>>6). Types 0-2 only: type 3 would overlap the traffic table at $758C.
B 29516,576,8
; --- Traffic table: 20 other road users, 3 bytes each: x, y, flags ---
; Walked by the routines at $D8F9 (collision with the player), $F1CC (movement) and $F42F (drawing). Bytes 0 and
; 1 are the map tile (x, y) of the vehicle's top-left char. The flags byte: bits 7-6 = heading (0 left,
; 1 down, 2 right, 3 up, as for the player), bits 5-4 = vehicle type (0 van, 1 motorbike, 2 saloon car;
; see the sprite block at $734C), bits 2-0 = ink colour (5 cyan, 2 red, 3 magenta seen). Bit 3 is not yet
; understood. Verified on three vehicles; the sprite address formula matched all of them.
b 30092 Traffic table (20 x 3 bytes: x, y, flags)
B 30092,60,3
; --- Player sprite, set 1: 10 frames x 32 bytes (16x16 px) at $75C8-$7707 ---
; Each frame is four 8x8 chars in the order top-left, top-right, bottom-left, bottom-right (8 bytes each,
; MSB = leftmost pixel). Found by diffing the screen against the rendered map: the only cells that did not
; match were a 2x2 block at the centre of the play area, and its 32 bytes were then searched for in RAM.
; Drawn on screen with attribute 47 (bright white ink on black). Frame 2 ($7608) is the bike seen from
; above, riding straight; the others lean and turn (frames 0, 8 and 9 show the wheels from the side).
b 30152 Player (bike) sprite frames, set 1 (10 x 32 bytes)
D 30152 Frame n is at $75C8 + 32*n. Frame 2 ($7608) matched the player on screen byte for byte. Replaces the auto-generated entries that were here (several were mis-labelled as code).
B 30152,320,8
b 30472 Two bytes before the unknown 32 bytes
; --- Tile colour table: one Spectrum attribute byte per tile id, at $770A + id ---
; Verified: all 38 tile ids visible in the level snapshot show exactly the attribute at this table
; position (38 of 38 matches). Only ids 32-201 are tile ids; the 32 bytes below $772A look like
; pixel data (not attributes) and belong to something else.
b 30474 Unknown, 32 bytes (looks like pixel data)
B 30474,32,8
b 30506 Tile colour table for tile ids 32-201
D 30506 Attribute byte (flash/bright/paper/ink) for tile id t is at $770A + t, i.e. this block starts at id 32.
B 30506,170,10
b 30676 Unused (zero) before the building colour blocks
; --- Building colour (attribute) blocks: ids 1..19, 36 bytes each ---
; Building id t's Spectrum attribute bytes (flash/bright/paper/ink), one per char cell of its 6x6
; footprint, row-major, are at $77E5 + 36*t. Same house graphic, three colour schemes: id 1 yellow
; walls (30), id 2 magenta (18), id 3 cyan (28), all with roof 50 and base 20; id 4 white (38).
; In the menu snapshot every block is complete. In the level snapshot ids 4-8 are partly or wholly
; zero (black on black = invisible) - the game appears to hide those buildings at the start.
; Verified: id 16 = the two houses on screen; id 1 = the visible edge of the yellow house.
b 30729 Building colour blocks (19 x 36 bytes)
D 30729 Attribute block for building id t is at $77E5 + 36*t, as 6 rows of 6 attribute bytes.
B 30729,684,6
b 31413 Unused (zero)
; --- Tile graphics: single 8x8 chars (8 bytes each), tile ids 32..201 ---
; Map id t (t >= 32) is drawn from $79E0 + 8*t. Ids 0-19 are not tiles (0 = blank, 1-19 =
; buildings) and 20-31 are unused, so the bytes under tile ids 0-31 are the colour blocks above.
; Verified against the on-screen play area (every tile id checked matches byte for byte).
; Last non-zero byte is $802D = tile 201. See notes/03-level-map.md.
b 31456 Tile graphics (8 bytes per tile, 1bpp, MSB = leftmost pixel)
D 31456 Indexed by the level map at $9858: tile t is at $79E0 + 8*t (this block starts at tile 32). Each tile is eight pixel rows.
B 31456,1360,8
N 32672 Tile ids 184-189: a red propeller aeroplane, a 3x2 object laid out 184 185 186 / 187 188 189. One in the map, at (116..118, 30..31), parked beside the airport terminal (building id 17 at (109,24)). Colour red (42) per the tile colour table.
N 32720 Tile ids 190-193: crisp packet, a yellow 2x2 object (a b / c d). 30 are placed in the map when a game starts; none exist in the controls-menu snapshot.
N 32752 Tile ids 194-197: oil slick, a blue 2x2 object. 20 placed at game start.
N 32784 Tile ids 198-201: fuel can, a red 2x2 object. 3 placed at game start.
b 32816 Unused (zero) before the building graphics
D 32816 Tile ids 203 and 204 point here (12 map cells each, blank graphics): perhaps invisible markers such as checkpoints or spawn points. Not yet identified.
; --- Building graphics: 19 blocks of 6 x 6 chars (288 bytes each), ids 1..19 ---
; Building id t (1..19) is the 36 consecutive 8-byte chars at $80B8 + 288*t, row-major, 6 chars per
; row. In the level map every region of id t is exactly a 6x6 rectangle; its cell (r,c) from the
; rectangle's top-left shows char 6*r+c of the block. Verified on 4 ids and then by rendering the
; whole map (tools/render_map.py). From the block sheet: 1-5 house (colour variants), 6 half-timbered
; house, 7 cafe, 8 police, 9 bistro, 10 baker, 11 butcher, 12 church, 13 fire station, 14 school,
; 15 house with fence, 16 house, 17 airport terminal (control tower and flags), 18 works, 19 petrol station.
b 33240 Building graphics (19 blocks x 288 bytes)
D 33240 Block for map id t starts at $80B8 + 288*t (id 0 has no block; its slot overlaps unused tile space). Each block is 6x6 chars in row-major order, 8 bytes per char.
B 33240,5472,8
b 38712 Zero padding before the level map
; --- Level map (128 x 128 tiles, 1 byte per tile, row-major, 128-byte stride) ---
; Found by diffing two gameplay snapshots: 2x2 blocks of tile ids BE BF / C0 C1 appear and
; vanish at addresses exactly $80 apart. Extent is exact: it starts at $9858 (216 zero bytes
; of padding precede it from $9780) and ends at $D857 = 128 rows x 128 = $4000 bytes; the very
; next byte, $D858, is code (CD 77 DD = CALL $DD77). Note rows are NOT aligned to $xx00/$xx80:
; they begin at addresses = $58 mod $80. Drawn as a 128-wide image: work/map_level.png.
b 39000 Level map
D 39000 128x128 tile map, one byte per tile, row-major (128 bytes per row, first row at $9858). Tile ids index the scenery graphics at $5B00+ (not yet confirmed). Replaces the auto-generated b/t/c entries that the old control file had here.
B 39000,16384,128
c 55384 Game start setup
D 55384 Sets the player to map (59,100), heading $C0, sprite frame $7608 and the viewport to (51,111), then scrolls the viewport 19 rows to (51,92). The coordinates it stores are what identified the variables at $E51A, $E90B and $E734.
c 55496
c 55544
c 55545
c 55645 Player hits something: beep, flash, SLEEP minus 1
D 55645 Entered from the collision test at $D8F9 when the player overlaps a traffic table vehicle (and from the routine at $EF9F, probably for an oil slick). Beeps via ROM 949, flashes the play area attributes (routine at $D99B), then decrements SLEEP at $5B04 if it is not already 0 and calls the routine at $E08D. The user confirms SLEEP falls when the bike hits another vehicle or an oil slick. Runs on every pass of an overlap and takes 76 ms (measured): beep 27 ms, flash 7 ms, beep 27 ms, flash 7 ms, then SLEEP and the score (7 ms).
c 55687 Beep: call the ROM's BEEP with HL = pitch, DE = length ($D987)
D 55687 Saves the border colour variable, sets it to 8, calls the ROM BEEP at $03B5 (949) and restores it. The ROM's rule: frequency = 437500 / (HL + 30.125) Hz, length = DE / frequency seconds, a square wave. Used by the crash routine ($D95D: HL 16, DE 261, twice), the fuel gauge step ($D9FA: 75, 10), a crisp packet ($EECA: 150, 16), the click when the bike is drawn ($E82F: 1, 1) and the tune player.
c 55707
c 55740 Set the needle value from the speed and draw it
D 55740 value = 200 - 19 * $E517 (the speed counter), stored at $DB91; then calls $DB3E.
s 55777
c 55779
c 55802
c 55856
c 55879
c 55919
c 55959
c 56116
c 56117
c 56126 Draw the speedometer needle ($DB3E)
D 56126 Not a sound routine (an earlier note called it one): erases the old needle and draws the new one (XOR) as a line, from a descriptor at $DB8A (56202) built from the (length, step) table at $DBD0 (56272) and the value at $DB91 (56209), which $D9BC (55740) sets to 200 - 19 * speed counter. Values of 128 or more (counters 0-3) point right, the others up to vertical (counter 4) and left. The 11 resulting pixel sets are in assets/hud_needle.json (tools/extract_needle.py).
c 56167
s 56202 Needle line descriptor ($DB8A)
c 56211
b 56246
c 56313
c 56334
c 56337
c 56359
c 56420
c 56445
c 56456
c 56467
c 56480
c 56491
c 56502
c 56571 Draw (XOR) a line from a descriptor ($DCFB)
c 56595
c 56618
s 56648 The line routine's working copy of the line being drawn (7 bytes, copied from a descriptor such as the needle's at $DB8A or a clock hand's at $DBD6/$DBDD, by $DB35)
c 56650
c 56695 Select Controls menu ($DD77): draws it, waits for key 1-5
c 56804 Choice 1, Keyboard: patch $DFA8 for N M A Z Space
c 56851 Choice 2, Kempston: IN port 31, CALL NZ
c 56918 Choice 3, Sinclair: keys 6 7 9 8 0
c 56952 Choice 4, Fuller: IN port 127
c 57073
c 57086
t 57120
c 57191
c 57234
c 57242
c 57253
b 57255 Direction input (set by the routine at $DFA8)
D 57255 One bit per direction: bit 0 = left, bit 1 = right, bit 2 = up, bit 3 = down (read by the movement dispatcher at $E51E).
B 57255,1,1
c 57256 Read the keys or joystick into $DFA7 ($DFA8)
c 57307
c 57316
c 57325
c 57334
c 57343
c 57352 Print one 24-character message line in the bar
D 57352 Hides row 22 of the bar (attribute $49, blue ink on blue paper), prints the line (HL) there with the routine at $DEFE, then falls into the scroll routine at $E01F (57375), which shifts the pixel lines of rows 21-22 up one at a time (8 steps with a delay between), so the text scrolls up from the hidden row into the middle row (row 21), where it stays, pushing any previous line off the top. Only row 21 ever shows text; row 20 is unused. Print and scroll in take 0.42 s, a scroll out ($E01F alone, called at the end of every message) 0.40 s.
; --- Score ---
b 57419 Score digits (ASCII)
D 57419 Five ASCII digits, most significant first. Holds $30 x5 at game start and became '00016' ($30 $30 $30 $31 $36) when the on-screen score read 0016. Zero in the menu snapshot, so it is initialised when a game starts. The code at $E050 looks like a number-to-decimal routine (LD A,'0' / LD DE,10000 ...).
B 57419,5,5
c 57424
c 57432
c 57434
c 57485 Update the score, SLEEP and high score on the screen
D 57485 Prints the 16-bit score at $5B05 as 4 digits, the SLEEP byte at $5B04 as 2 digits, then if the score is above the high score at $5B02 copies it there and prints that too. Called after every hit (see $D95D) and after scoring.
c 57553
c 57575
c 57597
c 57646
c 57774
c 57800
c 57808
c 57825
c 57839
c 57853
c 57886
c 57891
c 57913
c 57940
c 57942
s 57969
c 58001
c 58030 Main game loop
D 58030 Saves the caller's return address at $5B00, runs the start-up routine at $D858, then loops calling the frame routine at $D899 (55449). Each pass it checks the end-of-game conditions: the player on tile (105,27) with bit 5 of $5B07 set jumps to the routine at $E452; SLEEP ($5B04) = 0 gives "You've woken yourself up"; the clock bytes $DBD2/$DBD3 = 0 and 40 give "It's eight o'clock"; the fuel state at $E28F/$E290 = (3,2) gives "You've run out of fuel".
c 58109 Clock check
D 58109 Reached when $DBD3 = 40: if $DBD2 = 0 the message "It's eight o'clock" is shown, otherwise the loop carries on.
t 58118 Game messages: 6 x 24 characters
D 58118 The text shown in the blue bar at the bottom of the screen when the game ends. Each message is exactly 24 characters, padded with spaces. In order: 0 "It's eight o'clock" ($E306), 1 "Time to get up Colin" ($E31E), 2 "You've woken yourself up" ($E336), 3 "You are so clumsy, Colin" ($E34E), 4 "You've run out of fuel" ($E366), 5 "Time to wake up colin" ($E37E). They are shown in pairs by the routine at $E3A3: 0 then 1 (eight o'clock), 2 then 3 (SLEEP 0), 4 then 5 (out of fuel); the finish uses the two lines at $E422 the same way.
T 58118,144,24
c 58260 Out of fuel message (entry $E396 sets HL to message 4)
c 58267 Show message 2: you've woken yourself up
D 58267 SLEEP reached 0.
c 58272 Show message 0: it's eight o'clock
D 58272 Also the common routine that draws a 24-character message (HL) into the bar at the bottom of the screen (entry $E3A3).
c 58339
c 58385
t 58402
b 58451
c 58453
c 58477
c 58500
c 58515 Save the HUD's bike picture to $5DE9 (40 lines x 11 bytes from screen $48D4), then the reset at $DA97
c 58543 Put the HUD's bike picture back from $5DE9 (the end of a game: the equipment pictures go)
c 58568
c 58593
s 58598
c 58600
c 58624
c 58642
; --- Player state variables ---
; Found by diffing snapshots and confirmed with snapshots before and after riding 6 tiles south.
b 58646 Player state
D 58646 $E519 bits 7-6 look like the heading ($C0 at the start, $40 after riding south; the code at $E736 does LD A,($E519) / AND $C0). $E51A,$E51B = the player's map tile x,y (top-left of the 2x2 sprite). $E51C,$E51D = (9,15) at the start, (11,17) later in one snapshot, meaning unknown.
N 58649 Heading in bits 7-6 (set to $C0 at game start by the code at $D858).
N 58650 Player map tile x. The map is at $9858 with 128 bytes per row. Set to 59 at game start.
N 58651 Player map tile y. Set to 100 at game start.
N 58652 The bike's place in the view: column + 1 (9 at game start) and 23 - row (15 at game start). The move handlers use them as a dead zone for the camera (see notes/03, Camera).
B 58646,4,1
B 58650,2,1
B 58652,2,1
c 58654 Player movement dispatcher
D 58654 Copies the direction input ($DFA7) to $E518 and jumps to the handler for left (bit 0), up (bit 2), right (bit 1) or down (bit 3). The bike has four orientations kept in bits 7-6 of $E519: $C0 up, $80 right, $40 down, $00 left. Each handler first turns the bike to face that way (sets the sprite frame), then moves it one tile if the tiles ahead are free.
c 58680 Move right
D 58680 Entry $E538. Heading $80: tests the tiles at x+2, then x++ (camera scrolls instead once the player is past viewport column 8, stopping at camera x = 110 = 128 - 18). Sprite frame = $75C8 + 128 (frame 4).
c 58769
c 58785
c 58816
c 58832
c 58843
c 58853 Move up
D 58853 Entry $E5E5. Heading $C0: tests the tiles above, then y--. Sprite frame = $75C8 + 64 (frame 2). Bit 5 of $E519 is cleared when the turn completes.
c 58937
c 58953
c 58996
c 59007
c 59017 Move down
D 59017 Entry $E689. Heading $40: tests the tiles two rows below, then y++. Sprite frame = $75C8 + 192 (frame 6).
c 59103
c 59119
c 59150
c 59164
c 59175
; --- Player sprite frame pointers ---
b 59185 Player sprite frame pointers
D 59185 $E732 = start of the sprite frames ($75C8) and $E734 = the frame being drawn ($7608 at the start, $7688 after riding south). The data below ($E736) is code that reads the heading from $E519.
N 59186 Pointer to sprite frame 0 ($75C8).
N 59188 Pointer to the current sprite frame ($75C8 + 32*n).
B 59185,1,1
B 59186,2,2
B 59188,2,2
c 59190 Move left
D 59190 Entry $E736. Heading $00: tests the tiles to the left, then x--. Sprite frame = $75C8 + 0 (frame 0), confirmed in a snapshot facing left.
c 59275
c 59291
c 59316
c 59332
c 59343
c 59353
c 59451
c 59469
c 59578
s 59631
c 59633
; --- Camera: top-left map tile of the visible 18 x 16 viewport ---
b 59659 Viewport top-left map tile (x, y)
D 59659 The 18 x 16 tile area drawn inside the 1-pixel frame. Start-up value (51,111); the game scrolls it 19 rows (routine at $E90D, called from $D858) to (51,92). The player is drawn 8 tiles right and 8 down from it at the start, then follows the dead-zone rule of the move handlers. Mirrored as a pointer at $EB36.
N 59659 x
N 59660 y
B 59659,2,1
c 59661
c 59691
c 59713
c 59735
c 59756
c 59804
c 59852
c 59908
c 59964
c 60027
c 60028
c 60087
c 60088
c 60152
; --- Viewport map pointers ---
b 60214 Viewport pointers into the map
D 60214 $EB36 = $9858 + 128*y + x for the viewport top-left (verified in four snapshots). $EB38 is the map address of the cell being fetched for drawing: the scroll routines set it to the new edge column or row ($EB36 + 17 for the right edge) and step it by 1 or 128 per cell; the routine at $E83B (called after each move) sets it to the cells the bike has just left, which it redraws from the map. $EB3C fetches the tile from it.
N 60214 Map pointer for the viewport top-left (x,y at $E90B).
N 60216 Map address of the cell being fetched for drawing (scroll edge, or the cells the bike has just left).
B 60214,2,2
B 60216,2,2
B 60218,2,1
c 60220
c 60236
c 60261
c 60280
c 60328
c 60346
c 60375
c 60399
c 60423
c 60450
c 60479
c 60522
c 60536
c 60556
c 60576
c 60601
c 60626
c 60663
c 60685
c 60791
c 60858
c 60886
c 60895
c 60922
c 60952
c 60980
c 61008
c 61036
c 61045 Tile check: can the bike enter this tile?
D 61045 A = the map tile id ahead. Returns A = 0 if the bike may move there, non-zero if blocked. Free: ids 0, 69, 191-193, 195-197, 199-201 and 205 upward. Special: 65 water (handler $EF9C), 190 crisp packet ($EECA), 194 oil slick ($EF20), 198 fuel can ($EFD6), 203 and 204 dark-area markers ($F006 and $F070). Every other id (grass, fences, buildings...) is blocked without any penalty. Checked by flood-filling the whole map from the start: the free tiles reached on foot are exactly the roads and pavements.
c 61059
c 61130 Crisp packet (tile 190)
D 61130 Beep, remove the packet, show "Packet of KP Skips" and add 2 to the score at $5B05 (INC HL twice), then redraw the score.
t 61192
b 61217
c 61219
c 61229
c 61241
t 61292
b 61341
c 61343
c 61355
c 61362
t 61374
b 61398
c 61399 Fuel can (tile 198)
D 61399 Shows "Fill up with petrol" and loops (calling $D9FA) until the fuel pair at $E28F/$E290 is back to (4,4), the full tank.
c 61427
c 61445
c 61456
t 61504
b 61553
c 61555
c 61562
c 61572
t 61594
b 61618 Screen cell of the tile being fetched during a scroll (2 bytes: column, 24 - row); the dark-area test at $F0C5/$F0D8 reads it
c 61620 Tile fetch for drawing a newly exposed row or column of the play area ($F0B4)
D 61620 Works out the map cell for the screen cell being filled and returns its tile id, except that without the headlamp ($5B07 bit 0) it returns the blank tile 205 for map y above 80 and x up to 40 (the dark area; it tests the column number plus one against 41, found by running this routine in a simulator and confirmed on a real snapshot). Only cells that scroll into view are fetched, so cells already on screen keep what they showed until they scroll off.
c 61629
c 61656
c 61688
c 61694
c 61707
c 61717
c 61730
c 61740
c 61753
c 61782 Choose the player sprite set
D 61782 Bit 5 of $5B07 (Martin on board) selects sprite set 2 at $5C09, otherwise set 1 at $75C8. Also stores the sprite attribute $47 (bright white) at $E731.
c 61800
c 61832
c 61837
c 61842
s 61856
c 61900 Move the other vehicles (one step each, every frame)
D 61900 For each of the 20 traffic table entries, by heading (flags bits 7-6): left tests tiles (x-1,y) and (x-1,y+1), right (x+3,y) and (x+3,y+1), down (x,y+2) and (x+1,y+2), up (x,y-1) and (x+1,y-1). If both are free the vehicle steps one tile; otherwise the turn logic at $F2D2 (62162) picks a new heading. Verified by simulation against a snapshot (tools/traffic_sim.py).
c 61921
c 61930
c 61939
c 61954
c 61991
c 62031
c 62071
s 62107 Traffic: map (x, y) of the cell a vehicle is about to enter, tested by $F2AD
c 62109
s 62135
c 62136 Random number generator for the traffic ($F2B7 holds the seed)
D 62136 seed' = low byte minus high byte of 254*(seed+1) (minus 1 when there is no borrow). Used for turns and for the tile 69 gate.
c 62162 Blocked vehicle: choose a new heading
D 62162 One random byte r. The Z80 test CP k / JP M is a signed test, giving three bins: r 85-212 (50%) turn left->up, right->down, down->right, up->left; r 42-84 (17%) U-turn; r 0-41 and 213-255 (33%) the other turn: left->down, right->up, down->left, up->right. A turn only happens if the tiles in the new direction are free (except down and up, which are not checked).
c 62196
c 62205
c 62209
c 62268
c 62277
c 62281
c 62328
c 62337
c 62341
c 62359
c 62368
c 62372
c 62414
c 62459
c 62484
c 62507
c 62508
c 62509
c 62510
c 62511 Draw all vehicles ($F42F)
c 62540
c 62549
c 62558
s 62573 Traffic drawing ($F42F) working variables: $F46D pointer to the vehicle's entry, $F46F count, $F470 visibility bits of the cell ($F476), $F472/$F473 row and column loop counters, $F474/$F475 screen column and row of the cell
c 62582
c 62643
c 62780
c 62801 Draw a vehicle going left, restore the 2 cells to its right ($F551)
c 62869 Restore one map cell behind a vehicle ($F595)
c 62928 Draw a vehicle going right, restore the 2 cells to its left ($F5D0)
c 63013 Draw a vehicle going up, restore the 2 cells below it ($F625)
c 63095 Draw a vehicle going down, restore the 2 cells above it ($F677)
s 63183
c 63187 Background tile for a cell, through the dark-area test ($F6D3)
c 63216
c 63243
c 63262
c 63312
c 63330
c 63369
c 63382 Vehicle tile test
D 63382 A = a non-zero tile id. Returns 0 (free) for ids 190 and above, a random 50% for id 69 (a gate), and 255 (blocked) for ids 1-189. Tile id 0 is free without calling this.
c 63397
c 63409
c 63413 Dark-area tile mask
D 63413 Used when a vehicle's old cell is redrawn ($F595 restores the two cells behind each vehicle every frame, via $F6D3). If bit 0 of $5B07 (headlamp) is set the real tile is returned. Without it, tiles in the dark region (map y above 80 and x up to 41 here: this routine tests the map x itself) come back as tile 205 (blank), so the bike cannot see the map there. With the headlamp you see all of it.
c 63422
s 63439
c 63500 Park at a house door and visit it ($F80C)
D 63500 Sets the speed counter to 10 (stopped), shows the bike parked (frame 8 or 9), draws the room, then announces every item in the room (the loop at $FD2C calls $FD63 for each) and ORs them into the inventory byte $5B07. If the inventory did not change it shows "No items in this house". Each visit adds 3 to the score.
c 63526
b 63647
t 63654
c 63676
c 63692
c 63776 Colin walks into the house (5 frames)
D 63776 The animation shown when the bike parks at a door, before the room is swapped in. For each of 5 frames it copies 32 bytes from $72AC (frame n at $72AC + 32*n; 2x2 chars, top row first) straight over the 2x2 cells two rows above the bike's cells (column $E51C, row 24 - ($E51D + 2)), so the figure takes the colours of the door cells, then waits 64000 loops (about 0.29 s) before the next frame. After frame 5 it returns at once. Colin shrinks over the frames as he walks away from the viewer into the doorway.
c 63842
c 63843
c 63852
c 63992
c 64046
c 64069
s 64099
c 64101
c 64142
c 64259
s 64297
c 64305
; --- Item table: 7 records x 57 bytes, one per bit of the inventory byte $5B07 ---
; Record k (bit k of $5B07) is at 64412 + 57*k: 2 header bytes, 48 characters of text (two 24-character lines shown
; when the item is found) and 7 tail bytes. Bit order: 0 headlamp, 1 new tyres (special wheels), 2 snorkel,
; 3 periscope, 4 Turbo DIY kit, 5 Martin (the passenger to take to the airport), 6 the friend's mum (a temporary
; stop: bit 6 is cleared again after a delay). Header byte 0 (bit 7 clear) = points: 10 each for the headlamp, tyres, snorkel, periscope and Turbo kit, 100 for Martin, 0 for the mum; header byte 1 = the room-slot mask removed when the item is taken. Bit 4 (Turbo kit) is never read by any code: it does nothing. Bit 6 = tea: 600 clock passes. The 7 tail bytes are a sprite descriptor (column, 24 - row, pointer, width, height, ink): for the five equipment items the picture is ORed onto the HUD bike picture (headlamp $6056, tyres $609E, snorkel $60F6, periscope $6156, Turbo kit $60E6), for Martin ($5D09) and the mum ($5D49) it is drawn at the room's centre.
b 64412 Item table (7 x 57 bytes)
B 64412,2,2
T 64414,48,24
B 64462,7,7
B 64469,2,2
T 64471,48,24
B 64519,7,7
B 64526,2,2
T 64528,48,24
B 64576,7,7
B 64583,2,2
T 64585,48,24
B 64633,7,7
B 64640,2,2
T 64642,48,24
B 64690,7,7
B 64697,2,2
T 64699,48,24
B 64747,7,7
B 64754,2,2
T 64756,48,24
B 64804,7,7
c 64814
c 64837 Tea with the friend's mum ($FD45)
D 64837 Calls the clock routine at $DC04 600 times (6 x 100, each followed by a 256-step delay), so 120 clock ticks go by: the seconds counter $DBD2 wraps twice (SLEEP +5 each time, up to 50, and the fuel cans are put back), the hour hand moves 10 places and the clock hands whirl. Then clears bit 6 of $5B07.
c 64867 Announce one item found in a house ($FD63)
D 64867 HL = the item record. Byte 0 without bit 7 = the points (10 for the five ordinary items, 100 for Martin, 0 for the friend's mum), added to the score at $5B05. Byte 1 is a mask that clears the item from the room's item bytes (bit 7 of byte 0 chooses which byte), so each item can only be taken once, except the friend's mum. Prints the two 24-character lines, then if bit 7 of the first room byte is set (the friend's mum is in) runs the tea routine at $FD45.
c 64895
c 64969
c 64986
c 65032 Tune player ($FE08)
D 65032 B = number of notes, HL = table of 4-byte notes (DE = length, HL = pitch), each played with $D987 and followed by a 12 x 256 DJNZ gap (about 11 ms); after the last note a 255 x 256 wait (about 0.24 s). Tables: $FE2F start-up fanfare (5 notes), $FE43 end of game (14 notes), $FEEB leaving a house (19 notes).
c 65062 Delay loop: B x 256 DJNZ
; --- Tune: start-up fanfare, 5 notes of 4 bytes (DE length, HL pitch), 3.0 s ---
b 65071 Start-up fanfare (5 notes: 514, 575, 641, 514, 757 Hz)
B 65071,20,4
; --- Tune: end of game, 14 notes, 7.3 s ---
b 65091 End-of-game tune (14 notes, 262 to 411 Hz)
B 65091,56,4
; --- Tune: finish (airport), 28 notes, 7.2 s ---
b 65147 Finish tune (28 notes, 328 to 575 Hz)
B 65147,112,4
; --- Tune: leaving a house, 19 notes, 4.1 s ---
b 65259 Leaving-a-house tune (19 notes, 347 to 575 Hz)
B 65259,76,4
t 65360
b 65363
t 65369
b 65372
t 65393
b 65399
t 65420
b 65423
t 65428
b 65431
t 65444
b 65447
t 65449
b 65455
t 65465
b 65471
t 65473
b 65479
t 65481
b 65487
t 65497
b 65503
