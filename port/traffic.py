"""The other road users, as the original's routine at $F1CC (61900) moves them. Pure Python, no pygame.

A table of [x, y, flags]; flags bits 7-6 = heading (0 left, 1 down, 2 right, 3 up), bits 5-4 = vehicle type
(0 van, 1 motorbike, 2 saloon car), bits 2-0 = ink colour. Notes: notes/03-level-map.md ("Traffic movement").
Verified against the snapshots by tools/traffic_sim.py: one update of the controls-menu table reproduces the level
snapshot's table and ends on the same random seed.
"""


def jp_m(a, k):
    """Z80 `CP k` then `JP M`: taken when bit 7 of (a - k) is set (a signed test, so three bins, not two)."""
    return ((a - k) & 0x80) != 0


class Traffic:
    def __init__(self, table, seed, game_map=None):
        self.table = [list(e) for e in table]       # [x, y, flags] x 20
        self.seed = seed                             # $F2B7
        self.map = game_map                          # 128 x 128 numpy array of tile ids (live: pickups come and go)

    def rng(self):
        """$F2B8 (62136): seed' = low byte minus high byte of 254 * (seed + 1), less 1 when there is no borrow."""
        a = self.seed
        hl = ((a << 8) - a - a + 254) & 0xFFFF
        low, high = hl & 255, hl >> 8
        out = (low - high) & 255
        if low >= high:
            out = (out - 1) & 255
        self.seed = out
        return out

    def tile(self, x, y):
        return int(self.map[y, x]) if 0 <= x < 128 and 0 <= y < 128 else 1

    def blocked_tile(self, x, y):
        """$F796 (63382) for non-zero ids: free from 190 up, a random 50% gate for 69, blocked for 1-189. Id 0 is free."""
        t = self.tile(x, y)
        if t == 0:
            return False
        if t == 69:
            return self.rng() < 128
        return t <= 189

    # ---- the four turn routines: 62372 ($F3A4) left, 62414 ($F3CE) right, 62459 ($F3FB) down, 62484 ($F414) up ----
    def turn_left(self, e):
        if (e[2] & 192) != 128:
            if self.blocked_tile(e[0] - 1, e[1]):
                return
            e[0] -= 1
        e[2] &= 63

    def turn_right(self, e):
        if self.blocked_tile(e[0] + 3, e[1]) or self.blocked_tile(e[0] + 3, e[1] + 1):
            return
        e[2] = (e[2] & ~0x40) | 0x80

    def turn_down(self, e):
        if (e[2] & 192) not in (0, 192):
            e[0] += 1
        e[2] = (e[2] & ~0x80) | 0x40

    def turn_up(self, e):
        if (e[2] & 192) not in (0, 64):
            e[0] += 1
        e[2] |= 192

    def turn(self, e):
        """$F2D2 (62162): a blocked vehicle picks a new heading from one random byte (bins 0-41/213-255, 42-84, 85-212)."""
        h = e[2] & 192
        a = self.rng()
        main, uturn, other = {0: (self.turn_up, self.turn_right, self.turn_down),
                              128: (self.turn_down, self.turn_left, self.turn_up),
                              64: (self.turn_right, self.turn_up, self.turn_left),
                              192: (self.turn_left, self.turn_down, self.turn_right)}[h]
        if not jp_m(a, 85):
            main(e)
        elif jp_m(a, 170):
            uturn(e)
        else:
            other(e)

    def update(self):
        """$F1CC (61900): every vehicle takes one step if the two tiles on its leading edge are free, else it turns."""
        for e in self.table:
            x, y, h = e[0], e[1], e[2] & 192
            if h == 0:
                a, b, dx, dy = (x - 1, y), (x - 1, y + 1), -1, 0
            elif h == 128:
                a, b, dx, dy = (x + 3, y), (x + 3, y + 1), 1, 0
            elif h == 64:
                a, b, dx, dy = (x, y + 2), (x + 1, y + 2), 0, 1
            else:
                a, b, dx, dy = (x, y - 1), (x + 1, y - 1), 0, -1
            if self.blocked_tile(*a) or self.blocked_tile(*b):
                self.turn(e)
            else:
                e[0] += dx
                e[1] += dy

    @staticmethod
    def size(e):
        """(width, height) in tiles: 3 x 2 moving left or right, 2 x 2 moving up or down ($D8F9 uses bit 6 of the heading)."""
        return (2 if e[2] & 0x40 else 3), 2

    def hits(self, px, py):
        """$D8F9 (55545): does the player's 2x2 overlap any vehicle's footprint? Returns the first one or None."""
        for e in self.table:
            w, h = self.size(e)
            if e[0] < px + 2 and px < e[0] + w and e[1] < py + 2 and py < e[1] + h:
                return e
        return None
