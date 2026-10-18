"""unittest suite, part 3: the audio layer. No sound card is needed: a fake backend records what would be played, and
unittest.mock stands in for pygame, Windows' winmm and the command line players so the exact calls can be checked.

Run everything:   python -m unittest discover -s tests -v
"""
import array
import os
import random
import sys
import unittest
import wave
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import FakeBackend          # noqa: E402
import audio as A                        # noqa: E402

CLIP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "audio")
NEEDED = {c for clips in A.EVENT_CLIPS.values() for c in clips} | set(A.MUSIC_CLIPS)


class ClipFileTests(unittest.TestCase):
    def test_every_clip_the_game_can_ask_for_exists_as_a_wav(self):
        for name in sorted(NEEDED):
            with self.subTest(clip=name):
                self.assertTrue(os.path.exists(os.path.join(CLIP_DIR, name + ".wav")))

    def test_wav_format_length_and_loudness(self):
        peaks = {}
        for name in sorted(NEEDED):
            with wave.open(os.path.join(CLIP_DIR, name + ".wav")) as w:
                with self.subTest(clip=name):
                    self.assertEqual((w.getsampwidth(), w.getframerate()), (2, 44100))
                    self.assertTrue(0.1 < w.getnframes() / 44100.0 < 10)
                peaks[name] = max(abs(x) for x in array.array("h", w.readframes(w.getnframes())))
        for name, peak in peaks.items():
            with self.subTest(clip=name):
                self.assertTrue(1500 < peak < 32000, peak)                  # not silent, not clipped
        quietest_effect = min(p for n, p in peaks.items() if n not in A.MUSIC_CLIPS)
        self.assertLess(max(peaks[n] for n in A.MUSIC_CLIPS), 0.5 * quietest_effect)      # music sits behind the effects


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.fb = FakeBackend()
        self.au = A.Audio(backend=self.fb, rng=random.Random(1))

    def test_all_clips_are_loaded_with_a_duration(self):
        self.assertEqual(set(self.fb.loaded), NEEDED)
        self.assertTrue(all(0.1 < self.au.durations[n] < 10 for n in NEEDED))
        self.assertEqual(self.au.backend_name, "fake")

    def test_each_event_plays_its_clip(self):
        table = {"solved_perfect": "chimes_AnswerPerfect", "solved_great": "chimes_AnswerExcellent",
                 "solved_ok": "chimes_AnswerCorrect", "menu_open": "popUpAppear", "menu_close": "popUpDisappear",
                 "game_start": "gameStart", "game_end": "gameEnd", "slide": "woodSlide", "hint": "hint",
                 "drop": "drop", "rotate": "tileRotate08"}
        for event, clip in table.items():
            with self.subTest(event=event):
                self.fb.played.clear()
                self.au.handle([event])
                self.assertEqual(self.fb.played, [clip])

    def test_pickups_use_all_four_variants(self):
        self.au.handle(["pickup"] * 60)
        self.assertEqual(set(self.fb.played), {"pickup0", "pickup1", "pickup2", "pickup3"})

    def test_several_events_in_one_call_play_in_order(self):
        self.au.handle(["drop", "rotate", "hint"])
        self.assertEqual(self.fb.played, ["drop", "tileRotate08", "hint"])

    def test_muted_sound_plays_nothing(self):
        self.au.handle(["drop", "rotate", "solved_perfect"], sound_on=False)
        self.assertEqual(self.fb.played, [])

    def test_unknown_events_and_empty_lists_are_ignored(self):
        self.au.handle(["no_such_event"])
        self.au.handle([])
        self.assertEqual(self.fb.played, [])

    def test_music_starts_at_once_and_then_waits_for_the_clip_to_end(self):
        self.au.update(0.0, music_on=True)
        self.assertEqual(len(self.fb.played), 1)
        first = self.fb.played[0]
        self.assertIn(first, A.MUSIC_CLIPS)
        self.au.update(self.au.durations[first] * 0.5, music_on=True)
        self.assertEqual(len(self.fb.played), 1)
        self.assertGreaterEqual(self.au.music_until, self.au.durations[first] + self.au.music_gap[0])
        self.assertLessEqual(self.au.music_until, self.au.durations[first] + self.au.music_gap[1])

    def test_music_never_repeats_the_same_clip_back_to_back(self):
        self.au.update(0.0, music_on=True)
        for _ in range(60):
            self.au.update(20.0, music_on=True)
        played = self.fb.played
        self.assertEqual(len(played), 61)
        self.assertTrue(all(a != b for a, b in zip(played, played[1:])))
        self.assertTrue(set(played) <= set(A.MUSIC_CLIPS))

    def test_music_gap_can_be_configured(self):
        au = A.Audio(backend=self.fb, rng=random.Random(1), music_gap=(0.0, 0.0))
        au.update(0.0, music_on=True)
        clip = au.music_playing
        self.assertAlmostEqual(au.music_until, au.durations[clip])

    def test_music_stops_when_muted_stays_off_and_restarts_immediately(self):
        self.au.update(0.0, music_on=True)
        playing = self.au.music_playing
        n = len(self.fb.played)
        self.au.update(0.1, music_on=False)
        self.assertEqual(self.fb.stopped, [playing])
        self.assertIsNone(self.au.music_playing)
        self.au.update(500.0, music_on=False)
        self.assertEqual(len(self.fb.played), n)
        self.au.update(0.1, music_on=True)
        self.assertEqual(len(self.fb.played), n + 1)

    def test_muting_twice_stops_only_once(self):
        self.au.update(0.0, music_on=True)
        self.au.update(0.1, music_on=False)
        self.au.update(0.1, music_on=False)
        self.assertEqual(len(self.fb.stopped), 1)

    def test_close_closes_the_backend(self):
        self.au.close()
        self.assertTrue(self.fb.closed)

    def test_a_failing_backend_close_is_swallowed(self):
        bad = mock.Mock()
        bad.name = "bad"
        bad.close.side_effect = OSError("device gone")
        A.Audio(backend=bad).close()                 # must not raise

    def test_a_missing_clip_folder_means_silence_not_a_crash(self):
        fb = FakeBackend()
        au = A.Audio(folder="/no/such/folder", backend=fb)
        au.handle(["drop", "solved_perfect"])
        au.update(1.0, music_on=True)
        self.assertEqual((fb.loaded, fb.played), ({}, []))

    def test_a_clip_that_fails_to_load_is_skipped(self):
        fb = FakeBackend(fail_on={"hint"})
        au = A.Audio(backend=fb)
        self.assertNotIn("hint", au.durations)
        au.handle(["hint", "drop"])
        self.assertEqual(fb.played, ["drop"])

    def test_every_event_maps_to_at_least_one_clip(self):
        for event, clips in A.EVENT_CLIPS.items():
            with self.subTest(event=event):
                self.assertTrue(clips)


def broken(name, exc):
    """A stand-in for a backend class that fails to start (a real factory has a __name__, which make_backend reports)."""
    def factory():
        raise exc
    factory.__name__ = name
    return factory


class BackendSelectionTests(unittest.TestCase):
    def test_the_first_backend_that_works_wins(self):
        with mock.patch.object(A, "PygameBackend", return_value="pygame!"):
            self.assertEqual(A.make_backend(), "pygame!")

    def test_failing_backends_are_skipped(self):
        with mock.patch.object(A, "PygameBackend", new=broken("PygameBackend", ImportError("no pygame"))), \
                mock.patch.object(A, "WindowsMciBackend", new=broken("WindowsMciBackend", OSError("not windows"))), \
                mock.patch.object(A, "SubprocessBackend", new=lambda: "player!"):
            self.assertEqual(A.make_backend(), "player!")

    def test_when_nothing_works_the_game_stays_silent(self):
        with mock.patch.object(A, "PygameBackend", new=broken("PygameBackend", ImportError("no pygame"))), \
                mock.patch.object(A, "WindowsMciBackend", new=broken("WindowsMciBackend", AttributeError("windll"))), \
                mock.patch.object(A, "SubprocessBackend", new=broken("SubprocessBackend", RuntimeError("no player"))):
            backend = A.make_backend()
        self.assertIsInstance(backend, A.NullBackend)
        for part in ("PygameBackend", "WindowsMciBackend", "SubprocessBackend"):
            self.assertIn(part, backend.reason)

    def test_the_null_backend_is_inert(self):
        nb = A.NullBackend()
        for call in (lambda: nb.load("x", "y"), lambda: nb.play("x"), lambda: nb.stop("x"), nb.close):
            call()
        self.assertEqual(nb.name, "none")


class SubprocessBackendTests(unittest.TestCase):
    def make(self, which=None, platform="linux"):
        which = which or (lambda name: "/usr/bin/" + name if name == "aplay" else None)
        with mock.patch.object(A.shutil, "which", side_effect=which), mock.patch.object(A.sys, "platform", platform):
            return A.SubprocessBackend()

    def test_linux_uses_the_first_available_player(self):
        pa = self.make(lambda n: "/usr/bin/" + n)                       # everything installed: paplay wins
        self.assertEqual(pa._cmd, ["paplay"])
        self.assertEqual(self.make()._cmd, ["aplay", "-q"])

    def test_macos_uses_afplay(self):
        self.assertEqual(self.make(lambda n: "/usr/bin/afplay" if n == "afplay" else None, "darwin")._cmd, ["afplay"])

    def test_no_player_means_the_backend_is_unavailable(self):
        with self.assertRaises(RuntimeError):
            self.make(lambda n: None)

    def test_play_runs_the_player_with_the_clip_and_stop_ends_running_ones(self):
        backend = self.make()
        running, finished = mock.Mock(), mock.Mock()
        running.poll.return_value = None
        finished.poll.return_value = 0
        with mock.patch.object(A.subprocess, "Popen", side_effect=[running, finished]) as popen:
            backend.load("x", "/tmp/x.wav")
            backend.play("x")
            backend.play("x")
            popen.assert_called_with(["aplay", "-q", "/tmp/x.wav"], stdout=A.subprocess.DEVNULL, stderr=A.subprocess.DEVNULL)
            self.assertEqual(popen.call_count, 2)
        backend.stop("x")
        running.terminate.assert_called_once_with()
        finished.terminate.assert_not_called()

    def test_unknown_clips_do_not_start_a_process(self):
        backend = self.make()
        with mock.patch.object(A.subprocess, "Popen") as popen:
            backend.play("nope")
            popen.assert_not_called()

    def test_close_stops_everything(self):
        backend = self.make()
        proc = mock.Mock()
        proc.poll.return_value = None
        with mock.patch.object(A.subprocess, "Popen", return_value=proc):
            backend.load("x", "/tmp/x.wav")
            backend.play("x")
        backend.close()
        proc.terminate.assert_called_once_with()


class WindowsMciBackendTests(unittest.TestCase):
    def make(self):
        backend = object.__new__(A.WindowsMciBackend)          # skip __init__: ctypes.windll only exists on Windows
        backend._winmm = mock.Mock()
        backend._winmm.mciSendStringW.return_value = 0
        backend._buf = object()
        backend._aliases = {}
        return backend

    def commands(self, backend):
        return [c.args[0] for c in backend._winmm.mciSendStringW.call_args_list]

    def test_load_opens_a_wave_device_with_its_own_alias(self):
        b = self.make()
        b.load("drop", r"C:\game\data\audio\drop.wav")
        self.assertEqual(self.commands(b), ['open "C:\\game\\data\\audio\\drop.wav" type waveaudio alias mp_drop'])

    def test_play_restarts_the_clip_so_it_can_overlap_other_sounds(self):
        b = self.make()
        b.load("drop", "d.wav")
        b._winmm.mciSendStringW.reset_mock()
        b.play("drop")
        self.assertEqual(self.commands(b), ["seek mp_drop to start", "play mp_drop"])

    def test_stop_and_close(self):
        b = self.make()
        b.load("a", "a.wav")
        b.load("b", "b.wav")
        b._winmm.mciSendStringW.reset_mock()
        b.stop("a")
        b.close()
        self.assertEqual(self.commands(b), ["stop mp_a", "close mp_a", "close mp_b"])
        self.assertEqual(b._aliases, {})

    def test_a_clip_that_fails_to_open_is_never_played(self):
        b = self.make()
        b._winmm.mciSendStringW.return_value = 263             # an MCI error code
        b.load("drop", "d.wav")
        b._winmm.mciSendStringW.reset_mock()
        b.play("drop")
        b._winmm.mciSendStringW.assert_not_called()

    def test_unknown_clips_are_ignored(self):
        b = self.make()
        b.play("nope")
        b.stop("nope")
        b._winmm.mciSendStringW.assert_not_called()

    @unittest.skipIf(sys.platform == "win32", "winmm exists on Windows")
    def test_the_real_backend_is_unavailable_on_other_systems(self):
        with self.assertRaises((AttributeError, OSError)):
            A.WindowsMciBackend()


class PygameBackendTests(unittest.TestCase):
    def fake_pygame(self):
        pg = mock.MagicMock()
        pg.mixer.Sound.side_effect = lambda path: mock.Mock(path=path)
        return pg

    def test_wiring_with_a_fake_pygame(self):
        pg = self.fake_pygame()
        with mock.patch.dict(sys.modules, {"pygame": pg}):
            backend = A.PygameBackend()
        pg.mixer.pre_init.assert_called_once_with(44100, -16, 2, 512)
        pg.mixer.init.assert_called_once_with()
        backend.load("drop", "/tmp/drop.wav")
        pg.mixer.Sound.assert_called_once_with("/tmp/drop.wav")
        backend.play("drop")
        backend._sounds["drop"].play.assert_called_once_with()
        backend.stop("drop")
        backend._sounds["drop"].stop.assert_called_once_with()
        backend.play("nope")                                   # unknown: nothing happens
        backend.close()
        pg.mixer.quit.assert_called_once_with()

    def test_an_uninstalled_pygame_makes_the_backend_unavailable(self):
        with mock.patch.dict(sys.modules, {"pygame": None}):   # None in sys.modules makes `import pygame` fail
            with self.assertRaises(ImportError):
                A.PygameBackend()

    def test_the_audio_layer_works_through_the_pygame_backend(self):
        pg = self.fake_pygame()
        with mock.patch.dict(sys.modules, {"pygame": pg}):
            au = A.Audio(backend=A.PygameBackend(), rng=random.Random(2))
        au.handle(["drop"])
        played = [name for name, s in au.backend._sounds.items() if s.play.called]
        self.assertEqual(played, ["drop"])


if __name__ == "__main__":
    unittest.main()
