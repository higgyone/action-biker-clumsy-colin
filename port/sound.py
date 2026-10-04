"""The original's sounds, rebuilt for the port. The game only has a beeper: every noise goes through the ROM's BEEP routine
($03B5) via the game's own routine at $D987 (55687), with HL = pitch and DE = length in cycles of the wave:
    frequency = 437500 / (HL + 30.125) Hz        duration = DE / frequency seconds        (a square wave)
The tune player at $FE08 (65032) plays notes of 4 bytes (DE, HL), each followed by a gap of 12 x 256 DJNZ loops (about 11 ms)
and ends with a longer wait of 255 x 256 loops (about 0.24 s). Notes: notes/03-level-map.md ("Sound").

samples() builds every sound as an int16 array and needs only numpy, so it can be tested without a sound card.
"""
import numpy as np

RATE = 44100
VOLUME = 0.25
NOTE_GAP = 12 * 256 * 13 / 3_500_000       # seconds: the pause after every note of a tune
TUNE_TAIL = 255 * 256 * 13 / 3_500_000     # seconds: the wait at the end of a tune
FLASH = 0.0072                             # seconds the play-area flash ($D99B, 25,000 T-states) takes after each of the crash's two beeps
CRASH_TAIL = 0.0069                        # seconds the crash routine then spends on SLEEP and the score ($E08D) before it returns (measured)

# beeps used directly by the game: name -> (HL, DE) and the routine that makes them
BEEPS = {
    "crash": (16, 261),      # $D95D (55650): twice, each followed by the play-area flash; vehicles, water ($EF9C); runs on every pass of an overlap
    "step": (75, 10),        # $D9FA (55802): one click for every step of the fuel gauge, also while a fuel can refills the tank
    "crisp": (150, 16),      # $EECA (61130): a packet of crisps
    "tick": (1, 1),          # $E82F (59439): one 70-microsecond click every time the bike is drawn, i.e. every pass
}


def frequency(hl):
    return 437500.0 / (hl + 30.125)


def beep_seconds(hl, de):
    return de / frequency(hl)


def silence(seconds):
    return np.zeros(max(0, round(RATE * seconds)), dtype=np.int16)


def beep(hl, de, volume=VOLUME):
    f = frequency(hl)
    n = max(1, round(RATE * de / f))
    phase = (np.arange(n) / RATE * f) % 1.0
    return (np.where(phase < 0.5, 1.0, -1.0) * volume * 32767).astype(np.int16)


def tune(notes):
    parts = []
    for de, hl in notes:
        parts += [beep(hl, de), silence(NOTE_GAP)]
    parts.append(silence(TUNE_TAIL))
    return np.concatenate(parts)


def tune_seconds(notes):
    return sum(beep_seconds(hl, de) + NOTE_GAP for de, hl in notes) + TUNE_TAIL


def samples(tunes):
    """All sounds as {name: int16 array}. `tunes` is assets/sounds.json: {"start": [[DE, HL], ...], "end": ..., "house": ...}."""
    out = {name: beep(*BEEPS[name]) for name in ("step", "crisp", "tick")}
    out["crash"] = np.concatenate([beep(*BEEPS["crash"]), silence(FLASH), beep(*BEEPS["crash"]), silence(FLASH), silence(CRASH_TAIL)])
    for name, notes in tunes.items():
        out[name] = tune(notes)
    return out


class Sound:
    """Plays the sounds through pygame's mixer. play(name) never blocks; seconds(name) is how long the original's routine runs."""

    def __init__(self, tunes):
        import pygame
        pygame.mixer.quit()                       # pygame.init() may already have opened a stereo mixer
        pygame.mixer.init(RATE, -16, 1, allowedchanges=0)   # keep it mono at RATE even if the sound card prefers stereo (SDL converts)
        pygame.mixer.set_num_channels(8)
        self.pygame = pygame
        self.arrays = samples(tunes)
        if pygame.mixer.get_init()[2] != 1:       # a stereo mixer anyway: send the same samples to both channels
            self.arrays = {name: np.column_stack((a, a)) for name, a in self.arrays.items()}
        self.sounds = {name: pygame.sndarray.make_sound(a) for name, a in self.arrays.items()}
        self.sequences = {}
        self.tunes = set(tunes)                   # the music; everything else is a sound effect
        self.muted = set()

    def mute(self, effects=False, music=False):
        """Silence the sound effects and/or the music. Only the sound goes: seconds() is unchanged, so the game waits for a silent tune as long."""
        self.muted = {name for name in self.arrays if (name in self.tunes and music) or (name not in self.tunes and effects)}

    def seconds(self, name):
        return len(self.arrays[name]) / RATE

    def play(self, name):
        if name not in self.muted:
            self.sounds[name].play()

    def play_seq(self, name, count, gap, lead=0.0):
        """`count` copies of a short sound, `gap` seconds apart, the first after `lead` seconds (the oil skid's ticks, the gauge's refill clicks)."""
        if count <= 0 or name in self.muted:
            return
        key = (name, count, round(gap, 4), round(lead, 3))
        if key not in self.sequences:
            one = self.arrays[name]
            pause = silence(max(0.0, gap - len(one) / RATE))
            self.sequences[key] = self.pygame.sndarray.make_sound(np.concatenate([silence(lead)] + [np.concatenate([one, pause])] * count))
        self.sequences[key].play()
