# Setup and first disassembly

## Environment
Windows, Python venv in `.venv` with `skoolkit` (10.1), `pygame-ce`, `pillow`, `numpy`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install skoolkit pygame-ce pillow numpy
```

## Source files
`Action-Biker_ZX-Spectrum_EN/` holds the downloaded `.tap`, `.z80`, `.tzx` (plus alternate dumps).
We work from the `.z80` snapshot, copied to `work/biker.z80`.

- `.z80` = compressed snapshot of the 48K RAM plus a register header. The game is already loaded.
- `.tap` = BASIC loader `BIKER` (116 bytes) followed by six headerless data blocks (flag 255), loaded by the
  game's own loader: 7020, 17500, **6912 (loading screen 1)**, 17000, **6912 (loading screen 2)** and 7551
  bytes. The two 6912-byte blocks are exactly a full screen (6144 pixel bytes + 768 colour bytes). Screen 1
  is a KP Skips sponsor advert and screen 2 the "Action Biker by M J Child" title. `tools/tap_screens.py
  GAME.tap OUT_PREFIX` draws them (local PNGs, gitignored). The block sizes add up to about 63 KB, more than
  the 48 KB of RAM, so the screens are shown and then overwritten. The other four blocks are not yet
  investigated (the 17 KB ones may be compressed or hold the game and its data in stages).
- The snapshot is at the "Select Controls" menu (Keyboard, Kempston, Sinclair, Fuller, Cursor),
  not in gameplay.

## Commands (SkoolKit 10 names!)
SkoolKit 10 renamed the scripts: `sna2ctl.py`, `sna2skool.py`, `sna2img.py` (not `snap2*`).
On Windows run them through the venv Python and redirect stdout. Launching the `.py` directly via
file association loses the redirect and gives 0-byte files. `-o` means `--org`, not an output file.

```bash
PY=.venv/Scripts/python.exe
$PY .venv/Scripts/sna2ctl.py   work/biker.z80 > work/biker.ctl
$PY .venv/Scripts/sna2skool.py -c work/biker.ctl work/biker.z80 > work/biker.skool
$PY .venv/Scripts/sna2img.py   work/biker.z80 work/screen.png
```

- `sna2ctl` guesses which regions are code/data and writes a control file (`c`, `b`, `t`, `w`).
- `sna2skool` disassembles using that control file.
- `sna2img` renders screen memory (`$4000-$5AFF`) to PNG.

The workflow is a loop: edit `work/biker.ctl` as we learn, re-run `sna2skool`, read the result.
The auto-generated ctl mislabels some data as code; fix by hand.

## Flat RAM dump
`work/biker.bin` = 49,152 bytes, byte 0 = address `$4000` (offset = address - 0x4000):

```python
from skoolkit.snapshot import Snapshot
open('work/biker.bin','wb').write(bytes(Snapshot.get('work/biker.z80').ram(1)))
```
