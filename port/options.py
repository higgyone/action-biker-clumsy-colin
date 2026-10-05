"""The setup screen: not in the original. It comes first, before the tape's loading screens, in the Spectrum's font and colours, and lets you
turn the trainer options, the port's fixes and the sound on or off before playing.

The trainer options are the cheats (SLEEP, fuel and the clock never run out); the fixes change how the game plays; the sound lines turn the
sound effects (clicks, beeps, crashes) and the music (the start fanfare, the house jingle and the end tunes) on or off. With every trainer
option and fix off the game is exactly the original. Keys: up/down choose a line, Space (or X) turns it on or off, 1-9 and 0 switch the
trainer and fix lines directly, S and M the sound lines, Enter plays, Esc quits. A joystick works too: up/down to choose, left/right or fire
to switch. The choice is remembered for the next run in ~/.action_biker.json.
"""
import json
import os

import pygame

TRAINER = ("infinite_sleep", "infinite_fuel", "infinite_time")
SOUND = ("sound_effects", "music")
LABELS = {
    "infinite_sleep": "Infinite SLEEP",
    "infinite_fuel": "Infinite fuel",
    "infinite_time": "Infinite time",
    "easy_parking": "Easy parking",
    "turn_assist": "Turn assist",
    "quick_start": "Quick start",
    "quick_turns": "Quick turns",
    "map_view": "Map view     (Tab)",
    "breadcrumbs": "Breadcrumbs    (B)",
    "item_markers": "Item markers   (I)",
    "sound_effects": "Sound effects",
    "music": "Music",
}
ABOUT = {                                  # shorter than the FIXES descriptions, to fit under the list (30 columns, 4 lines)
    "infinite_sleep": "SLEEP never goes down: crashes, oil and water cost nothing.",
    "infinite_fuel": "The fuel never runs out.",
    "infinite_time": "Eight o'clock never ends the day. The clock still runs.",
    "easy_parking": "Space enters a house whenever a door is under the bike or just ahead, even when stopped; Colin walks up the path.",
    "turn_assist": "Turns pressed a tile or two early or late still work: the bike carries on or slides across, then turns.",
    "quick_start": "No wait to get going, and the bike speeds up twice as fast.",
    "quick_turns": "The bike turns at once at any speed.",
    "map_view": "Tab shows the whole town: you, your trail and the part on screen. The game waits while it is up.",
    "breadcrumbs": "B shows or hides a trail of dots where you have ridden this game; a ringed dot where you went into a house.",
    "item_markers": "I shows or hides a marker on every house that still holds items.",
    "sound_effects": "The clicks, beeps and crashes. The game's timing stays the same with them off.",
    "music": "The start fanfare, the house jingle and the end tunes. The game still waits for them, silently.",
}
SAVED = os.path.join(os.path.expanduser("~"), ".action_biker.json")
# Spectrum colours (bright)
BLACK, BLUE, RED, MAGENTA, GREEN, CYAN, YELLOW, WHITE = [(255 if i & 2 else 0, 255 if i & 4 else 0, 255 if i & 1 else 0) for i in range(8)]


def load_saved():
    """What was ticked last time: {"fixes": [...], "sound_effects": bool, "music": bool}, or {} if nothing was saved."""
    try:
        data = json.load(open(SAVED))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save(fixes, sound):
    try:
        json.dump({"fixes": sorted(fixes), **{name: name in sound for name in SOUND}}, open(SAVED, "w"))
    except OSError:
        pass


def wrap(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return lines + [line] if line else lines


class OptionsScreen:
    def __init__(self, fixes, font, chosen=None, sound=None):
        """fixes: the port's FIXES table {name: description}; font: the ROM font (96 chars x 8 bytes). chosen: the fixes ticked to begin with, sound: the sound lines ticked (None:
        what was saved last time; with nothing saved, no fixes and the sound on)."""
        saved = load_saved()
        self.descriptions = fixes
        self.names = [n for n in TRAINER if n in fixes] + [n for n in fixes if n not in TRAINER] + list(SOUND)
        self.ticked = set(saved.get("fixes", ()) if chosen is None else chosen) & set(fixes)
        self.ticked |= {n for n in SOUND if saved.get(n, True)} if sound is None else set(sound) & set(SOUND)
        self.cursor = 0
        self.last_pad = (0, False)
        self.font = font

    @property
    def fixes(self):
        return self.ticked - set(SOUND)

    @property
    def sound(self):
        return self.ticked & set(SOUND)

    def hotkey(self, i):
        name = self.names[i]
        return {"sound_effects": "S", "music": "M"}.get(name, str((i + 1) % 10) if i < 10 else " ")

    def toggle(self, name):
        self.ticked ^= {name}

    def key(self, key):
        """A key press. Returns True when the game should start."""
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return True
        hot = {pygame.key.key_code(self.hotkey(i).lower()): i for i in range(len(self.names)) if self.hotkey(i) != " "}
        if key in hot:
            self.cursor = hot[key]
            self.toggle(self.names[self.cursor])
        elif key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % len(self.names)
        elif key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % len(self.names)
        elif key in (pygame.K_SPACE, pygame.K_x, pygame.K_LEFT, pygame.K_RIGHT):
            self.toggle(self.names[self.cursor])
        return False

    def pad(self, mask, fire):
        """A joystick's direction bits (1 left, 2 right, 4 up, 8 down) and fire: acts on presses only, so holding does not repeat."""
        old_mask, old_fire = self.last_pad
        new = mask & ~old_mask
        self.last_pad = (mask, fire)
        if new & 4:
            self.cursor = (self.cursor - 1) % len(self.names)
        if new & 8:
            self.cursor = (self.cursor + 1) % len(self.names)
        if new & 3 or (fire and not old_fire):
            self.toggle(self.names[self.cursor])

    def text(self, screen, s, col, row, ink, paper=BLACK):
        """Print with the Spectrum ROM font at character (col, row)."""
        for i, ch in enumerate(s):
            code = ord(ch) - 32
            glyph = self.font[8 * code:8 * code + 8] if 0 <= code < 96 else bytes(8)
            for r in range(8):
                for bit in range(8):
                    screen.set_at((8 * (col + i) + bit, 8 * row + r), ink if glyph[r] & (0x80 >> bit) else paper)

    def draw(self, screen):
        """The screen on a 256x192 surface, in the Spectrum's colours and font."""
        screen.fill(BLACK)
        self.text(screen, "     TRAINER  AND  FIXES      ", 1, 0, WHITE, BLUE)
        row = 2
        groups = [("TRAINER", YELLOW, [n for n in self.names if n in TRAINER]),
                  ("FIXES", CYAN, [n for n in self.names if n not in TRAINER and n not in SOUND]),
                  ("SOUND", MAGENTA, list(SOUND))]
        for title, colour, names in groups:
            self.text(screen, title, 1, row, colour)
            row += 1
            for name in names:
                i = self.names.index(name)
                on = name in self.ticked
                paper = BLUE if i == self.cursor else BLACK
                self.text(screen, f" {self.hotkey(i)} {LABELS.get(name, name):<20}  ", 1, row, WHITE, paper)
                self.text(screen, " ON " if on else " OFF", 26, row, GREEN if on else RED, paper)
                row += 1
        name = self.names[self.cursor]
        for k, line in enumerate(wrap(ABOUT.get(name) or self.descriptions.get(name, ""), 30)[:4]):
            self.text(screen, line, 1, 18 + k, WHITE)
        self.text(screen, "Keys or fire: on/off ENTER: go", 1, 23, YELLOW)
