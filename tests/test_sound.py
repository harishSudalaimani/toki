import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from toki.sound import play_alert, ring_alert


class SoundTests(unittest.TestCase):
    def test_no_sound_backend_returns_unavailable(self):
        with patch("toki.sound.sys.platform", "linux"), \
             patch("toki.sound.shutil.which", return_value=None):
            self.assertFalse(play_alert())

    def test_missing_audio_backend_returns_without_terminal_bell(self):
        stop = threading.Event()
        stop.set()
        with patch("toki.sound.sys.platform", "linux"), \
             patch("toki.sound.shutil.which", return_value=None):
            self.assertFalse(ring_alert(stop, max_seconds=1))

    def test_windows_ring_stops_and_releases_system_sound(self):
        calls = []
        fake_winsound = SimpleNamespace(
            SND_FILENAME=8, SND_LOOP=2, SND_ASYNC=4,
            PlaySound=lambda sound, flags: calls.append((sound, flags)),
        )
        stop = threading.Event()
        stop.set()
        with patch("toki.sound.sys.platform", "win32"), \
             patch.dict("sys.modules", {"winsound": fake_winsound}), \
             patch("toki.sound._make_quack", return_value="quack.wav"), \
             patch("toki.sound.os.unlink"):
            self.assertTrue(ring_alert(stop, max_seconds=1))
        self.assertEqual(calls, [("quack.wav", 14), (None, 0)])


if __name__ == "__main__":
    unittest.main()
