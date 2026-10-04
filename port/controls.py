"""The five control schemes of the original's Select Controls menu, from the game's own tables.

The game reads the keyboard or a joystick with the routine at $DFA8 (57256): five tests, each `LD A,port / IN A,($FE) / AND mask / CALL Z` (CALL NZ for
the Kempston joystick, which is active high; the Fuller one is active low like a key), in the order left, right, up, down, fire. The menu ($DD77, 56695) patches the ports and masks of that routine for
the scheme chosen; what it writes is copied here (SCHEMES) and checked against the original by tools/check_controls.py. The scheme the code holds before
any patch is Cursor (5 left, 8 right, 7 up, 6 down, Space), so choosing 5 patches nothing.
"""
import pygame

ACTIONS = ("left", "right", "up", "down", "fire")

# for each action (the value loaded into A before the IN, which picks the keyboard half-row, and the mask), as the menu leaves them; "in" is the port the IN
# reads. The joystick schemes read port 31 / 127 (the A value does not matter, None) and need a joystick interface.
SCHEMES = {
    "KEYBOARD": {"menu": 1, "in": 254, "keys": [(127, 8), (127, 4), (253, 1), (254, 2), (127, 1)]},          # N M A Z Space
    "KEMPSTON": {"menu": 2, "in": 31, "keys": [(None, 2), (None, 1), (None, 8), (None, 4), (None, 16)], "joystick": True},
    "SINCLAIR": {"menu": 3, "in": 254, "keys": [(239, 16), (239, 8), (239, 2), (239, 4), (239, 1)]},         # 6 7 9 8 0
    "FULLER": {"menu": 4, "in": 127, "keys": [(None, 4), (None, 8), (None, 1), (None, 2), (None, 128)], "joystick": True},
    "CURSOR": {"menu": 5, "in": 254, "keys": [(247, 16), (239, 4), (239, 8), (239, 16), (127, 1)]},          # 5 8 7 6 Space
}
BY_MENU = {s["menu"]: name for name, s in SCHEMES.items()}

# the Spectrum keyboard: half-row port high byte -> keys for bits 0..4
ROWS = {
    254: "shift z x c v", 253: "a s d f g", 251: "q w e r t", 247: "1 2 3 4 5",
    239: "0 9 8 7 6", 223: "p o i u y", 191: "enter l k j h", 127: "space symbol m n b",
}
PYGAME_KEY = {"shift": pygame.K_LSHIFT, "space": pygame.K_SPACE, "symbol": pygame.K_RSHIFT, "enter": pygame.K_RETURN}


def key_for(port, mask):
    """pygame key for a keyboard (port, mask) pair, or None."""
    name = ROWS[port].split()[mask.bit_length() - 1]
    return PYGAME_KEY.get(name, getattr(pygame, "K_" + name, None))


class Controls:
    """Turns pygame input into the game's direction/fire bits: bit 0 left, 1 right, 2 up, 3 down (as $DFA7) and the trigger separately.
    The arrow keys and Space always work as well, and so does a USB joystick or gamepad if one is plugged in (pygame.joystick)."""

    def __init__(self, scheme="KEYBOARD"):
        self.name = scheme
        self.scheme = SCHEMES[scheme]
        self.joystick = None
        if pygame.joystick.get_count():            # a USB joystick or gamepad works with every scheme (stick or hat = directions, any button = fire)
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
        self.keys = [None if self.scheme.get("joystick") else key_for(*pair) for pair in self.scheme["keys"]]   # pygame keys, None for a joystick

    def read(self, k):
        """(direction mask, fire) from the pygame key state `k` (pygame.key.get_pressed())."""
        bits = [bool(key and k[key]) for key in self.keys]
        if self.joystick:
            x = self.joystick.get_axis(0) if self.joystick.get_numaxes() else 0
            y = self.joystick.get_axis(1) if self.joystick.get_numaxes() > 1 else 0
            hat = self.joystick.get_hat(0) if self.joystick.get_numhats() else (0, 0)
            bits[0] |= x < -0.5 or hat[0] < 0
            bits[1] |= x > 0.5 or hat[0] > 0
            bits[2] |= y < -0.5 or hat[1] > 0
            bits[3] |= y > 0.5 or hat[1] < 0
            bits[4] |= any(self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons()))
        bits[0] |= bool(k[pygame.K_LEFT])
        bits[1] |= bool(k[pygame.K_RIGHT])
        bits[2] |= bool(k[pygame.K_UP])
        bits[3] |= bool(k[pygame.K_DOWN])
        bits[4] |= bool(k[pygame.K_SPACE])
        return sum(1 << i for i in range(4) if bits[i]), bits[4]
