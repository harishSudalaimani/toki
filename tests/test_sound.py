import contextlib
import io
import unittest
from unittest.mock import patch

from toki.sound import play_alert


class SoundTests(unittest.TestCase):
    def test_terminal_bell_is_used_when_native_audio_is_unavailable(self):
        output = io.StringIO()
        with patch("toki.sound.sys.platform", "linux"), \
             patch("toki.sound.shutil.which", return_value=None), \
             contextlib.redirect_stdout(output):
            self.assertFalse(play_alert())
        self.assertEqual(output.getvalue(), "\a")

    def test_linux_tries_aplay_if_paplay_cannot_play(self):
        from toki.sound import _linux_sound

        players = {"canberra-gtk-play": None, "paplay": "/usr/bin/paplay", "aplay": "/usr/bin/aplay"}
        with patch("toki.sound.shutil.which", side_effect=players.get), \
             patch("toki.sound._run", side_effect=[False, True]) as run:
            self.assertTrue(_linux_sound())
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
