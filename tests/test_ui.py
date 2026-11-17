import contextlib
import io
import unittest
from datetime import datetime
from unittest.mock import patch

from toki.ui import draw_dashboard, draw_timer


class UiTests(unittest.TestCase):
    def test_dashboard_scales_clock_for_large_terminal(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch("toki.ui._terminal", return_value=(120, 40)):
            draw_dashboard(datetime(2026, 2, 3, 14, 25, 36), ["  ●  07:30   Work   tomorrow"])
        rendered = output.getvalue()
        self.assertIn("TOKI", rendered)
        self.assertIn("ALARMS", rendered)
        self.assertIn("03 FEBRUARY 2026", rendered)
        self.assertGreaterEqual(rendered.count("███"), 6)

    def test_timer_screen_shows_progress_and_time(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch("toki.ui._terminal", return_value=(80, 24)):
            draw_timer(30, 60, elapsed=30.0)
        self.assertIn("TIMER", output.getvalue())
        self.assertIn("50%", output.getvalue())


if __name__ == "__main__":
    unittest.main()
