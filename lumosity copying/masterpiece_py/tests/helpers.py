"""Shared helpers for the test suites (the tests/test_core.py script and the tests/test_game.py unittest suite)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core import *


def overlap_fraction(data, sil):
    polys = [xform(data.shapes[c], r, x, y) for c, r, x, y in sil]
    x0, y0, x1, y1 = bbox(polys)
    cov = over = 0
    y = y0 + 0.3719                       # off-grid samples (grid-aligned ones land on shared edges)
    while y <= y1:
        x = x0 + 0.2131
        while x <= x1:
            n = sum(point_in_poly((x, y), p) for p in polys)
            cov += n >= 1
            over += n >= 2
            x += 5
        y += 5
    return over / max(cov, 1)


def inside_point(poly):
    """A point guaranteed to be inside the polygon (the pivot can lie outside concave pieces)."""
    c = centroid(poly)
    if point_in_poly(c, poly):
        return c
    x0, y0, x1, y1 = bbox([poly])
    y = y0
    while y <= y1:
        x = x0
        while x <= x1:
            if point_in_poly((x + 0.31, y + 0.17), poly):
                return (x + 0.31, y + 0.17)
            x += 3
        y += 3
    raise AssertionError("no interior point")


def solve_perfectly(game):
    """Play the current trial optimally through the public mouse/key API.
    Uses the pairing piece i <-> slot i, which is the pairing the rotation budget is defined on."""
    pz = game.puzzle
    for piece in list(pz.pieces):
        slot = pz.slots[piece.id]
        shape = pz.data.shapes[piece.cls]
        # select the piece with a click inside it
        cx, cy = inside_point(pz.draw_poly_of(piece))
        px, py = game.w2p(cx, cy)
        game.mouse_down(px, py)
        game.mouse_up(px, py)
        assert game.selected is piece, (piece.cls, game.selected and game.selected.cls)
        # rotate the shortest way
        st = step_for(piece.cls)
        n = 360 // st
        # symmetric pieces match at several rotations: take the cheapest one (either direction)
        ccw = min((j for j in range(n) if poly_match(xform(shape, piece.rot + j * st), xform(shape, slot.rot), 1.0)),
                  key=lambda j: min(j, n - j))
        for _ in range(min(ccw, n - ccw)):
            game.action("rotl" if ccw <= n - ccw else "rotr")
        # drag it close to (not exactly on) its slot and release
        pc = centroid(pz.poly_of(piece))
        sc = centroid(slot.poly)
        cx, cy = inside_point(pz.draw_poly_of(piece))
        game.mouse_down(*game.w2p(cx, cy))
        tx, ty = game.w2p(cx + sc[0] - pc[0] + 9, cy + sc[1] - pc[1] - 7)
        game.mouse_move(tx, ty)
        game.mouse_up(tx, ty)


class FakeBackend:
    """Stands in for a sound card: records what the Audio layer asks it to do."""
    name = "fake"

    def __init__(self, fail_on=()):
        self.loaded, self.played, self.stopped, self.closed = {}, [], [], False
        self.fail_on = set(fail_on)

    def load(self, name, path):
        if name in self.fail_on:
            raise OSError("cannot load " + name)
        self.loaded[name] = path

    def play(self, name):
        self.played.append(name)

    def stop(self, name):
        self.stopped.append(name)

    def close(self):
        self.closed = True


def menu_center(key):
    ya, yb = MENU_Y[[k for k, _ in MENU_ITEMS].index(key)]
    return (MENU_X[0] + MENU_X[1]) / 2.0, (ya + yb) / 2.0


def click_menu_item(game, key):
    x, y = menu_center(key)
    game.mouse_down(x, y)
    game.mouse_up(x, y)


def scene_texts(game):
    return [p[3] for p in game.scene() if p[0] == "text"]


def has_rect(game, box, color):
    return any(p[0] == "rect" and tuple(p[1:5]) == tuple(box) and p[5] == color for p in game.scene())


def button(name):
    return next(b for b in Game.BUTTONS if b[0] == name)


def button_center(name):
    _, x0, y0, x1, y1 = button(name)
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0
