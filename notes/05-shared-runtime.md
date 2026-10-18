# Moving the port onto zxport (the shared run-time package)

`zx-port-kit` now has `zxport/`, the Spectrum basics that every port needs at run time. It
was written for Ghostbusters, from what this port had worked out. This note says which parts
of Action Biker's port now come from it, and which stay here, and why.

## What moves to zxport
| Here before | Now | Same behaviour? |
|---|---|---|
| `sound.py`: `frequency`, `beep_seconds`, `silence`, `beep`, `tune`, `RATE`, `VOLUME` (the ROM BEEP as square waves) | `zxport.beeper` | the same sums; `tune` passes the note gap and the tail |
| `biker.py`: `rgb()`, the Spectrum's colours | `zxport.screen.PALETTE` | the same 16 colours (205 normal, 255 bright) |
| `biker.py`: `screen_surface()`, a 6912-byte screen as a picture | `zxport.screen.screen_from_bytes` + `Screen.to_surface` | the same picture, made with numpy instead of a pixel at a time |
| `biker.py`: the window, its border and the scaling (`present`) | `zxport.window.Window.show_surface` | the same size and border |
| `biker.py`: the pass counter (`acc += ... * PASS_HZ`) | `zxport.window.Pacer(PASS_HZ)` | the same rate; after a long stall it catches up at most 4 passes at once |

## What stays here
- `controls.py`: the five control schemes are the game's own tables, patched by its Select
  Controls menu and checked against it (`tools/check_controls.py`). `zxport.keys` is a simpler
  layout of named keys, which suits a game that reads fixed keys.
- `sound.py`'s `Sound` class: it mutes the effects and the music separately and plays runs
  of clicks (`play_seq`). `zxport.beeper.Sounds` has neither yet.
- The drawing in `World` and `options.py`: they build pygame surfaces a character at a
  time, where zxport keeps pixels and colours as arrays (`zxport.screen.Screen`). Changing
  that means redrawing everything, for no change on the screen.

## How it is checked
The checks that use these parts are run before and after, and must give the same results:
`check_port_sound.py` (the beeps and tunes), `check_screens.py` (the loading screens and their
borders), `check_options.py` (the setup screen, pausing), and the rest of the `check_*.py` and
`compare_original.py` (the game itself).

## Setup
`requirements.txt` now has `-e ../zx-port-kit`, as Ghostbusters does: clone `zx-port-kit` next
to this repo. The public copy gets the `zxport/` modules the port imports (beeper, screen, window) copied into `port/zxport/` by `make_public.py`, and
its `requirements.txt` without that line, so it still needs nothing but pip.

## Done
All twelve checks pass before and after (`check_port_sound`, `check_options`, `check_screens`,
`check_port_items`, `check_port_needle`, `check_port_traffic`, `check_port_fixes`, `check_hud`,
`check_rooms`, `check_vehicle_drawing`, `check_controls`, `compare_original`). On top of that,
every sound comes out sample for sample the same, and the four screens from the tape pixel for
pixel. The public copy, built by `make_public.py`, runs its checks with only pip's packages
installed (no zx-port-kit).
