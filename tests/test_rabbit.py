import contextlib
import io
import unittest
from unittest.mock import patch

from toki.rabbit import _FRAMES, dance


class RabbitTests(unittest.TestCase):
    def test_non_terminal_output_contains_rabbit_dance_frames(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch("toki.rabbit.time.sleep"):
            dance(duration=0.6, frame_delay=0.2)
        rendered = output.getvalue()
        self.assertEqual(rendered.count("[=.=]"), 3)
        self.assertIn("/\\       /\\", rendered)
        self.assertIn(_FRAMES[1][6], rendered)


if __name__ == "__main__":
    unittest.main()
