"""Build the public copy of this project: the port, the tools and the notes, without any of the original game's data.

Usage: python tools/make_public.py [DEST]        (run from the repo root; default DEST: ../action-biker-clumsy-colin, a clone of
                                                  github.com/higgyone/action-biker-clumsy-colin)

Copies the tracked files that are this project's own work (port/, tools/, notes/, work/biker.ctl, README.md, requirements.txt and the git
settings) into DEST, leaving out everything taken from the game: the tape and snapshot files, assets/ (graphics, map, sounds, texts),
the disassembly (work/biker.skool), the ZEsarUX snapshots, the patched tapes, the exported sounds and every picture. The README's
"private repository" paragraph is replaced by the public one, and the .gitignore keeps the game's files out of the public repository
when someone extracts their own. DEST is cleared first (except its .git folder), so it can be a clone of the public repository: build,
look at `git status` there, commit, push.
The script stops if anything it would copy is binary or looks like game data.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.chdir(ROOT)
DEST = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "..", "action-biker-clumsy-colin"))

KEEP_DIRS = ("port/", "tools/", "notes/")
KEEP_FILES = ("README.md", "requirements.txt", ".gitattributes", "work/biker.ctl")
NEVER = (".tap", ".tzx", ".z80", ".sna", ".szx", ".zip", ".bin", ".png", ".wav", ".skool", ".json")

PRIVATE = """**This repository contains copyrighted game data (the original tape/snapshot files in
`Action-Biker_ZX-Spectrum_EN/`, ZEsarUX snapshots, the disassembly and pictures drawn from them) so it must stay
private.** It is tracked so the project can be picked up on another PC; the setup is in
`notes/01-setup-and-disassembly.md`."""
PUBLIC = """*Action Biker* is © 1985 Mastertronic; the game was written by M J Child. **This repository holds none of the game's code or data**:
only the port, the tools and the notes. To play, you need your own copy of the game (see *Getting started* below), from which
`tools/extract_assets.py` makes the graphics, map, sounds and texts the port reads. Pictures and the disassembly referred to in the notes
are not included; the tools make them from your copy."""
TITLE = ("# Action Biker -> Python/pygame", "# Action Biker: Clumsy Colin")
LICENSE = """MIT License

Copyright (c) 2026 higgyone

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This licence covers this project's own code, tools and notes only. Action Biker itself (its code, graphics,
map, sounds and texts) is (c) 1985 Mastertronic and is not part of this repository or covered by this licence.
"""
LICENSE_NOTE = """
## Licence
This project's code, tools and notes are under the MIT licence (`LICENSE`). Action Biker itself is (c) 1985 Mastertronic: none of it is
in this repository, and you need your own copy of the game to play.
"""
GITIGNORE = """# Python
.venv/
__pycache__/
*.pyc

# Everything taken from the original game stays out of this repository: your copy of the game,
# what tools/extract_assets.py makes from it, and the snapshots and pictures the tools write
game/
Action-Biker_ZX-Spectrum_EN/
assets/
work/*
!work/biker.ctl
*.tap
*.tzx
*.z80
*.sna
*.szx
*.png
*.wav
*.skool
"""


def tracked():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
    return [f for f in out if f]


def wanted(path):
    if path.lower().endswith(NEVER):
        return False
    return path in KEEP_FILES or path.startswith(KEEP_DIRS)


def main():
    files = [f for f in tracked() if wanted(f) and os.path.exists(f)]
    for f in files:                                   # nothing binary goes out
        data = open(f, "rb").read()
        if b"\0" in data:
            sys.exit(f"stopped: {f} looks binary")
    os.makedirs(DEST, exist_ok=True)
    for name in os.listdir(DEST):                     # start clean, keep the clone's .git
        if name != ".git":
            path = os.path.join(DEST, name)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    for f in files:
        dst = os.path.join(DEST, f)
        os.makedirs(os.path.dirname(dst) or DEST, exist_ok=True)
        shutil.copyfile(f, dst)
    readme = open(os.path.join(DEST, "README.md"), encoding="utf-8").read().replace("\r\n", "\n")
    if PRIVATE not in readme:
        sys.exit("stopped: the README's private paragraph has changed; update PRIVATE in tools/make_public.py")
    readme = readme.replace(PRIVATE, PUBLIC).replace(*TITLE).rstrip("\n") + "\n" + LICENSE_NOTE
    open(os.path.join(DEST, "README.md"), "w", encoding="utf-8", newline="\n").write(readme)
    open(os.path.join(DEST, "LICENSE"), "w", newline="\n").write(LICENSE)
    open(os.path.join(DEST, ".gitignore"), "w", newline="\n").write(GITIGNORE)
    print(f"{len(files)} files copied to {DEST}")
    for f in sorted(files):
        print("  ", f)


if __name__ == "__main__":
    main()
