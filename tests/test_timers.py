import unittest
from unittest.mock import patch

from toki.timer import Countdown, format_duration, parse_duration


class TimerTests(unittest.TestCase):
    def test_parse_duration(self):
        for value, expected in (("30m", 1800), ("3h", 10800), ("90s", 90), ("1h30m", 5400)):
            with self.subTest(value=value):
                self.assertEqual(parse_duration(value), expected)

    def test_reject_bad_durations(self):
        for value in ("", "0s", "1m1m", "2d", "m30", "1h 30m"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_duration(value)

    def test_countdown_completion_uses_monotonic_elapsed_time(self):
        with patch("toki.timer.time.monotonic", return_value=100.0):
            timer = Countdown.start(5)
        self.assertEqual(timer.remaining(now=103.0), 2)
        self.assertEqual(timer.remaining(now=105.0), 0)
        with patch("toki.timer.time.monotonic", return_value=105.0):
            self.assertTrue(timer.complete)

    def test_format_duration(self):
        self.assertEqual(format_duration(5400), "01:30:00")


if __name__ == "__main__":
    unittest.main()
