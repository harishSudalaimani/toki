import unittest
from unittest.mock import patch

from toki.stopwatch import Stopwatch, format_elapsed


class StopwatchTests(unittest.TestCase):
    def test_elapsed_uses_monotonic_clock(self):
        with patch("toki.stopwatch.time.monotonic", return_value=10.0):
            stopwatch = Stopwatch.start()
        self.assertAlmostEqual(stopwatch.elapsed(now=12.35), 2.35)

    def test_format_elapsed(self):
        self.assertEqual(format_elapsed(3661.29), "01:01:01.2")


if __name__ == "__main__":
    unittest.main()
