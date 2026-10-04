# Memory map (from tools/tilemap.py, snapshot at the controls menu)

`tools/tilemap.py` draws each 8 consecutive bytes as an 8x8 1bpp tile, 32 tiles per row, wrapping into
side-by-side blocks. It ignores opcodes entirely: graphics look like pictures, code looks like static.
It assumes 8 bytes = one tile counted from the start address, so graphics in other layouts
(16 wide, column-major, pre-shifted) look scrambled. It is a scouting tool, not the extractor.

```
python tools/tilemap.py work/biker.z80 work/tiles.png [start_hex] [end_hex]
```

| Range | Observation |
|---|---|
| `$4000-$5AFF` | Screen memory (mostly blank at the menu) |
| `$5B00-$97FF` (approx.) | Scenery graphics in horizontal strips: houses, trees, rooftops, shop signs BAKER / BUTCHER / PETROL. Static between snapshots. The game is top-down, not side-scrolling (see note 03). |
| `$9858-$D857` | **Level map**: 128 x 128 tile ids, 1 byte each, 128-byte rows. Not sprites (earlier guess was wrong). See note 03. |
| `$D858-$FFFF` | Mostly code/tables/buffers. Score digits at `$E04B`. Character font near `$FF00` (A B C D ...). |

## Open questions (all answered since)
- ~~Tile size/layout of the scenery art, and how map tile ids index it. Where the sprites (bike, cars) live.~~ Note 03: tiles at `$79E0`,
  buildings at `$80B8`, the bike at `$75C8`, vehicles at `$734C`.
- ~~Where the main loop is.~~ `$E2AE`; one frame is `$D899` (note 03).
- ~~Whether the TAP's multiple blocks mean extra stages not in this snapshot.~~ No: the blocks are the loader, the game and the two
  loading screens; `tools/original.py` loads the whole tape in the simulator and reaches the same menu as the `.z80`.
- `$5B00-$97FF` is not all scenery: `$5B00-$5B08` are variables (seed, high score, SLEEP, score, items), `$5B09-$5D08` the two extra
  bike sprite sets, `$5D09-$6625` the house item graphics (with the saved HUD bike picture at `$5DE9`), `$6626` the item records,
  `$66B2` the house table. The "font near `$FF00`" is not used by the game, and the stack sits just above it.
