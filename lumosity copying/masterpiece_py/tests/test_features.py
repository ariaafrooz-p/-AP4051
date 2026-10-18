"""unittest suite, part 2: pause menu, intro pan, hover / pressed effects and the sound events the game emits.

Run everything:   python -m unittest discover -s tests -v
"""
import os
import random
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import *          # noqa: E402,F401,F403

try:
    import numpy as np
    from PIL import Image
except ImportError:            # the pixel-level asset checks are skipped without them
    np = Image = None

DATA = None
UI = "#30bdeb"


def setUpModule():
    global DATA
    DATA = GameData()


def hold_a_piece(game, index=0):
    """Click a piece (select it) and release the mouse, like a player tapping it."""
    pc = game.puzzle.pieces[index]
    x, y = inside_point(game.puzzle.draw_poly_of(pc))
    game.mouse_down(*game.w2p(x, y))
    game.mouse_up(*game.w2p(x, y))
    return pc


class PauseMenuTests(unittest.TestCase):
    def setUp(self):
        self.g = Game(DATA, seed=2)
        self.g.drain_events()

    def test_pause_keys_toggle_the_menu(self):
        for key in ("p", "escape"):
            with self.subTest(key=key):
                self.g.key(key)
                self.assertEqual(self.g.state, "paused")
                self.g.key(key)
                self.assertEqual(self.g.state, "playing")

    def test_the_pause_button_opens_the_menu(self):
        self.g.mouse_down(*button_center("pause"))
        self.assertEqual(self.g.state, "paused")

    def test_each_screen_has_its_own_background(self):
        self.assertTrue(self.g.static_scene()[0][3].endswith("background.png"))
        self.g.key("p")
        self.assertTrue(self.g.static_scene()[0][3].endswith("pause.png"))
        click_menu_item(self.g, "howto")
        self.assertTrue(self.g.static_scene()[0][3].endswith("wood.png"))

    def test_all_six_items_are_listed(self):
        self.g.key("p")
        self.assertEqual([lab for _, lab in MENU_ITEMS],
                         ["Resume", "Restart", "Mute Sound", "Mute Music", "Quit", "How To Play"])
        for _, lab in MENU_ITEMS:
            self.assertIn(lab, scene_texts(self.g))

    def test_three_ways_to_resume(self):
        for how in ("item", "tag", "key"):
            with self.subTest(how=how):
                g = Game(DATA, seed=2)
                g.key("p")
                if how == "item":
                    click_menu_item(g, "resume")
                elif how == "tag":
                    g.mouse_down(10, 10)
                else:
                    g.key("p")
                self.assertEqual(g.state, "playing")

    def test_the_gap_between_two_items_does_nothing(self):
        self.g.key("p")
        gap_y = (MENU_Y[0][1] + MENU_Y[1][0]) / 2.0
        self.g.mouse_down(472, gap_y)
        self.assertEqual(self.g.state, "paused")

    def test_mute_items_flip_flags_and_labels(self):
        self.g.key("p")
        for key, flag, label in (("mute_sound", "sound_muted", "Sound"), ("mute_music", "music_muted", "Music")):
            with self.subTest(item=key):
                click_menu_item(self.g, key)
                self.assertTrue(getattr(self.g, flag))
                self.assertIn("Unmute " + label, scene_texts(self.g))
                self.assertNotIn("Mute " + label, scene_texts(self.g))
                click_menu_item(self.g, key)
                self.assertFalse(getattr(self.g, flag))
                self.assertIn("Mute " + label, scene_texts(self.g))

    def test_quit_asks_the_view_to_close(self):
        self.g.key("p")
        self.assertFalse(self.g.quit_requested)
        click_menu_item(self.g, "quit")
        self.assertTrue(self.g.quit_requested)

    def test_restart_starts_over_with_a_clean_score(self):
        solve_perfectly(self.g)
        self.g.key("space")
        self.assertEqual(self.g.trial, 2)
        self.assertGreater(self.g.referee.total, 0)
        self.g.key("p")
        click_menu_item(self.g, "restart")
        self.assertEqual((self.g.state, self.g.trial, self.g.referee.total, self.g.puzzle.moves),
                         ("playing", 1, 0, 0))

    def test_how_to_play_opens_and_any_click_goes_back(self):
        self.g.key("p")
        click_menu_item(self.g, "howto")
        self.assertEqual(self.g.state, "howto")
        self.assertIn("How To Play", scene_texts(self.g))
        self.g.mouse_down(300, 300)
        self.assertEqual(self.g.state, "paused")
        click_menu_item(self.g, "howto")
        self.g.key("p")
        self.assertEqual(self.g.state, "paused")

    def test_nothing_in_the_game_reacts_while_paused(self):
        hold_a_piece(self.g)
        self.g.key("p")
        for key in ("q", "e", "h"):
            self.g.key(key)
        self.assertEqual((self.g.puzzle.moves, self.g.puzzle.hints), (0, 0))
        self.assertFalse(any(p[0] == "poly" and p[2] == CYAN for p in self.g.scene()))


class IntroTests(unittest.TestCase):
    def setUp(self):
        self.g = Game(DATA, seed=12, intro=True)
        self.x_end = DATA.intro["x_end"]

    def run_to_the_end(self, dt=0.05, limit=400):
        events = []
        for _ in range(limit):
            if self.g.state != "intro":
                break
            self.g.tick(dt)
            events += self.g.drain_events()
        return events

    def test_a_game_with_the_intro_option_starts_in_the_intro(self):
        self.assertEqual(self.g.state, "intro")
        self.assertEqual(self.g.drain_events(), ["game_start"])
        self.assertTrue(self.g.static_scene()[0][3].endswith("wood.png"))      # the wood is fixed on screen

    def test_the_intro_draws_the_desk_the_hud_but_not_the_bottom_bar(self):
        prims = self.g.dynamic_scene()
        images = [p for p in prims if p[0] == "image"]
        self.assertTrue(images[0][3].endswith("intro_world.png"))
        self.assertEqual(images[0][1], 0)
        self.assertTrue(images[1][3].endswith("hud.png"))
        texts = [p[3] for p in prims if p[0] == "text"]
        self.assertIn("PUZZLE 1 of 4", texts)
        self.assertNotIn("HINT", texts)

    def test_it_rests_then_pans_smoothly_to_the_board(self):
        self.g.tick(INTRO_HOLD * 0.5)
        self.assertEqual(self.g.cam_x, 0)
        last = -1.0
        while self.g.state == "intro":
            self.g.tick(0.05)
            self.assertGreaterEqual(self.g.cam_x, last - 1e-9)
            self.assertTrue(0 <= self.g.view_dx <= self.x_end)
            last = self.g.cam_x
        self.assertEqual(self.g.state, "playing")
        self.assertEqual(self.g.view_dx, 0)

    def test_the_intro_lasts_hold_plus_pan_and_the_clock_starts_after_it(self):
        self.run_to_the_end(dt=0.05)
        self.assertAlmostEqual(self.g.intro_t, INTRO_HOLD + INTRO_PAN, delta=0.06)
        self.assertEqual(self.g.elapsed, 0.0)
        self.g.tick(1.0)
        self.assertAlmostEqual(self.g.elapsed, 1.0)

    def test_the_wood_slide_sound_plays_once_when_the_pan_starts(self):
        self.g.drain_events()
        events = self.run_to_the_end()
        self.assertEqual(events.count("slide"), 1)

    def test_a_huge_time_step_still_finishes_cleanly(self):
        self.g.tick(1000)
        self.assertEqual((self.g.state, self.g.view_dx, self.g.elapsed), ("playing", 0, 0.0))

    def test_board_items_travel_with_the_desk(self):
        ref = Game(DATA, seed=12)
        mine = [p for p in self.g.dynamic_scene() if p[0] == "poly"]
        theirs = [p for p in ref.dynamic_scene() if p[0] == "poly"][:len(mine)]
        for a, b in zip(mine, theirs):
            for (xa, ya), (xb, yb) in zip(a[1], b[1]):
                self.assertAlmostEqual(xa - xb, self.x_end, places=6)
                self.assertAlmostEqual(ya, yb, places=6)

    def test_after_the_pan_the_screen_equals_the_normal_game_screen(self):
        self.run_to_the_end()
        ref = Game(DATA, seed=12)
        strip = lambda g: [p for p in g.dynamic_scene() if p[0] != "image"]
        self.assertEqual(strip(self.g), strip(ref))
        self.assertTrue(self.g.static_scene()[0][3].endswith("background.png"))

    def test_skipping(self):
        for how in ("click", "space", "return", "escape"):
            with self.subTest(how=how):
                g = Game(DATA, seed=3, intro=True)
                g.tick(1.0)
                g.mouse_down(300, 300) if how == "click" else g.key(how)
                self.assertEqual((g.state, g.view_dx, g.puzzle.moves), ("playing", 0, 0))

    def test_other_keys_do_nothing_during_the_intro(self):
        for key in ("q", "e", "h", "p", "left"):
            with self.subTest(key=key):
                self.g.key(key)
                self.assertEqual(self.g.state, "intro")
        self.assertEqual((self.g.puzzle.moves, self.g.puzzle.hints), (0, 0))

    def test_restart_and_play_again_replay_the_intro(self):
        g = Game(DATA, seed=3, intro=True)
        g.key("space")
        g.key("p")
        click_menu_item(g, "restart")
        self.assertEqual((g.state, g.cam_x, g.trial, g.referee.total), ("intro", 0, 1, 0))
        g.key("space")
        for _ in range(TRIALS_PER_GAME):
            solve_perfectly(g)
            g.key("space")
        self.assertEqual(g.state, "summary")
        g.key("space")
        self.assertEqual(g.state, "intro")

    def test_without_the_intro_option_restart_goes_straight_to_play(self):
        g = Game(DATA, seed=3)
        g.key("p")
        click_menu_item(g, "restart")
        self.assertEqual(g.state, "playing")

    def test_missing_intro_assets_fall_back_to_normal_play(self):
        with mock.patch.object(DATA, "intro", None):
            self.assertEqual(Game(DATA, seed=1, intro=True).state, "playing")

    @unittest.skipIf(np is None, "numpy / Pillow not installed")
    def test_the_last_intro_frame_equals_the_board_screen_pixel_for_pixel(self):
        with Image.open(os.path.join(DATA.folder, "intro_world.png")) as im:
            world = np.array(im.convert("RGBA"))
        with Image.open(os.path.join(DATA.folder, "background.png")) as im:
            bg = np.array(im.convert("RGB")).astype(int)
        self.assertEqual(world.shape, (Game.H, DATA.intro["width"], 4))
        bx0, by0, bx1, by1 = Game.BOARD_RECT
        last = world[:, self.x_end:self.x_end + Game.W, :3].astype(int)
        self.assertEqual(int(np.abs(last[by0:by1, bx0:bx1] - bg[by0:by1, bx0:bx1]).max()), 0)

    @unittest.skipIf(np is None, "numpy / Pillow not installed")
    def test_the_wood_stays_transparent_and_the_hud_overlay_has_alpha(self):
        with Image.open(os.path.join(DATA.folder, "intro_world.png")) as im:
            world = np.array(im.convert("RGBA"))
        self.assertEqual(world[300, 100, 3], 0)
        self.assertGreater(world[:, :, 3].mean(), 20)
        with Image.open(os.path.join(DATA.folder, "hud.png")) as hud:
            self.assertEqual((hud.mode, hud.size), ("RGBA", (Game.W, Game.H)))


class HoverAndPressTests(unittest.TestCase):
    def setUp(self):
        self.g = Game(DATA, seed=2)

    def lit(self, box):
        return has_rect(self.g, box, UI)

    def test_no_hover_until_the_mouse_position_is_known(self):
        self.g.key("p")
        self.assertIsNone(self.g.hover)

    def test_the_menu_item_under_the_mouse_turns_cyan_with_white_text(self):
        self.g.key("p")
        labels = [lab for _, lab in MENU_ITEMS]
        for (key, label), (ya, yb) in zip(MENU_ITEMS, MENU_Y):
            with self.subTest(item=key):
                self.g.hover_at(*menu_center(key))
                self.assertEqual(self.g.hover, key)
                self.assertTrue(self.lit((MENU_X[0], ya, MENU_X[1], yb)))
                colour = {p[3]: p[5] for p in self.g.scene() if p[0] == "text" and p[3] in labels}
                self.assertEqual(colour[label], "#ffffff")
                self.assertTrue(all(c == UI for l, c in colour.items() if l != label))

    def test_only_one_menu_item_is_lit_and_gaps_are_not_hover_targets(self):
        self.g.key("p")
        self.g.hover_at(*menu_center("quit"))
        self.assertEqual(sum(1 for p in self.g.scene() if p[0] == "rect" and p[5] == UI), 1)
        self.g.hover_at(472, (MENU_Y[0][1] + MENU_Y[1][0]) / 2)
        self.assertIsNone(self.g.hover)
        self.assertFalse(any(p[0] == "rect" and p[5] == UI for p in self.g.scene()))

    def test_leaving_the_window_clears_the_hover(self):
        self.g.key("p")
        self.g.hover_at(*menu_center("quit"))
        self.g.hover_at(None, None)
        self.assertIsNone(self.g.hover)

    def test_no_stale_hover_after_the_screen_changes(self):
        self.g.key("p")
        click_menu_item(self.g, "resume")            # the mouse is still over where 'Resume' was
        self.assertEqual(self.g.state, "playing")
        self.assertIsNone(self.g.hover)

    def test_the_pause_button_turns_cyan_with_white_bars_on_hover(self):
        self.g.hover_at(10, 10)
        self.assertEqual(self.g.hover, "pause")
        self.assertTrue(self.lit((0, 0, 50, 50)))
        bars = [p[5] for p in self.g.scene() if p[0] == "rect" and p[1] in (17, 28) and p[2] == 14]
        self.assertEqual(bars, ["#ffffff", "#ffffff"])
        self.g.hover_at(300, 300)
        self.assertFalse(self.lit((0, 0, 50, 50)))

    def test_bar_buttons_are_hover_targets_but_do_not_fill_on_hover(self):
        for name in ("rotl", "rotr", "hint"):
            with self.subTest(button=name):
                self.g.hover_at(*button_center(name))
                self.assertEqual(self.g.hover, name)
                self.assertFalse(self.lit(button(name)[1:5]))

    def test_no_hover_effects_while_dragging(self):
        pc = self.g.puzzle.pieces[0]
        x, y = inside_point(self.g.puzzle.draw_poly_of(pc))
        self.g.mouse_down(*self.g.w2p(x, y))
        self.g.hover_at(*button_center("rotl"))
        self.assertIsNone(self.g.hover)

    def test_a_pressed_rotate_button_fills_with_the_arrow_colour(self):
        hold_a_piece(self.g)
        rotr = button("rotr")[1:5]
        before = self.g.puzzle.moves
        self.g.mouse_down(*button_center("rotr"))
        self.assertEqual(self.g.puzzle.moves, before + 1)
        self.assertEqual(self.g.press_name, "rotr")
        self.assertTrue(self.lit(rotr))
        self.g.tick(1.0)
        self.assertTrue(self.lit(rotr), "stays cyan while the mouse button is held")
        self.g.mouse_up(*button_center("rotr"))
        self.assertFalse(self.lit(rotr), "back to normal at once after a long press")

    def test_a_quick_click_or_key_press_still_flashes_then_fades(self):
        hold_a_piece(self.g)
        for action, name in ((lambda: (self.g.mouse_down(*button_center("rotr")), self.g.mouse_up(0, 0)), "rotr"),
                             (lambda: self.g.key("q"), "rotl")):
            with self.subTest(button=name):
                action()
                self.assertTrue(self.lit(button(name)[1:5]))
                self.g.tick(0.2)
                self.assertFalse(self.lit(button(name)[1:5]))

    def test_the_flash_matches_the_button_not_the_other_one(self):
        hold_a_piece(self.g)
        self.g.key("q")
        self.assertTrue(self.lit(button("rotl")[1:5]))
        self.assertFalse(self.lit(button("rotr")[1:5]))

    def test_the_hint_button_has_no_pressed_fill(self):
        self.g.mouse_down(*button_center("hint"))
        self.assertFalse(self.lit(button("hint")[1:5]))

    def test_the_pause_button_lights_up_while_held(self):
        self.g.mouse_down(10, 10)
        self.assertEqual((self.g.state, self.g.press_name), ("paused", "pause"))
        self.g.mouse_up(10, 10)
        self.assertIsNone(self.g.press_name)

    def test_the_held_piece_is_orange_with_a_ring_on_its_pivot(self):
        pc = hold_a_piece(self.g)
        held = [p for p in self.g.scene() if p[0] == "poly" and p[2] == SELECTED]
        ovals = [p for p in self.g.scene() if p[0] == "oval"]
        self.assertEqual((len(held), len(ovals)), (1, 2))
        px, py = self.g.w2p(pc.x, pc.y)
        for o in ovals:
            self.assertAlmostEqual((o[1] + o[3]) / 2, px, places=6)
            self.assertAlmostEqual((o[2] + o[4]) / 2, py, places=6)

    def test_no_ring_when_nothing_is_held(self):
        self.assertFalse(any(p[0] == "oval" for p in self.g.scene()))

    def test_a_hint_draws_dotted_yellow_outlines(self):
        pc = hold_a_piece(self.g)
        self.assertFalse(any(p[0] == "poly" and len(p) > 5 for p in self.g.scene()))
        for _ in range(10):
            self.g.action("hint")
            if self.g.puzzle.hint_piece is not pc:
                break
        dashed = [p for p in self.g.scene() if p[0] == "poly" and len(p) > 5]
        self.assertEqual(len(dashed), 2)
        for p in dashed:
            self.assertEqual((p[2], p[3], p[5]), ("", HINT_YELLOW, (8, 5)))
        solid = [p for p in self.g.scene() if p[0] == "poly" and len(p) == 5 and p[1] == dashed[1][1]]
        self.assertEqual(solid[0][3], "#ffffff", "the hinted piece keeps its white outline under the dashes")


class SoundEventTests(unittest.TestCase):
    def setUp(self):
        self.g = Game(DATA, seed=2)

    def test_starting_a_game_emits_the_jingle_once(self):
        self.assertEqual(self.g.drain_events(), ["game_start"])
        self.assertEqual(self.g.drain_events(), [])

    def test_tapping_dragging_rotating_and_hinting(self):
        self.g.drain_events()
        hold_a_piece(self.g)
        self.assertEqual(self.g.drain_events(), ["pickup", "drop"])
        self.g.key("q")
        self.assertEqual(self.g.drain_events(), ["rotate"])
        self.g.key("h")
        self.assertEqual(self.g.drain_events(), ["hint"])

    def test_clicking_empty_board_is_silent(self):
        self.g.drain_events()
        self.g.mouse_down(Game.CX, Game.BAR_Y - 5)
        self.assertEqual(self.g.drain_events(), [])

    def test_opening_and_closing_the_menu(self):
        self.g.drain_events()
        self.g.key("p")
        self.assertEqual(self.g.drain_events(), ["menu_open"])
        click_menu_item(self.g, "resume")
        self.assertEqual(self.g.drain_events(), ["menu_close"])
        self.g.key("p")
        self.g.mouse_down(10, 10)
        self.assertEqual(self.g.drain_events(), ["menu_open", "menu_close"])

    def test_a_perfect_game_chimes_slides_and_ends(self):
        g = Game(DATA, seed=7)
        g.drain_events()
        for trial in range(TRIALS_PER_GAME):
            solve_perfectly(g)
            events = g.drain_events()
            self.assertEqual(events.count("solved_perfect"), 1, events)
            g.key("space")
            self.assertEqual(g.drain_events(), ["slide"] if trial < TRIALS_PER_GAME - 1 else ["game_end"])

    def test_a_sloppy_trial_gets_the_matching_chime(self):
        g = Game(DATA, seed=8)
        g.drain_events()
        hold_a_piece(g)
        for _ in range(9):                         # wasted rotations
            g.key("q")
        solve_perfectly(g)
        events = g.drain_events()
        self.assertNotEqual(g.last["rating"], "PERFECT")
        self.assertIn("solved_" + g.last["rating"].lower(), events)
        self.assertNotIn("solved_perfect", events)


if __name__ == "__main__":
    unittest.main()
