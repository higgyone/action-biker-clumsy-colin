# Action Biker: Clumsy Colin

Reverse engineering the ZX Spectrum game *Action Biker* (Mastertronic, 1985) and rebuilding it
in Python/pygame so it **plays the same** (not byte-identical).

*Action Biker* is © 1985 Mastertronic; the game was written by M J Child. **This repository holds none of the game's code or data**:
only the port, the tools and the notes. To play, you need your own copy of the game (see *Getting started* below), from which
`tools/extract_assets.py` makes the graphics, map, sounds and texts the port reads. Pictures and the disassembly referred to in the notes
are not included; the tools make them from your copy.

## Status
**Done.** The port plays the game as the original does, checked against the original's own code running in a Z80 simulator: frame by
frame for the bike, view, speed, SLEEP, score, items, clock, fuel and all 20 vehicles (`tools/compare_original.py`), and pixel by pixel
for the vehicles, the house rooms, the fuel gauge and the clock (`tools/check_vehicle_drawing.py`, `check_rooms.py`, `check_hud.py`).
On top of that, a setup screen turns on optional fixes and a trainer, and switches the sound effects and music.

- [x] Tooling (SkoolKit, venv) and the disassembly (`work/biker.ctl` -> `.skool`)
- [x] Assets: map, tiles, buildings, sprites, vehicles, house rooms and items, HUD, font, messages, tunes, all read from your copy of the
      game by `tools/extract_assets.py`
- [x] Logic: bike, camera, traffic, SLEEP, score, items, tea, clock, fuel, dark area, messages, sound, endings and the main loop
      (`notes/03-level-map.md`); every memory location the notes once marked unknown is identified
- [x] The pygame port (`port/biker.py`): loading screens, Select Controls, the whole game with the original's timings
- [x] The fixed version: the setup screen (below)

## Getting started
You need **your own copy of the original game**. This project contains none of it: `tools/extract_assets.py` reads the graphics, map,
sounds and texts out of your copy into `assets/`, and the port plays from those. It works with:

- a **`.tzx` or `.tap`** tape image (best: it also gives the three loading screens), or
- a **`.z80`** snapshot saved at the game's Select Controls menu, before a game has been played,
- or a `.zip` holding one of them.

You also need Python 3.9 or later. Then, from the folder you cloned this into:

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python tools/extract_assets.py "path/to/Action Biker.tzx"
.venv/Scripts/python port/biker.py
```

On Linux or macOS use `.venv/bin/python` instead of `.venv/Scripts/python`. The extraction takes a few seconds and only has to be done
once. It runs the game's own loader, menu and start-up in SkoolKit's Z80 simulator and reads everything from there, so nothing is copied
by hand. Run without a path, it looks for a copy in a `game/` folder.

**Which copy?** Copies of the tape differ. Of the TOSEC set, the `.tzx`, the `[a]` `.tap` and the `[a2]` `.tzx` give exactly the assets
this port was made and checked with. The plain `.tap` and the `[a]` `.tzx` load with the colours of five buildings missing (black on
black, as that copy plays); the extractor warns when that happens. A `.z80` has no loading screens, so the port skips them.

## The setup screen: trainer, fixes and sound
The port starts with a screen the original does not have. Choose a line with up/down and turn it on or off with Space (or press its key),
then press **Enter** to play. A joystick works too. Your choice is remembered for next time (in `~/.action_biker.json`).

**With everything under Trainer and Fixes off, you are playing the original game**, with its own timings, quirks and difficulty.

| Key | Trainer | What it does |
|---|---|---|
| 1 | Infinite SLEEP | SLEEP never goes down: crashes, oil and water cost nothing |
| 2 | Infinite fuel | the tank never runs dry |
| 3 | Infinite time | eight o'clock never ends the day (the clock still runs, and SLEEP still comes back every so often) |

| Key | Fix | What it does |
|---|---|---|
| 4 | Easy parking | Space enters a house whenever a door is under the bike or just ahead of it, even standing still, and the bike pulls onto the door's path so Colin always walks up it. The original only lets you in on the pass where the moving bike's front touches the door |
| 5 | Turn assist | a turn onto a side road pressed a tile or two early or late still works: the bike carries on to the junction, or slides across a tile, then turns |
| 6 | Quick start | no wait to get going from a standstill, and the bike speeds up twice as fast |
| 7 | Quick turns | the bike turns at once at any speed, instead of waiting between turn steps when slow |
| 8 | Map view | **Tab** shows the whole town: you as a blinking red dot, your trail, the part on screen, and the edge of the dark area (dashed pink). The game waits while it is up |
| 9 | Breadcrumbs | **B** shows or hides a trail of dots wherever you have ridden this game; where you stopped to go into a house the dot is bigger, with a white ring (a white square on the Tab map) |
| 0 | Item markers | **I** shows or hides a marker on every house that still holds something (red: Martin, cyan: the friend's mum, yellow: the rest) |

| Key | Sound | What it does |
|---|---|---|
| S | Sound effects | the clicks, beeps and crashes |
| M | Music | the start fanfare, the house jingle and the end tunes |

With the sound off the game keeps its timing: it still waits for a tune, silently.

## Playing
After the setup screen the game starts as the tape does: the KP Skips loading screen and the Action Biker title (any key skips them),
then **Select Controls**: 1 Keyboard (N left, M right, A up, Z down, Space), 2 Kempston, 3 Sinclair (6 7 9 8 0), 4 Fuller, 5 Cursor
(5 8 7 6, Space). The arrow keys and Space always work as well, and a USB joystick or gamepad works with every scheme. **P** or **Esc**
pauses the game (P or Esc again to carry on, **Q** to quit); before the game starts, Esc quits.

You are Colin, dreaming. Find **Martin** in one of the houses and ride him to the **airport** in the top right before eight o'clock.
Stop at a house door and press **Space** to go in: some houses hold equipment you need (a headlamp for the dark part of town, tyres for
oil, a snorkel and periscope for the water), and the friend's mum gives you a cup of tea, which brings SLEEP back but costs time. Crashing
into the traffic costs SLEEP; at 0 you wake up. Fuel cans refill the tank. The whole game is written up in `notes/04-how-the-game-works.md`.

**Command line options:** `--no-intro` goes straight to the game (keyboard controls, fixes from the command line), `--controls NAME`
picks the control scheme and skips the screens too, `--fix NAME` turns one fix on (repeatable), `--fixes` all of them, `--list-fixes`
lists them, `--no-sound-effects` and `--no-music` switch the sound off.

New fixes go in the `FIXES` table of `port/biker.py` (and `port/options.py` for the setup screen); `tools/check_port_fixes.py` checks each
one, and `tools/compare_original.py` checks that with no fixes the game still plays exactly like the original, frame by frame.

## Layout

- `port/` the pygame game: `biker.py` (game, HUD, main loop), `traffic.py`, `sound.py`, `controls.py`, `options.py` (the setup screen)
- `tools/` `extract_assets.py` (writes `assets/` from your copy of the game), `original.py` (loads your copy in the simulator), the
  `check_*.py` and `compare_original.py` checks against the original, and helpers (`tilemap.py`, `render_map.py`, `make_patched_game.py`, ...)
- `assets/` everything the port loads, made by `tools/extract_assets.py`
- `work/biker.ctl` SkoolKit control file; the place our understanding of the code accumulates
- `notes/` what we have learned so far

The game itself (object, controls, items, hazards) is written up in `notes/04-how-the-game-works.md`.

## Testing aid: a patched copy of the game
`python tools/make_patched_game.py` writes `work/biker_infinite.tap` and `.tzx`: the original tape with four bytes changed so SLEEP and fuel never
go down and eight o'clock no longer ends the day (the clock itself still runs: SLEEP still recovers, the fuel cans come back, tea works). Load the `.tap` in an emulator exactly as the original. `python tools/check_patched_game.py`
runs the real game code in a simulator to show the difference. Details are in the header of `tools/make_patched_game.py`.
The same script also writes `work/biker_infinite_fast.tap` and `.tzx`: the same four patches plus one byte (`$E4F5`, `AND A` to `XOR A`) so the bike is at full speed on the first pass of a held key instead of speeding up over about ten passes (letting go still coasts to a stop). Careful: full speed is also what makes oil slicks dangerous without the special wheels.

## Licence
This project's code, tools and notes are under the MIT licence (`LICENSE`). Action Biker itself is (c) 1985 Mastertronic: none of it is
in this repository, and you need your own copy of the game to play.
