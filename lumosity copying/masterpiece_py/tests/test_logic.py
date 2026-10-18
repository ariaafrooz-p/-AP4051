"""unittest suite, part 1: data, geometry, scoring, puzzle rules, the game loop and the drawing primitives.

Run everything:   python -m unittest discover -s tests -v
Run one class:    python -m unittest tests.test_logic.ScoringTests -v     (from the project folder)
"""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import *          # noqa: E402,F401,F403  (core's names + the shared helpers)

DATA = None


def setUpModule():
    global DATA
    DATA = GameData()          # parsing 5,152 puzzles takes a moment: do it once for the whole module


class DataTests(unittest.TestCase):
    def test_piece_and_puzzle_counts(self):
        self.assertEqual(len(DATA.shapes), 23)
        self.assertEqual(sum(len(v) for v in DATA.levels.values()), 5152)

    def test_level_range(self):
        self.assertEqual((min(DATA.level_keys), max(DATA.level_keys)), (0, 38))
        self.assertEqual(DATA.level_keys, sorted(DATA.level_keys))

    def test_every_shape_has_a_smooth_outline(self):
        self.assertEqual(set(DATA.outlines), set(DATA.shapes))
        for name, poly in DATA.outlines.items():
            with self.subTest(piece=name):
                self.assertGreaterEqual(len(poly), 3)

    def test_every_puzzle_uses_known_pieces_and_one_to_nine_of_them(self):
        for sils in DATA.levels.values():
            for sil in sils:
                self.assertTrue(1 <= len(sil) <= 9)
                for cls, _rot, _x, _y in sil:
                    self.assertIn(cls, DATA.shapes)

    def test_rotations_in_the_data_are_multiples_of_the_piece_step(self):
        for sils in DATA.levels.values():
            for sil in sils:
                for cls, rot, _x, _y in sil:
                    st = step_for(cls)
                    r = rot % st
                    self.assertTrue(math.isclose(r, 0, abs_tol=1e-6) or math.isclose(r, st, abs_tol=1e-6), (cls, rot))

    def test_rotate_arrow_is_loaded(self):
        self.assertGreater(len(DATA.arrow), 10)

    def test_intro_description_matches_the_window(self):
        self.assertIsNotNone(DATA.intro)
        self.assertEqual(DATA.intro["width"], DATA.intro["x_end"] + Game.W)
        self.assertEqual(DATA.intro["height"], Game.H)


class GeometryTests(unittest.TestCase):
    def test_xform_rotates_counter_clockwise(self):
        (x, y), = xform([(1.0, 0.0)], 90)
        self.assertAlmostEqual(x, 0.0, places=9)
        self.assertAlmostEqual(y, 1.0, places=9)

    def test_xform_translates_after_rotating(self):
        (x, y), = xform([(1.0, 0.0)], 180, 5, -3)
        self.assertAlmostEqual(x, 4.0, places=9)
        self.assertAlmostEqual(y, -3.0, places=9)

    def test_centroid_of_a_square(self):
        self.assertEqual(centroid([(0, 0), (2, 0), (2, 2), (0, 2)]), (1.0, 1.0))

    def test_poly_match_ignores_vertex_order(self):
        a = [(0, 0), (10, 0), (10, 10)]
        self.assertTrue(poly_match(a, [(10, 10), (0, 0), (10, 0)]))

    def test_poly_match_tolerance_and_size(self):
        a = [(0, 0), (10, 0), (10, 10)]
        self.assertTrue(poly_match(a, [(x + 5, y) for x, y in a], tol=12))
        self.assertFalse(poly_match(a, [(x + 20, y) for x, y in a], tol=12))
        self.assertFalse(poly_match(a, a + [(0, 10)]))

    def test_point_in_poly_handles_a_concave_shape(self):
        ell = [(0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4)]
        for pt in ((1, 1), (3, 1), (1, 3)):
            with self.subTest(inside=pt):
                self.assertTrue(point_in_poly(pt, ell))
        for pt in ((3, 3), (5, 1), (-1, 2)):
            with self.subTest(outside=pt):
                self.assertFalse(point_in_poly(pt, ell))

    def test_bbox_covers_all_polygons(self):
        self.assertEqual(bbox([[(0, 1), (2, 5)], [(-1, 3)]]), (-1, 1, 2, 5))

    def test_step_for_piece_families(self):
        for name in DATA.shapes:
            with self.subTest(piece=name):
                self.assertEqual(step_for(name), 60 if name.startswith("Polyiamond") else 45)

    def test_collider_polygons_tile_the_puzzles_without_overlap(self):
        rng = random.Random(1)
        for _ in range(40):
            sil = rng.choice(DATA.levels[rng.choice(DATA.level_keys)])
            self.assertLess(overlap_fraction(DATA, sil), 0.02)


class ScoringTests(unittest.TestCase):
    def test_round_up_to_ten(self):
        for value, expected in ((0, 0), (0.1, 10), (10, 10), (10.01, 20), (41, 50), (99.9, 100)):
            with self.subTest(value=value):
                self.assertEqual(round_up_to_ten(value), expected)

    def test_penalty_table(self):
        # penalty = per * (budget - min(moves, 2*budget)), per = 10 * (100 // budget), never below -score
        cases = [
            (1000, 3, 3, 0), (1000, 2, 3, 0),            # within budget
            (1000, 5, 4, -250), (1000, 6, 4, -500),      # over budget
            (1000, 99, 4, -1000),                        # capped at twice the budget
            (200, 5, 4, -200), (500, 9, 4, -500),        # never more than the score
            (1000, 130, 101, 0),                         # 100 // 101 == 0: no per-rotation cost
        ]
        for score, moves, budget, expected in cases:
            with self.subTest(score=score, moves=moves, budget=budget):
                self.assertEqual(penalty(score, moves, budget), expected)

    def test_penalty_can_be_disabled(self):
        self.assertEqual(penalty(1000, 9, 4, enabled=False), 0)

    def test_penalty_ignores_a_zero_budget(self):
        self.assertEqual(penalty(1000, 9, 0), 0)

    def test_next_score_level_moves_toward_the_target(self):
        self.assertAlmostEqual(Referee.next_score_level(10, 20), 15.0)      # up: half way
        self.assertAlmostEqual(Referee.next_score_level(10, 2), 8.0)        # down is damped
        self.assertEqual(Referee.next_score_level(1, -50), 0)               # floored at the minimum

    def test_pick_silhouette_returns_the_nearest_available_level(self):
        ref = Referee(DATA, random.Random(1))
        for level, expected in ((8.0, 8), (8.9, 8), (9.1, 10), (-5, 0), (99, 38), (5.0, 5)):
            ref.level = level
            key, sil = ref.pick_silhouette()
            with self.subTest(level=level):
                self.assertEqual(key, expected)
                self.assertIn(sil, DATA.levels[key])

    def _score(self, extra_moves=0, hints=0, seconds=5.0):
        puzzle = Puzzle(DATA, DATA.levels[12][3], random.Random(5))
        puzzle.moves = puzzle.budget + extra_moves
        puzzle.hints = hints
        return Referee(DATA, random.Random(1)).score_trial(puzzle, seconds, 12), puzzle

    def test_fewer_rotations_score_more(self):
        perfect, puzzle = self._score(0)
        one_over, _ = self._score(1)
        far_over, _ = self._score(50)
        self.assertEqual(perfect["rating"], "PERFECT")
        self.assertEqual(one_over["rating"], "GREAT")
        self.assertEqual(far_over["rating"], "OK")
        self.assertGreater(perfect["points"], one_over["points"])
        self.assertEqual(far_over["points"], 0)
        self.assertEqual(perfect["points"] % 10, 0)
        self.assertEqual(perfect["budget"], puzzle.budget)

    def test_hints_cost_points_and_the_perfect_rating(self):
        clean, _ = self._score(0, hints=0)
        hinted, _ = self._score(0, hints=1)
        self.assertLess(hinted["points"], clean["points"])
        self.assertNotEqual(hinted["rating"], "PERFECT")

    def test_perfect_and_fast_raises_the_level_and_slow_sloppy_play_lowers_it(self):
        ref = Referee(DATA, random.Random(1))
        start = ref.level
        puzzle = Puzzle(DATA, DATA.levels[12][3], random.Random(5))
        puzzle.moves = puzzle.budget
        ref.score_trial(puzzle, 1.0, 12)
        self.assertGreater(ref.level, start)
        high = ref.level
        puzzle.moves = puzzle.budget * 5
        ref.score_trial(puzzle, 999.0, 12)
        self.assertLess(ref.level, high)
        self.assertEqual(ref.total, sum(r["points"] for r in ref.results))

    def test_response_time_budget_grows_with_the_level(self):
        ref = Referee(DATA, random.Random(1))
        ref.level = MIN_LEVEL
        low = ref.response_seconds()
        ref.level = MAX_LEVEL
        self.assertLess(low, ref.response_seconds())


class PuzzleTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(3)

    def single_square(self):
        return Puzzle(DATA, [("Square", 0, 0, 0)], self.rng)

    def test_scramble_needs_at_least_one_rotation(self):
        for seed in range(30):
            rng = random.Random(seed)
            pz = Puzzle(DATA, rng.choice(DATA.levels[rng.choice(DATA.level_keys)]), rng)
            with self.subTest(seed=seed):
                self.assertGreaterEqual(pz.budget, 1)
                for piece in pz.pieces:                        # start orientations are whole steps away from the target
                    st = step_for(piece.cls)
                    r = (piece.rot - pz.slots[piece.id].rot) % st
                    self.assertLess(min(r, st - r), 1e-6)

    def test_steps_needed_uses_the_cheapest_direction(self):
        pz = self.single_square()
        for cls, start, target, expected in (("Triangle40", 180, 0, 4), ("Triangle40", 45, 0, 1),
                                             ("Triangle40", 315, 0, 1), ("Triangle40", 0, 0, 0)):
            with self.subTest(piece=cls, start=start):
                self.assertEqual(pz.steps_needed(cls, start, target), expected)

    def test_a_square_is_symmetric_every_quarter_turn(self):
        pz = self.single_square()
        for start, expected in ((0, 0), (90, 0), (180, 0), (270, 0), (45, 1), (135, 1)):
            with self.subTest(start=start):
                self.assertEqual(pz.steps_needed("Square", start, 0), expected)

    def test_piece_snaps_when_close_and_correctly_oriented(self):
        pz = self.single_square()
        piece, slot = pz.pieces[0], pz.slots[0]
        piece.rot = slot.rot
        target = centroid(slot.poly)
        piece.x, piece.y = target[0] + 20, target[1] - 15
        pz.drop(piece)
        self.assertIs(piece.slot, slot)
        self.assertIs(slot.piece, piece)
        got = centroid(pz.poly_of(piece))
        self.assertAlmostEqual(got[0], target[0], places=6)
        self.assertAlmostEqual(got[1], target[1], places=6)
        self.assertTrue(pz.is_solved())

    def test_piece_does_not_snap_when_too_far(self):
        pz = self.single_square()
        piece, slot = pz.pieces[0], pz.slots[0]
        piece.rot = slot.rot
        target = centroid(slot.poly)
        piece.x, piece.y = target[0] + pz.snap_radius + 40, target[1]
        pz.drop(piece)
        self.assertIsNone(piece.slot)
        self.assertFalse(pz.is_solved())

    def test_piece_does_not_snap_with_the_wrong_orientation(self):
        pz = self.single_square()
        piece, slot = pz.pieces[0], pz.slots[0]
        piece.rot = slot.rot + 45
        target = centroid(slot.poly)
        piece.x, piece.y = target[0], target[1]
        pz.drop(piece)
        self.assertIsNone(piece.slot)

    def test_picking_a_snapped_piece_frees_its_slot_and_moves_it_to_the_top(self):
        pz = self.single_square()
        piece, slot = pz.pieces[0], pz.slots[0]
        piece.rot = slot.rot
        piece.x, piece.y = centroid(slot.poly)
        pz.drop(piece)
        self.assertIs(slot.piece, piece)
        pz.pick(piece)
        self.assertIsNone(slot.piece)
        self.assertIsNone(piece.slot)
        self.assertIs(pz.order[-1], piece)

    def test_snapped_pieces_sit_under_loose_ones(self):
        sil = [("Square", 0, -80, 0), ("Square", 0, 80, 0)]
        pz = Puzzle(DATA, sil, self.rng)
        first, second = pz.pieces
        first.rot = pz.slots[0].rot
        first.x, first.y = centroid(pz.slots[0].poly)
        pz.drop(first)
        self.assertEqual(pz.order[0], first)

    def test_rotate_counts_moves_and_turns_by_one_step(self):
        pz = self.single_square()
        piece = pz.pieces[0]
        piece.rot, piece.x, piece.y = 0, 500, 500                       # far from any slot: stays loose
        pz.rotate(piece, 1)
        self.assertEqual((pz.moves, piece.rot), (1, 45))
        pz.rotate(piece, -1)
        pz.rotate(piece, -1)
        self.assertEqual((pz.moves, piece.rot), (3, 315))

    def test_rotating_a_snapped_piece_unlocks_it(self):
        pz = self.single_square()
        piece, slot = pz.pieces[0], pz.slots[0]
        piece.rot = slot.rot
        piece.x, piece.y = centroid(slot.poly)
        pz.drop(piece)
        pz.rotate(piece, 1)
        self.assertIsNone(slot.piece)
        self.assertIsNone(piece.slot)

    def test_hint_points_at_an_empty_slot_and_counts(self):
        pz = Puzzle(DATA, DATA.levels[12][0], self.rng)
        slot = pz.hint()
        self.assertIn(slot, pz.slots)
        self.assertIs(pz.hint_slot, slot)
        self.assertEqual(pz.hints, 1)
        self.assertEqual(pz.hint_piece.cls, slot.cls)
        self.assertIsNone(pz.hint_piece.slot)

    def test_hint_returns_none_when_nothing_is_left(self):
        pz = self.single_square()
        piece, slot = pz.pieces[0], pz.slots[0]
        piece.rot = slot.rot
        piece.x, piece.y = centroid(slot.poly)
        pz.drop(piece)
        self.assertIsNone(pz.hint())
        self.assertEqual(pz.hints, 0)

    def test_coverage_accepts_exact_placement_and_rejects_a_shifted_one(self):
        pz = Puzzle(DATA, DATA.levels[12][0], self.rng)
        taken = set()
        for p in pz.pieces:
            s = next(s for s in pz.slots if s.cls == p.cls and id(s) not in taken)
            taken.add(id(s))
            p.rot, p.x, p.y = s.rot, s.x, s.y
        self.assertTrue(pz.is_solved())
        cov, over, out = pz.coverage()
        self.assertGreater(cov, 0.97)
        for p in pz.pieces:
            p.x += 25
        self.assertFalse(pz.is_solved())

    def test_hit_test_returns_the_topmost_piece_and_none_on_empty_space(self):
        pz = Puzzle(DATA, [("Square", 0, 0, 0), ("Square", 0, 0, 0)], self.rng)
        a, b = pz.pieces
        for p in (a, b):
            p.rot, p.x, p.y = 0, 0.0, 0.0
        self.assertIs(pz.hit_test(0, 0), pz.order[-1])
        pz.pick(a)
        self.assertIs(pz.hit_test(0, 0), a)
        self.assertIsNone(pz.hit_test(900, 900))

    def test_start_layout_is_visible_and_pieces_do_not_overlap(self):
        view = dict(board=Game.BOARD_RECT, center=(Game.CX, Game.CY), max_scale=1.36,
                    play=(8, 52, Game.W - 8, Game.BAR_Y - 8))
        for seed in range(25):
            rng = random.Random(seed)
            pz = Puzzle(DATA, rng.choice(DATA.levels[rng.choice(DATA.level_keys)]), rng, view)
            polys = [pz.draw_poly_of(p) for p in pz.pieces]
            with self.subTest(seed=seed):
                for poly in polys:
                    xs = [Game.CX + x * pz.S for x, _ in poly]
                    ys = [Game.CY - y * pz.S for _, y in poly]
                    self.assertGreater(min(xs), 7)
                    self.assertLess(max(xs), Game.W - 7)
                    self.assertGreater(min(ys), 51)
                    self.assertLess(max(ys), Game.BAR_Y - 7)
                for i in range(len(polys)):
                    for j in range(i + 1, len(polys)):
                        inside = total = 0
                        x0, y0, x1, y1 = bbox([polys[i]])
                        y = y0 + 1.3
                        while y < y1:
                            x = x0 + 1.1
                            while x < x1:
                                if point_in_poly((x, y), polys[i]):
                                    total += 1
                                    inside += point_in_poly((x, y), polys[j])
                                x += 8
                            y += 8
                        self.assertLess(inside / max(total, 1), 0.05)

    def test_the_silhouette_scale_fits_the_board(self):
        view = dict(board=Game.BOARD_RECT, center=(Game.CX, Game.CY), max_scale=1.36)
        rng = random.Random(8)
        for key in DATA.level_keys:
            pz = Puzzle(DATA, DATA.levels[key][0], rng, view)
            with self.subTest(level=key):
                self.assertLessEqual(pz.S, 1.36)
                self.assertLessEqual(pz.sil_h * pz.S, 0.5 * (Game.BOARD_RECT[3] - Game.BOARD_RECT[1]) + 1e-6)


class GameFlowTests(unittest.TestCase):
    def test_a_new_game_starts_on_the_first_trial(self):
        g = Game(DATA, seed=2)
        self.assertEqual((g.state, g.trial, g.referee.total), ("playing", 1, 0))

    def test_same_seed_gives_the_same_game(self):
        a, b, c = Game(DATA, seed=7), Game(DATA, seed=7), Game(DATA, seed=8)
        pos = lambda g: [(p.cls, round(p.x, 6), round(p.y, 6), p.rot) for p in g.puzzle.pieces]
        self.assertEqual(pos(a), pos(b))
        self.assertNotEqual(pos(a), pos(c))

    def test_optimal_play_is_perfect_every_time_and_ends_on_the_summary(self):
        g = Game(DATA, seed=7)
        for trial in range(TRIALS_PER_GAME):
            self.assertEqual(g.state, "playing")
            solve_perfectly(g)
            self.assertEqual(g.state, "solved")
            self.assertEqual(g.last["rating"], "PERFECT")
            self.assertEqual(g.last["moves"], g.last["budget"])
            self.assertGreater(g.last["points"], 0)
            g.key("space")
        self.assertEqual(g.state, "summary")
        self.assertEqual(len(g.referee.results), TRIALS_PER_GAME)
        self.assertEqual(g.referee.total, sum(r["points"] for r in g.referee.results))

    def test_play_again_after_the_summary_resets_everything(self):
        g = Game(DATA, seed=7)
        for _ in range(TRIALS_PER_GAME):
            solve_perfectly(g)
            g.key("space")
        g.key("space")
        self.assertEqual((g.state, g.trial, g.referee.total), ("playing", 1, 0))

    def test_the_level_rises_while_playing_perfectly(self):
        g = Game(DATA, seed=11)
        start = g.referee.level
        for _ in range(3):
            solve_perfectly(g)
            g.key("space")
        self.assertGreater(g.referee.level, start)

    def test_the_clock_only_runs_while_playing(self):
        g = Game(DATA, seed=2)
        g.tick(1.5)
        self.assertAlmostEqual(g.elapsed, 1.5)
        g.key("p")
        g.tick(10)
        self.assertAlmostEqual(g.elapsed, 1.5)

    def test_a_hint_expires(self):
        g = Game(DATA, seed=4)
        g.action("hint")
        self.assertIsNotNone(g.puzzle.hint_slot)
        g.tick(Game.HINT_SECONDS + 0.5)
        self.assertIsNone(g.puzzle.hint_slot)
        self.assertIsNone(g.puzzle.hint_piece)

    def test_rotating_needs_a_selected_piece(self):
        g = Game(DATA, seed=4)
        g.key("q")
        self.assertEqual(g.puzzle.moves, 0)
        pc = g.puzzle.pieces[0]
        x, y = inside_point(g.puzzle.draw_poly_of(pc))
        g.mouse_down(*g.w2p(x, y))
        g.mouse_up(*g.w2p(x, y))
        g.key("q")
        g.key("e")
        self.assertEqual(g.puzzle.moves, 2)

    def test_dragging_moves_the_piece_with_the_mouse(self):
        g = Game(DATA, seed=4)
        pc = g.puzzle.pieces[0]
        x, y = inside_point(g.puzzle.draw_poly_of(pc))
        px, py = g.w2p(x, y)
        before = (pc.x, pc.y)
        g.mouse_down(px, py)
        g.mouse_move(px + 30, py + 15)
        g.mouse_up(px + 30, py + 15)
        self.assertAlmostEqual(pc.x - before[0], 30 / g.S, places=6)
        self.assertAlmostEqual(pc.y - before[1], -15 / g.S, places=6)

    def test_coordinate_round_trip(self):
        g = Game(DATA, seed=4)
        for wx, wy in ((0, 0), (123.4, -56.7), (-200, 150)):
            self.assertEqual([round(v, 6) for v in g.p2w(*g.w2p(wx, wy))], [wx, wy])


class SceneTests(unittest.TestCase):
    """Every drawing primitive must be well formed, in every screen the game can show (the view trusts them blindly)."""
    SHAPES = {"rect": 7, "poly": (5, 6), "text": 8, "image": 4, "line": 4, "oval": 8}

    def check(self, game):
        for prim in game.scene():
            kind = prim[0]
            self.assertIn(kind, self.SHAPES)
            want = self.SHAPES[kind]
            self.assertIn(len(prim), want if isinstance(want, tuple) else (want,), prim[:2])
            numbers = []
            if kind in ("rect", "oval"):
                numbers = list(prim[1:5])
            elif kind in ("poly", "line"):
                numbers = [v for pt in (prim[1]) for v in pt]
            elif kind in ("text", "image"):
                numbers = list(prim[1:3])
            for v in numbers:
                self.assertTrue(math.isfinite(v), prim[:2])
            if kind == "image":
                self.assertTrue(os.path.exists(prim[3]), prim[3])

    def test_playing(self):
        self.check(Game(DATA, seed=2))

    def test_paused_and_how_to_play(self):
        g = Game(DATA, seed=2)
        g.key("p")
        self.check(g)
        click_menu_item(g, "howto")
        self.check(g)

    def test_intro(self):
        g = Game(DATA, seed=2, intro=True)
        for dt in (0.0, 1.0, 2.0, 2.0, 2.0):
            g.tick(dt)
            self.check(g)

    def test_solved_and_summary(self):
        g = Game(DATA, seed=2)
        for _ in range(TRIALS_PER_GAME):
            solve_perfectly(g)
            self.check(g)
            g.key("space")
        self.check(g)

    def test_with_hover_hint_and_a_held_piece(self):
        g = Game(DATA, seed=2)
        pc = g.puzzle.pieces[0]
        x, y = inside_point(g.puzzle.draw_poly_of(pc))
        g.mouse_down(*g.w2p(x, y))
        g.mouse_up(*g.w2p(x, y))
        g.action("hint")
        g.key("e")
        g.hover_at(10, 10)
        self.check(g)


if __name__ == "__main__":
    unittest.main()
